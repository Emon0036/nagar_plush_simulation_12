import random
import re
from typing import Dict, Any, List, Tuple, Optional
from backend.ai.astar import pathfinder
from backend.ai.risk_model import risk_model
from backend.ai.decision_engine import decision_engine

MINUTES_PER_TICK = 15
TICKS_PER_DAY = 24 * 60 // MINUTES_PER_TICK
SIMULATION_DAYS_PER_MONTH = 30
TICKS_PER_MONTH = TICKS_PER_DAY * SIMULATION_DAYS_PER_MONTH

class CitizenAgent:
    """
    Autonomous AI Citizen Agent.
    Models an individual citizen in the simulated urban economy with private state,
    budget dynamics, personal goals, and adaptive decision-making.
    """
    def __init__(self, data: Dict[str, Any]):
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.age: int = int(data.get("age", 28))
        self.gender: str = data.get("gender", "Male")
        self.occupation: str = data["occupation"]
        self.education: str = data.get("education", "Secondary")
        self.skills: str = data.get("skills", "")
        self.monthly_income: float = float(data.get("monthly_income", data.get("income", 25000)))
        self.essential_expenses: float = float(data.get("essential_expenses", 14000))
        self.discretionary_expenses: float = float(data.get("discretionary_expenses", 6000))
        self.savings: float = float(data.get("savings", 10000))
        self.debt: float = float(data.get("debt", 0))
        self.dependents: int = int(data.get("dependents", 1))

        # Personal Goal (Slide 10: e.g. "Buy a laptop")
        self.goal: str = data.get("goal", "Build 6-month emergency fund")
        self.goal_target_bdt: float = float(data.get("goal_target_bdt", 65000))
        self.goal_progress_bdt: float = float(data.get("goal_progress_bdt", min(self.savings * 0.4, self.goal_target_bdt)))

        # AI State & Risk Model output
        self.risk_score: float = float(data.get("risk_score", 0.15))
        self.is_distressed: bool = bool(data.get("is_distressed", False))
        self.top_risk_drivers: List[str] = []

        # Navigation & Spatial state
        self.home_hub: str = data.get("home_hub", "housing")
        self.workplace_hub: str = data.get("workplace_hub", "workplace")
        self.current_hub: str = "housing"
        self.x, self.y = pathfinder.get_hub_door(self.home_hub)
        self.current_path: List[Tuple[int, int]] = []
        self.path_index: int = 0
        self.route_progress: float = 0.0
        self.target_hub: Optional[str] = None
        self.activity_state: str = "at_home"
        self.activity_started_tick: int = 0
        self.last_arrival_tick: int = 0
        self.completed_journeys: int = 0

        # Every resident gets a stable, slightly different routine.  The seed is
        # derived from the id so the city remains repeatable after a restart.
        self.schedule = self._build_schedule()
        self.dispatch_order: int = self._dispatch_order()
        self.queue_position: int = self.dispatch_order
        self.movement_speed: float = self.schedule["travel_speed"]
        self.next_action: Dict[str, Any] = {
            "title": "Protect your savings buffer",
            "description": "Keep essential spending covered and build a small emergency reserve.",
            "support_type": "buffer_support",
            "button_label": "Apply simulated support",
        }

        # Explainable Decision Engine state
        self.current_decision: Dict[str, Any] = {
            "activity": "at_home",
            "destination": self.home_hub,
            "reason_code": "INITIALIZED",
            "reason": "Agent is waiting for its first decision cycle.",
            "priority": 0,
            "urgent": False,
            "needs": [],
            "request_job_match": False,
            "support_type": "",
        }
        self.decision_history: List[Dict[str, Any]] = []
        self.job_match_requested: bool = False
        self.last_automatic_support_key: str = ""
        self.last_automatic_support: Dict[str, Any] = {
            "applied": False,
            "support_type": "",
            "description": "",
            "source": "",
            "tick": None,
        }
        # Episodic Memory log
        self.memory_log: List[Dict[str, Any]] = [
            {"tick": 0, "action": "Initialized in city", "reason": "Citizen profile active"}
        ]

    def _stable_seed(self) -> int:
        return sum((index + 1) * ord(char) for index, char in enumerate(str(self.id)))

    def _dispatch_order(self) -> int:
        match = re.search(r"(\d+)$", str(self.id))
        if match:
            return int(match.group(1))
        return self._stable_seed() % 50 + 1

    def _build_schedule(self) -> Dict[str, Any]:
        """Create a personal daily routine with staggered travel times."""
        rng = random.Random(self._stable_seed())
        occupation = str(self.occupation).lower()
        is_unemployed = "unemployed" in occupation or "seeking" in occupation
        is_student = "student" in occupation or "learner" in occupation

        # Spread departures across the morning so the city has a readable
        # rolling flow instead of all residents leaving at the same moment.
        departure = 6 * 60 + rng.randint(-10, 150)
        if is_unemployed:
            work_start = departure + rng.randint(20, 55)
            work_end = 14 * 60 + rng.randint(-30, 90)
        elif is_student:
            work_start = departure + rng.randint(25, 60)
            work_end = 15 * 60 + rng.randint(-30, 75)
        else:
            work_start = departure + rng.randint(25, 65)
            work_end = 16 * 60 + rng.randint(-45, 75)

        errand_start = work_end + rng.randint(20, 70)
        errand_end = errand_start + rng.randint(35, 105)
        home_return = errand_end + rng.randint(15, 60)
        return {
            "departure_minute": departure,
            "work_start_minute": work_start,
            "work_end_minute": work_end,
            "errand_start_minute": errand_start,
            "errand_end_minute": errand_end,
            "home_return_minute": home_return,
            "errand_hub": "bank" if rng.random() < 0.38 else "market",
            # Route speeds are cells per simulation tick.  They differ enough
            # to make agents arrive at different times on the same road.
            "travel_speed": round(0.65 + rng.random() * 0.75, 2),
            "home_stay_minutes": rng.randint(45, 120),
        }

    def set_destination(self, target_hub: str, tick: int = 0):
        self.target_hub = target_hub
        target_coord = pathfinder.get_hub_door(target_hub)
        start_coord = (int(round(self.x)), int(round(self.y)))
        self.current_path = pathfinder.find_path(start_coord, target_coord)
        self.route_progress = 0.0
        self.path_index = 1 if len(self.current_path) > 1 else 0
        self.activity_started_tick = tick
        self.activity_state = "traveling"

    def step_movement(self, tick: int = 0, environment: Optional[Dict[str, Any]] = None):
        """Steps along the current A* route towards the target destination"""
        if not self.current_path or self.target_hub is None:
            return

        final_segment = max(len(self.current_path) - 1, 0)
        weather_stage = (environment or {}).get("stage", "normal")
        weather_speed_factor = 0.55 if weather_stage == "landfall" else 0.82 if weather_stage == "warning" else 1.0
        self.route_progress = min(self.route_progress + self.movement_speed * weather_speed_factor, float(final_segment))
        segment = int(self.route_progress)
        fraction = self.route_progress - segment
        start = self.current_path[segment]
        end = self.current_path[min(segment + 1, final_segment)]
        self.x = round(start[0] + (end[0] - start[0]) * fraction, 3)
        self.y = round(start[1] + (end[1] - start[1]) * fraction, 3)
        self.path_index = min(segment + 1, len(self.current_path))

        if self.route_progress >= final_segment:
            arrived_hub = self.target_hub
            self.x, self.y = pathfinder.get_hub_door(arrived_hub)
            self.current_hub = arrived_hub
            self.current_path = []
            self.route_progress = 0.0
            self.path_index = 0
            self.target_hub = None
            self.last_arrival_tick = tick
            self.completed_journeys += 1
            decision_activity = str(self.current_decision.get("activity", ""))
            if arrived_hub == self.home_hub or decision_activity == "returning_home":
                self.activity_state = "at_home"
            elif decision_activity in ("evacuating", "sheltered"):
                self.activity_state = "sheltered"
            else:
                self.activity_state = "at_destination"

    def evaluate_and_decide(self, tick: int, macro_state: Dict[str, Any]):
        """
        AI Decision Cycle (Continuous Feedback Loop):
        1. Query Logistic Regression risk model given personal finances & current macro shocks.
        2. Adjust spending, savings allocation, and job search behavior.
        3. Determine next physical movement hub (Home -> Work/School -> Market/Bank).
        """
        food_shock = float(macro_state.get("food_shock_pct", 0.0))
        tax_rate = float(macro_state.get("tax_rate", 0.10))
        environment = macro_state.get("environment", {}) or {}
        weather_stage = environment.get("stage", "normal")

        # 1. Update AI Risk Assessment via Logistic Regression
        self.refresh_risk_assessment(macro_state)

        # 2. Economic Cash Flow Tick. Income and expenses are monthly values,
        # so only one 15-minute share is applied on each simulation tick.
        tick_share = 1.0 / TICKS_PER_MONTH
        tax_deduction = self.monthly_income * tax_rate * tick_share
        net_income = (self.monthly_income * tick_share) - tax_deduction

        # Essential expenses inflated by food/commodity shock
        effective_essential = self.essential_expenses * (1.0 + food_shock * 0.70) * tick_share

        # Adaptive spending response
        if self.is_distressed:
            # Under financial stress: drastically cut discretionary spending (Slide 11)
            effective_discretionary = self.discretionary_expenses * 0.20 * tick_share
            action_note = f"Financial stress alert (Risk {self.risk_score:.0%}). Slashed discretionary spending to 20%."
        elif self.risk_score > 0.35:
            # Moderate caution
            effective_discretionary = self.discretionary_expenses * 0.60 * tick_share
            action_note = f"Exercising caution due to inflation. Reduced discretionary spending."
        else:
            effective_discretionary = self.discretionary_expenses * tick_share
            action_note = "Finances healthy. Standard lifestyle maintained."

        net_savings_delta = net_income - (effective_essential + effective_discretionary)

        if net_savings_delta >= 0:
            # Positive flow: add to savings and contribute to goal
            goal_contribution = net_savings_delta * 0.35
            self.savings += net_savings_delta - goal_contribution
            self.goal_progress_bdt = min(self.goal_target_bdt, self.goal_progress_bdt + goal_contribution)
            if self.goal_progress_bdt >= self.goal_target_bdt and not hasattr(self, "_goal_completed"):
                self._goal_completed = True
                self.record_memory(tick, f"Goal Achieved: {self.goal}!", f"Accumulated {self.goal_target_bdt:,.0f} BDT")
        else:
            # Deficit: must withdraw from savings
            deficit = abs(net_savings_delta)
            if self.savings >= deficit:
                self.savings -= deficit
                self.record_memory(tick, "Withdrew from savings", f"Covered deficit of {deficit:,.0f} BDT due to cost spike")
            else:
                remaining_deficit = deficit - self.savings
                self.savings = 0.0
                self.debt += remaining_deficit
                self.record_memory(tick, "Incurred emergency debt", f"Exhausted savings; borrowed {remaining_deficit:,.0f} BDT")

        # Record high-impact economic reactions
        if food_shock > 0.15 and random.random() < 0.2:
            self.record_memory(tick, "Food Price Shock Reaction", action_note)

        # 3. Ask the explainable Decision Engine what the agent should do.
        # It considers weather, risk, needs, employment, time, and location.
        self.update_decision(macro_state, tick)

    def update_decision(self, macro_state: Dict[str, Any], tick: int = 0) -> Dict[str, Any]:
        """Re-evaluate intent without applying another financial cash-flow tick."""
        decision = decision_engine.choose(self.to_dict(), macro_state)
        self._apply_decision(decision, tick)
        return decision

    def _clear_route(self):
        self.current_path = []
        self.route_progress = 0.0
        self.path_index = 0
        self.target_hub = None

    def _apply_decision(self, decision: Dict[str, Any], tick: int):
        """Apply a decision without rebuilding an unchanged A* route."""
        previous = self.current_decision or {}
        changed = any(
            decision.get(key) != previous.get(key)
            for key in ("activity", "destination", "reason_code")
        )
        self.current_decision = decision
        self.job_match_requested = bool(decision.get("request_job_match"))

        if changed:
            history_item = {"tick": tick, **decision}
            self.decision_history.append(history_item)
            if len(self.decision_history) > 12:
                self.decision_history.pop(0)
            self.record_memory(
                tick,
                f"Decision: {decision.get('activity', 'unknown')}",
                str(decision.get("reason", "Decision selected from current city state.")),
            )

        destination = str(decision.get("destination") or self.home_hub)
        if self.target_hub is not None and self.target_hub != destination:
            # A changed decision, especially an urgent one, overrides the old route.
            self._clear_route()

        if self.target_hub is None and destination != self.current_hub:
            self.set_destination(destination, tick)
        elif self.target_hub is None:
            self.activity_state = str(decision.get("activity", "at_destination"))
    def refresh_risk_assessment(self, macro_state: Dict[str, Any]):
        """Refresh risk and turn the result into a plain-language action."""
        risk_result = risk_model.predict_risk(self.to_dict(), macro_state)
        self.risk_score = risk_result["risk_score"]
        self.is_distressed = risk_result["is_distressed"]
        self.top_risk_drivers = risk_result.get("drivers", [])
        self.next_action = self._recommend_next_action(macro_state)

    def _recommend_next_action(self, macro_state: Dict[str, Any]) -> Dict[str, Any]:
        food_shock = float(macro_state.get("food_shock_pct", 0.0))
        tax_rate = float(macro_state.get("tax_rate", 0.10))
        environment = macro_state.get("environment", {}) or {}
        occupation = self.occupation.lower()

        # Safety actions must be recommended even when the agent is not financially distressed.
        if environment.get("stage") in ("warning", "landfall"):
            return {
                "title": "Move to the emergency shelter",
                "description": "Follow the civic shelter route and keep essential savings available for recovery.",
                "support_type": "emergency_support",
                "button_label": "Apply emergency support",
            }

        if not self.is_distressed:
            return {
                "title": "Protect your savings buffer",
                "description": "Keep essential spending covered and monitor the economic shock.",
                "support_type": "buffer_support",
                "button_label": "Apply simulated support",
            }

        if "unemployed" in occupation or "seeking" in occupation:
            return {
                "title": "Visit the civic center for job matching",
                "description": "A suitable work match can improve income and reduce pressure over time.",
                "support_type": "job_search_support",
                "button_label": "Apply temporary support",
            }
        if food_shock >= 0.15:
            return {
                "title": "Receive targeted food support",
                "description": "A temporary household transfer can cover the higher cost of essentials.",
                "support_type": "food_support",
                "button_label": "Apply food support",
            }
        if tax_rate >= 0.15:
            return {
                "title": "Receive temporary tax relief",
                "description": "A short-term relief payment protects take-home income while tax pressure is high.",
                "support_type": "tax_relief",
                "button_label": "Apply tax relief",
            }
        if self.debt > max(self.monthly_income * 0.25, 5000):
            return {
                "title": "Create a bank repayment plan",
                "description": "A small debt reduction can prevent the household from falling further behind.",
                "support_type": "debt_support",
                "button_label": "Apply debt support",
            }
        return {
            "title": "Build an emergency savings buffer",
            "description": "Protect essential expenses first and use a small targeted transfer to rebuild savings.",
            "support_type": "buffer_support",
            "button_label": "Apply savings support",
        }
    def record_memory(self, tick: int, action: str, reason: str):
        self.memory_log.append({"tick": tick, "action": action, "reason": reason})
        if len(self.memory_log) > 15:
            self.memory_log.pop(0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "occupation": self.occupation,
            "education": self.education,
            "skills": self.skills,
            "income": self.monthly_income,
            "monthly_income": self.monthly_income,
            "essential_expenses": self.essential_expenses,
            "discretionary_expenses": self.discretionary_expenses,
            "savings": self.savings,
            "debt": self.debt,
            "dependents": self.dependents,
            "goal": self.goal,
            "goal_target_bdt": self.goal_target_bdt,
            "goal_progress_bdt": self.goal_progress_bdt,
            "risk_score": self.risk_score,
            "is_distressed": int(self.is_distressed),
            "top_drivers": self.top_risk_drivers,
            "next_action": self.next_action,
            "decision": self.current_decision,
            "decision_history": self.decision_history[-8:],
            "job_match_requested": self.job_match_requested,
            "automatic_support": self.last_automatic_support,
            "weather_status": self.current_decision.get("activity") if self.current_decision.get("activity") in ("evacuating", "sheltered", "returning_home") else "normal",
            "home_hub": self.home_hub,
            "workplace_hub": self.workplace_hub,
            "current_hub": self.current_hub,
            "target_hub": self.target_hub,
            "route_remaining_steps": max(len(self.current_path) - self.path_index, 0),
            "route_progress": round(self.route_progress, 3),
            "route_length": max(len(self.current_path) - 1, 0),
            "activity_state": self.activity_state,
            "activity_started_tick": self.activity_started_tick,
            "last_arrival_tick": self.last_arrival_tick,
            "completed_journeys": self.completed_journeys,
            "travel_speed": self.movement_speed,
            "dispatch_order": self.dispatch_order,
            "queue_position": self.queue_position,
            "schedule": self.schedule,
            "x": round(float(self.x), 3),
            "y": round(float(self.y), 3),
            "route": [[int(x), int(y)] for x, y in self.current_path],
            "memory_log": self.memory_log[-8:]
        }
