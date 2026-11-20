import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from backend.simulation.agent import CitizenAgent
from backend.simulation.city import city_env
from backend.data.dataset_generator import generate_citizens_dataset
from backend.ai.csp_solver import run_job_allocation_csp
from backend.database.db import db_manager

logger = logging.getLogger("EcoSimEngine")

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MARKET_CONFIG_PATH = os.path.join(_BASE_DIR, "backend/data/market_config.json")
CITIZENS_CSV_PATH = os.path.join(_BASE_DIR, "backend/data/citizens.csv")

# Simulation clock: one real UI day is about 96 seconds in the frontend,
# split into 96 fifteen-minute ticks.
MINUTES_PER_TICK = 15
TICKS_PER_DAY = 24 * 60 // MINUTES_PER_TICK
SIMULATION_START_MINUTE = 6 * 60  # Start the city at 06:00.

class SimulationEngine:
    """
    EcoSim AI Simulation Engine.
    Coordinates agents, macro-shocks, labor market CSP matches,
    and macroeconomic indicator computation.
    """
    def __init__(self, agent_count: int = 50):
        self.tick: int = 0
        self.run_id: str = f"run_{os.urandom(4).hex()}"
        self.is_running: bool = False
        
        # Macroeconomic state
        self.macro_state = {
            "food_shock_pct": 0.0, # e.g. 0.30 for +30% food price shock
            "tax_rate": 0.10,
            "inflation_rate": 0.05,
            "poverty_line_bdt": 8500.0,
            "active_event_description": "Normal Economic Baseline",
            "environment": {
                "stage": "normal",
                "severity": 0.0,
                "wind_kph": 0,
                "rain_intensity": 0.0,
                "shelter_hub": "city_center",
                "title": "Clear weather",
                "description": "Normal city movement and routines."
            }
        }
        self._update_clock()

        self.agents: List[CitizenAgent] = []
        self.job_market_templates: List[Dict[str, Any]] = []
        self.metrics_history: List[Dict[str, Any]] = []
        self.recent_events: List[Dict[str, Any]] = []
        self.last_csp_tick: int = -TICKS_PER_DAY
        self.last_csp_result: Dict[str, Any] = {}
        self.support_event_id: int = 0
        self.cyclone_damage_bdt: float = 0.0
        self.cyclone_support_bdt: float = 0.0
        self.cyclone_feed: List[Dict[str, Any]] = []

        self._load_market_config()
        self._load_or_generate_agents(agent_count)
        for agent in self.agents:
            agent.refresh_risk_assessment(self.macro_state)
            agent.update_decision(self.macro_state, tick=0)
        self._refresh_dispatch_queue()
        self.calculate_metrics() # Initial metrics

    def _load_market_config(self):
        if os.path.exists(MARKET_CONFIG_PATH):
            with open(MARKET_CONFIG_PATH, "r") as f:
                data = json.load(f)
            self.job_market_templates = data.get("job_market_templates", [])
            self.macro_state["poverty_line_bdt"] = data.get("poverty_line_monthly_bdt", 8500.0)

    def _load_or_generate_agents(self, count: int):
        if db_manager.db_type == "mysql":
            self._load_cloud_agents(count)
            return
        if not os.path.exists(CITIZENS_CSV_PATH):
            try:
                generate_citizens_dataset(count, CITIZENS_CSV_PATH)
            except Exception as e:
                logger.error(f"Failed to generate citizens dataset: {e}")
                return
        
        try:
            df = pd.read_csv(CITIZENS_CSV_PATH)
            # Keep the checked-in dataset reusable, but run the live city with
            # the configured population so the map remains readable.
            self.agents = [CitizenAgent(row.to_dict()) for _, row in df.head(count).iterrows()]
        except Exception as e:
            logger.error(f"Failed to load citizens: {e}")
            self.agents = []
            return
        
        # Startup must not overwrite persisted citizens with CSV defaults.

    def _load_cloud_agents(self, count: int):
        """Initialize the live population from TiDB, without CSV fallback."""
        conn = db_manager.get_mysql_connection()
        if conn is None:
            raise RuntimeError("Cannot load citizens: TiDB is unavailable")
        try:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("SELECT * FROM citizens ORDER BY agent_id LIMIT %s", (count,))
                rows = cursor.fetchall()
            finally:
                cursor.close()
        finally:
            conn.close()
        if len(rows) < count:
            raise RuntimeError(f"TiDB has {len(rows)} citizens; {count} are required")
        self.agents = [CitizenAgent({
            **row,
            "id": row["agent_id"],
            "essential_expenses": row["essential_expense"],
            "discretionary_expenses": row["discretionary_expense"],
        }) for row in rows]

    def step(self) -> Dict[str, Any]:
        """
        Advances the simulation by one tick (representing a business cycle unit).
        """
        self.tick += 1
        self._update_clock()

        # 1. Agent decision loop & spatial movement
        cyclone_decision_updates = 0
        stage_before_step = self.macro_state.get("environment", {}).get("stage", "normal")
        for agent in self.agents:
            previous_activity = agent.current_decision.get("activity")
            agent.evaluate_and_decide(self.tick, self.macro_state)
            current_activity = agent.current_decision.get("activity")
            if stage_before_step in ("warning", "landfall", "recovery") and current_activity != previous_activity and cyclone_decision_updates < 5:
                if current_activity in ("evacuating", "sheltered"):
                    self._add_cyclone_feed("🚶", f"{agent.name} → Emergency Shelter")
                    cyclone_decision_updates += 1
                elif current_activity == "returning_home":
                    self._add_cyclone_feed("🚶", f"{agent.name} → Home for recovery")
                    cyclone_decision_updates += 1
            self._maybe_apply_automatic_support(agent)
            agent.step_movement(self.tick, self.macro_state.get("environment"))

        stage = self.macro_state.get("environment", {}).get("stage", "normal")
        automatic_emergency_supports = sum(
            1 for agent in self.agents
            if agent.last_automatic_support.get("tick") == self.tick
            and agent.last_automatic_support.get("support_type") == "emergency_support"
        )
        if automatic_emergency_supports:
            self._add_cyclone_feed("💰", f"Emergency support automatically provided to {automatic_emergency_supports} agents")
        if stage in ("warning", "landfall"):
            shelter_id = self.macro_state["environment"].get("shelter_hub", "city_center")
            reached = sum(
                1 for agent in self.agents
                if agent.last_arrival_tick == self.tick and agent.current_hub == shelter_id
            )
            if reached:
                self._add_cyclone_feed("🟢", f"{reached} agent{'s' if reached != 1 else ''} reached the emergency shelter")
        elif stage == "recovery":
            returned = sum(
                1 for agent in self.agents
                if agent.last_arrival_tick == self.tick and agent.current_hub == agent.home_hub
            )
            if returned:
                self._add_cyclone_feed("🏠", f"{returned} agent{'s' if returned != 1 else ''} returned home")

        self._maybe_run_csp()

        # Keep the visible rotation order deterministic: residents who have
        # completed a journey return home, while the next scheduled residents
        # become the next outbound travelers.
        self._refresh_dispatch_queue()

        # 2. Compute macroeconomic indicators
        metrics = self.calculate_metrics()

        # 3. Persist periodically to database
        if not getattr(self, "snapshot_managed", False) and (self.tick % 5 == 0 or self.macro_state["food_shock_pct"] > 0):
            db_manager.record_tick_metrics(metrics)
            if self.tick % 20 == 0:
                db_manager.save_citizens([a.to_dict() for a in self.agents])

        return {
            "tick": self.tick,
            "simulation_clock": self.get_simulation_clock(),
            "macro_state": self.macro_state,
            "metrics": metrics
        }

    def _maybe_apply_automatic_support(self, agent: CitizenAgent):
        """Apply one explainable support intervention for an urgent decision."""
        decision = agent.current_decision or {}
        # Any explicit recovery/support option is executable by the agent;
        # urgent decisions are not the only ones that can need help.
        if not decision.get("support_type"):
            return None

        support_type = str(decision["support_type"])
        reason_code = str(decision.get("reason_code", "DECISION_SUPPORT"))
        support_key = f"{agent.id}:{self.support_event_id}:{reason_code}:{support_type}"
        if agent.last_automatic_support_key == support_key:
            return None

        return self.apply_agent_support(
            agent.id,
            support_type=support_type,
            automatic=True,
            support_key=support_key,
        )

    def _maybe_run_csp(self):
        """Run job matching at most once per simulated day when requested."""
        requesters = [agent for agent in self.agents if agent.job_match_requested]
        if not requesters or self.tick - self.last_csp_tick < TICKS_PER_DAY:
            return None

        result = self.run_labor_csp()
        self.last_csp_tick = self.tick
        matched_ids = {
            match.get("agent_id")
            for match in result.get("allocations", [])
            if match.get("matched")
        }
        for agent in requesters:
            agent.job_match_requested = False
            agent.record_memory(
                self.tick,
                "Decision completed: job matched" if agent.id in matched_ids else "Decision completed: job search",
                "The CSP solver found a suitable vacancy." if agent.id in matched_ids else "No suitable vacancy was available in this matching cycle.",
            )
        self.last_csp_result = {
            "tick": self.tick,
            "automatic": True,
            "request_count": len(requesters),
            "matched_count": len(matched_ids),
            "allocations": result.get("allocations", []),
        }
        return result

    def _refresh_dispatch_queue(self):
        """Update the fair, repeatable order used by the city travel cycle."""
        now = self.macro_state.get("simulation_clock", {}).get("minutes", SIMULATION_START_MINUTE)
        ordered = sorted(
            self.agents,
            key=lambda item: (
                0 if item.activity_state == "traveling" else 1,
                abs(int(item.schedule.get("departure_minute", now)) - int(now)),
                item.dispatch_order,
            ),
        )
        for position, agent in enumerate(ordered, start=1):
            agent.queue_position = position

    def get_movement_summary(self) -> Dict[str, Any]:
        states = {}
        for agent in self.agents:
            states[agent.activity_state] = states.get(agent.activity_state, 0) + 1
        traveling = [agent for agent in self.agents if agent.activity_state == "traveling"]
        next_agent = min(
            (agent for agent in self.agents if agent.activity_state == "at_home"),
            key=lambda item: (item.schedule.get("departure_minute", 0), item.dispatch_order),
            default=None,
        )
        return {
            "total_agents": len(self.agents),
            "state_counts": states,
            "traveling_count": len(traveling),
            "at_home_count": sum(1 for agent in self.agents if agent.activity_state == "at_home"),
            "weather_stage": self.macro_state.get("environment", {}).get("stage", "normal"),
            "sheltered_count": sum(1 for agent in self.agents if agent.activity_state == "sheltered"),
            "next_dispatch_agent_id": next_agent.id if next_agent else None,
            "next_dispatch_agent_name": next_agent.name if next_agent else None,
            "active_routes": [
                {
                    "agent_id": agent.id,
                    "target_hub": agent.target_hub,
                    "progress": round(agent.route_progress, 3),
                    "remaining_steps": max(len(agent.current_path) - agent.path_index, 0),
                }
                for agent in traveling
            ],
        }

    def get_simulation_clock(self) -> Dict[str, Any]:
        """Return the simulated 24-hour clock for the current tick."""
        day_index = self.tick // TICKS_PER_DAY + 1
        minutes = (SIMULATION_START_MINUTE + (self.tick * MINUTES_PER_TICK)) % (24 * 60)
        hour, minute = divmod(minutes, 60)
        return {
            "day": day_index,
            "hour": hour,
            "minute": minute,
            "minutes": minutes,
            "time": f"{hour:02d}:{minute:02d}",
            "tick_in_day": self.tick % TICKS_PER_DAY,
            "ticks_per_day": TICKS_PER_DAY,
            "minutes_per_tick": MINUTES_PER_TICK,
        }

    def _update_clock(self):
        """Keep the current clock available to every agent and API response."""
        self.macro_state["simulation_clock"] = self.get_simulation_clock()

    def _add_cyclone_feed(self, icon: str, message: str, tick: Optional[int] = None):
        """Keep a compact, chronological emergency activity feed for the UI."""
        event_tick = self.tick if tick is None else tick
        self.cyclone_feed.append({
            "tick": event_tick,
            "time": self.get_simulation_clock()["time"],
            "icon": icon,
            "message": message,
        })
        self.cyclone_feed = self.cyclone_feed[-40:]

    def get_cyclone_dashboard(self) -> Dict[str, Any]:
        """Aggregate existing cyclone, movement, risk, and route state for React."""
        environment = self.macro_state.get("environment", {}) or {}
        stage = str(environment.get("stage", "normal"))
        mode = "emergency" if stage in ("warning", "landfall") else "recovery" if stage == "recovery" else "normal"
        total = len(self.agents)
        affected = [agent for agent in self.agents if stage != "normal"]
        evacuating = [agent for agent in self.agents if agent.current_decision.get("activity") == "evacuating"]
        sheltered = [agent for agent in self.agents if agent.current_hub == environment.get("shelter_hub", "city_center") and agent.target_hub is None]
        returning = [agent for agent in self.agents if agent.current_decision.get("activity") == "returning_home"]
        recovered = [agent for agent in affected if agent.current_hub == agent.home_hub and agent.target_hub is None]
        high_risk = [agent for agent in self.agents if agent.is_distressed or agent.risk_score >= 0.50]
        shelter_id = str(environment.get("shelter_hub", "city_center"))
        shelter = city_env.hubs.get(shelter_id, {})
        capacity = max(50, total + 10)
        speed_factor = 0.55 if stage == "landfall" else 0.82 if stage == "warning" else 1.0
        if mode == "recovery":
            progress = (len(recovered) / max(len(affected), 1))
        elif mode == "emergency":
            progress = len(sheltered) / max(total, 1)
        else:
            progress = 0.0
        return {
            "mode": mode,
            "stage": stage,
            "title": environment.get("title", "Clear weather"),
            "description": environment.get("description", "Normal city movement and routines."),
            "severity": round(float(environment.get("severity", 0.0)), 3),
            "wind_kph": environment.get("wind_kph", 0),
            "rain_intensity": environment.get("rain_intensity", 0.0),
            "affected_agents": len(affected),
            "high_risk_agents": len(high_risk),
            "evacuating_agents": len(evacuating),
            "sheltered_agents": len(sheltered),
            "returning_agents": len(returning),
            "recovered_agents": len(recovered),
            "total_agents": total,
            "available_shelters": [{
                "id": shelter_id,
                "name": f"{shelter.get('name', 'Emergency Shelter')}",
                "capacity": capacity,
                "occupied": len(sheltered),
                "available": max(capacity - len(sheltered), 0),
            }],
            "movement_speed_factor": speed_factor,
            "movement_speed_reduction_pct": round((1.0 - speed_factor) * 100),
            "financial_damage_bdt": round(self.cyclone_damage_bdt),
            "emergency_support_bdt": round(self.cyclone_support_bdt),
            "recovery_progress": round(min(max(progress, 0.0), 1.0), 3),
            "feed": self.cyclone_feed[-15:],
        }

    def calculate_metrics(self) -> Dict[str, Any]:
        """
        Computes community-wide economic indicators:
        - Gini Coefficient (Inequality)
        - Poverty Headcount Ratio
        - Average & Median Savings in BDT
        - Distressed population percentage
        """
        if not self.agents:
            return {}

        incomes = np.array([a.monthly_income for a in self.agents])
        savings = np.array([a.savings for a in self.agents])
        debts = np.array([a.debt for a in self.agents])
        wealth = np.maximum(savings + incomes, 1.0)

        # Exact Gini calculation on total economic capacity (wealth)
        gini = self._compute_gini(wealth)

        # Poverty and distress
        distressed_agents = [a for a in self.agents if a.is_distressed]
        distressed_count = len(distressed_agents)
        poverty_count = sum(1 for a in self.agents if a.monthly_income < self.macro_state["poverty_line_bdt"])
        
        # Quintile breakdown (Low, Lower-Mid, Mid, Upper-Mid, High)
        sorted_indices = np.argsort(incomes)
        n = len(self.agents)
        q_size = max(n // 5, 1)
        quintiles = []
        for q in range(5):
            idx_start = q * q_size
            idx_end = (q + 1) * q_size if q < 4 else n
            q_agents = [self.agents[sorted_indices[i]] for i in range(idx_start, idx_end)]
            quintiles.append({
                "quintile": f"Q{q+1}",
                "label": ["Lowest 20%", "Second 20%", "Middle 20%", "Fourth 20%", "Top 20%"][q],
                "avg_income": round(float(np.mean([a.monthly_income for a in q_agents])), 2),
                "avg_savings": round(float(np.mean([a.savings for a in q_agents])), 2),
                "avg_risk": round(float(np.mean([a.risk_score for a in q_agents])), 3)
            })

        metrics = {
            "tick": self.tick,
            "run_id": self.run_id,
            "food_shock_pct": self.macro_state["food_shock_pct"],
            "tax_rate": self.macro_state["tax_rate"],
            "inflation_rate": self.macro_state["inflation_rate"],
            "gini_coefficient": round(float(gini), 4),
            "poverty_rate": round(float(poverty_count / n), 4),
            "distress_rate": round(float(distressed_count / n), 4),
            "distressed_count": distressed_count,
            "total_agents": n,
            "avg_savings": round(float(np.mean(savings)), 2),
            "median_savings": round(float(np.median(savings)), 2),
            "avg_income": round(float(np.mean(incomes)), 2),
            "total_debt": round(float(np.sum(debts)), 2),
            "quintiles": quintiles
        }

        self.metrics_history.append(metrics)
        if len(self.metrics_history) > 100:
            self.metrics_history.pop(0)

        return metrics

    def _compute_gini(self, array: np.ndarray) -> float:
        """Computes Gini coefficient using relative mean absolute difference"""
        array = np.sort(array)
        index = np.arange(1, array.shape[0] + 1)
        n = array.shape[0]
        return ((np.sum((2 * index - n  - 1) * array)) / (n * np.sum(array)))

    def inject_event(self, event_type: str, magnitude: float = 0.0, description: str = "") -> Dict[str, Any]:
        """
        User-driven event injection (Slide 6 & Slide 11):
        - food_price_shock (+30% food prices)
        - tax_change (e.g. 0.05 to 0.25)
        - cash_stimulus (direct transfers to vulnerable agents)
        - cyclone_warning, cyclone_landfall, cyclone_recovery
        - reset_baseline
        """
        self.support_event_id += 1

        if event_type == "food_price_shock":
            mag = magnitude if magnitude != 0 else 0.30 # Default 30% shock
            self.macro_state["food_shock_pct"] = mag
            desc = description or f"Food Price Shock: Essential food prices increased by {mag*100:.0f}%"
            self.macro_state["active_event_description"] = desc
        elif event_type == "tax_change":
            mag = magnitude if magnitude != 0 else 0.15
            self.macro_state["tax_rate"] = mag
            desc = description or f"Fiscal Policy Shift: Tax rate adjusted to {mag*100:.1f}%"
            self.macro_state["active_event_description"] = desc
        elif event_type == "cash_stimulus":
            stimulus_amount = magnitude if magnitude != 0 else 5000.0
            # Direct stimulus to vulnerable/distressed citizens
            eligible_count = 0
            for a in self.agents:
                if a.is_distressed or a.monthly_income < 25000.0:
                    a.savings += stimulus_amount
                    a.record_memory(self.tick, "Received Government Stimulus", f"Direct aid of {stimulus_amount:,.0f} BDT")
                    eligible_count += 1
            desc = f"Government Cash Stimulus: Disbursed {stimulus_amount:,.0f} BDT to {eligible_count} vulnerable citizens"
            self.macro_state["active_event_description"] = desc
        elif event_type in ("cyclone_warning", "cyclone_landfall", "cyclone_recovery"):
            stage_defaults = {
                "cyclone_warning": (0.55, "warning", 80, 0.65, "Cyclone warning", "Residents are leaving work and moving toward emergency shelters."),
                "cyclone_landfall": (0.85, "landfall", 125, 0.95, "Cyclone landfall", "Movement is slower and vulnerable households are taking shelter."),
                "cyclone_recovery": (0.25, "recovery", 20, 0.20, "Cyclone recovery", "Sheltered residents are returning home and the city is reopening."),
            }
            default_severity, stage, default_wind, rain, title, detail = stage_defaults[event_type]
            severity = magnitude if magnitude != 0 else default_severity
            environment = self.macro_state["environment"]
            environment.update({
                "stage": stage,
                "severity": max(0.0, min(float(severity), 1.0)),
                "wind_kph": round(default_wind if event_type != "cyclone_warning" else 55 + severity * 45),
                "rain_intensity": rain,
                "title": title,
                "description": detail,
            })
            if event_type == "cyclone_warning":
                self.cyclone_damage_bdt = 0.0
                self.cyclone_support_bdt = 0.0
                self._add_cyclone_feed("⚠️", "Cyclone warning issued")
            if event_type == "cyclone_landfall" and not environment.get("damage_applied"):
                total_damage = 0.0
                for a in self.agents:
                    vulnerability = min(1.0, 0.30 + a.dependents * 0.07 + max(0.0, 1.0 - a.savings / max(a.essential_expenses * 3.0, 1.0)) * 0.35 + a.risk_score * 0.20)
                    cost = round((1500.0 + 4500.0 * severity) * vulnerability, -2)
                    if a.savings >= cost:
                        a.savings -= cost
                    else:
                        a.debt += cost - a.savings
                        a.savings = 0.0
                    total_damage += cost
                    a.record_memory(self.tick, "Cyclone emergency cost", f"Emergency household cost of {cost:,.0f} BDT")
                self.cyclone_damage_bdt += total_damage
                environment["damage_applied"] = True
                self._add_cyclone_feed("🔴", "Cyclone landfall: emergency household costs applied")
            desc = description or f"{title}: {detail}"
            self.macro_state["active_event_description"] = desc
            if event_type == "cyclone_recovery":
                self._add_cyclone_feed("🟢", "Cyclone passed; recovery and return-home routes started")
        elif event_type == "reset_baseline":
            self.macro_state["food_shock_pct"] = 0.0
            self.macro_state["tax_rate"] = 0.10
            self.macro_state["inflation_rate"] = 0.05
            self.macro_state["environment"] = {
                "stage": "normal", "severity": 0.0, "wind_kph": 0,
                "rain_intensity": 0.0, "shelter_hub": "city_center",
                "title": "Clear weather", "description": "Normal city movement and routines."
            }
            self.cyclone_damage_bdt = 0.0
            self.cyclone_support_bdt = 0.0
            self.cyclone_feed = []
            desc = "Economy reset to stable baseline conditions."
            self.macro_state["active_event_description"] = desc
        else:
            desc = f"Custom Event: {event_type}"

        event_record = {
            "id": len(self.recent_events) + 1,
            "event_type": event_type,
            "magnitude": magnitude,
            "description": desc,
            "tick": self.tick
        }
        self.recent_events.append(event_record)

        # Immediately step and re-evaluate so the user sees real-time impact
        self.step()
        return event_record

    def apply_agent_support(
        self,
        agent_id: str,
        support_type: str = "auto",
        automatic: bool = False,
        support_key: str = "",
    ) -> Dict[str, Any]:
        """Apply one small, explainable intervention to a selected resident."""
        agent = next((item for item in self.agents if item.id == agent_id), None)
        if not agent:
            raise ValueError("Agent not found")

        agent.refresh_risk_assessment(self.macro_state)
        before_score = agent.risk_score
        before_danger_count = sum(1 for item in self.agents if item.is_distressed)
        action = agent.next_action
        chosen_support = support_type if support_type != "auto" else action.get("support_type", "buffer_support")

        if chosen_support == "debt_support":
            reduction = min(agent.debt, 5000.0)
            agent.debt -= reduction
            support_description = f"Reduced debt by {reduction:,.0f} BDT"
        elif chosen_support == "tax_relief":
            agent.savings += 4000.0
            support_description = "Added 4,000 BDT temporary tax relief"
        elif chosen_support == "food_support":
            agent.savings += 5000.0
            support_description = "Added 5,000 BDT targeted food support"
        elif chosen_support == "job_search_support":
            agent.savings += 3000.0
            support_description = "Added 3,000 BDT temporary job-search support"
        elif chosen_support == "emergency_support":
            agent.savings += 5000.0
            support_description = "Added 5,000 BDT emergency cyclone support"
        else:
            agent.savings += 3000.0
            support_description = "Added 3,000 BDT targeted savings support"

        source = "Decision Engine" if automatic else "User"
        agent.record_memory(
            self.tick,
            "Received Automatic Support" if automatic else "Received Targeted Support",
            f"{support_description} Source: {source}.",
        )
        if automatic:
            agent.last_automatic_support_key = support_key
            agent.last_automatic_support = {
                "applied": True,
                "support_type": chosen_support,
                "description": support_description,
                "source": source,
                "tick": self.tick,
            }
            if chosen_support == "emergency_support":
                self.cyclone_support_bdt += 5000.0
        agent.refresh_risk_assessment(self.macro_state)
        agent.update_decision(self.macro_state, tick=self.tick)
        after_score = agent.risk_score
        after_danger_count = sum(1 for item in self.agents if item.is_distressed)
        metrics = self.calculate_metrics()
        return {
            "agent": agent.to_dict(),
            "support_type": chosen_support,
            "description": support_description,
            "before_risk": before_score,
            "after_risk": after_score,
            "before_danger_count": before_danger_count,
            "after_danger_count": after_danger_count,
            "risk_reduced": after_score < before_score,
            "automatic": automatic,
            "metrics": metrics,
        }

    def run_labor_csp(self) -> Dict[str, Any]:
        """
        Executes Constraint Satisfaction Problem (CSP) solver on the labor market.
        Matches unemployed or underemployed citizens with job vacancies.
        """
        # Candidates: agents currently unemployed or earning below 20,000 BDT
        candidates = [a.to_dict() for a in self.agents if a.occupation == "Unemployed / Seeking" or a.monthly_income < 20000]
        
        # Vacancies from config
        vacancies = []
        for t in self.job_market_templates:
            # Create individual vacancy instances up to capacity
            for i in range(min(t.get("capacity", 5), 4)):
                vacancies.append({
                    "job_id": f"{t['job_id']}_{i+1}",
                    "title": t["title"],
                    "sector": t["sector"],
                    "required_education": t["required_education"],
                    "required_skills": t["required_skills"],
                    "offered_salary_bdt": t["offered_salary_bdt"],
                    "workplace_hub": t["workplace_hub"]
                })

        result = run_job_allocation_csp(vacancies, candidates)

        # Apply matched allocations to agents
        agent_map = {a.id: a for a in self.agents}
        for match in result.get("allocations", []):
            if match.get("matched") and match["agent_id"] in agent_map:
                agent = agent_map[match["agent_id"]]
                old_occ = agent.occupation
                agent.occupation = match["job_title"]
                agent.monthly_income = match["salary_bdt"]
                agent.workplace_hub = match.get("workplace_hub", agent.workplace_hub)
                agent.schedule = agent._build_schedule()
                agent.movement_speed = agent.schedule["travel_speed"]
                agent.job_match_requested = False
                agent.refresh_risk_assessment(self.macro_state)
                agent.update_decision(self.macro_state, tick=self.tick)
                agent.record_memory(
                    self.tick, 
                    "Job Matched via CSP", 
                    f"Assigned to {match['job_title']} ({match['salary_bdt']:,} BDT/mo) from {old_occ}"
                )

        return result

    def get_state(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "run_id": self.run_id,
            "simulation_clock": self.get_simulation_clock(),
            "macro_state": self.macro_state,
            "city": city_env.to_dict(),
            "metrics": self.metrics_history[-1] if self.metrics_history else {},
            "metrics_history": self.metrics_history[-30:],
            "recent_events": self.recent_events[-10:],
            "movement": self.get_movement_summary(),
            "job_matching": self.last_csp_result,
            "cyclone_dashboard": self.get_cyclone_dashboard(),
            "agents_summary": [a.to_dict() for a in self.agents] # Full live population for the map
        }

engine = SimulationEngine()
