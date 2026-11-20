"""Explainable, rule-based activity selection for EcoSim citizens.

The Decision Engine answers only: "What should this agent do now?"
It does not calculate financial risk, allocate jobs, or calculate routes.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping


@dataclass(frozen=True)
class AgentDecision:
    activity: str
    destination: str
    reason_code: str
    reason: str
    priority: int
    urgent: bool = False
    needs: List[str] = field(default_factory=list)
    request_job_match: bool = False
    support_type: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DecisionEngine:
    """Choose the next explainable activity for one agent."""

    def choose(self, agent: Mapping[str, Any], macro_state: Mapping[str, Any]) -> Dict[str, Any]:
        environment = macro_state.get("environment", {}) or {}
        stage = str(environment.get("stage", "normal"))
        shelter_hub = str(environment.get("shelter_hub", "city_center"))
        clock = macro_state.get("simulation_clock", {}) or {}
        minutes = int(clock.get("minutes", 360))

        income = max(float(agent.get("income", agent.get("monthly_income", 25000))), 100.0)
        essential_expenses = max(float(agent.get("essential_expenses", 14000)), 100.0)
        savings = max(float(agent.get("savings", 0.0)), 0.0)
        debt = max(float(agent.get("debt", 0.0)), 0.0)
        risk_score = float(agent.get("risk_score", 0.0))
        food_shock = float(macro_state.get("food_shock_pct", 0.0))
        tax_rate = float(macro_state.get("tax_rate", 0.10))
        take_home = max(income * (1.0 - min(max(tax_rate, 0.0), 0.80)), 100.0)
        shocked_essential = essential_expenses * (1.0 + food_shock * 0.70)
        savings_months = savings / max(shocked_essential, 100.0)
        debt_ratio = debt / take_home

        occupation = str(agent.get("occupation", "")).lower()
        is_unemployed = "unemployed" in occupation or "seeking" in occupation
        is_student = (
            "student" in occupation
            or "learner" in occupation
            or str(agent.get("workplace_hub", "")) == "education"
        )

        # Safety always outranks the economic routine.
        if stage in ("warning", "landfall"):
            activity = "evacuating" if stage == "warning" else "sheltered"
            label = "cyclone warning" if stage == "warning" else "cyclone landfall"
            return self._decision(
                activity=activity,
                destination=shelter_hub,
                reason_code="CYCLONE_OVERRIDE",
                reason=f"{label.title()} overrides normal work, study, shopping, and banking.",
                priority=100,
                urgent=True,
                needs=["safety", "shelter"],
                support_type="emergency_support",
            )

        if stage == "recovery":
            return self._decision(
                activity="returning_home",
                destination=str(agent.get("home_hub", "housing")),
                reason_code="CYCLONE_RECOVERY",
                reason="The city is reopening, so the agent returns home before resuming normal routines.",
                priority=95,
                urgent=True,
                needs=["safe_return"],
            )

        critical_financial = risk_score >= 0.75 or (risk_score >= 0.50 and savings_months < 0.50)
        food_need = food_shock >= 0.15 and savings_months < 1.50

        # A critical unemployed resident needs both work and immediate support.
        if critical_financial and is_unemployed:
            return self._decision(
                activity="job_search",
                destination="city_center",
                reason_code="CRITICAL_JOB_SEARCH",
                reason="The agent is unemployed with critical financial pressure; seek support while the CSP job search is triggered.",
                priority=95,
                urgent=True,
                needs=["employment", "essential_support"],
                request_job_match=True,
                support_type="job_search_support",
            )

        # A critical household with a food need goes to essential supplies first.
        if critical_financial and food_need:
            return self._decision(
                activity="shopping",
                destination="market",
                reason_code="CRITICAL_FOOD_NEED",
                reason="The savings buffer is nearly exhausted during a food shock; essential food takes priority.",
                priority=92,
                urgent=True,
                needs=["food", "essential_goods", "essential_support"],
                support_type="food_support",
            )

        # Severe financial pressure otherwise routes the agent to recovery support.
        if critical_financial:
            return self._decision(
                activity="seeking_support",
                destination="city_center",
                reason_code="CRITICAL_FINANCIAL_RISK",
                reason="Financial risk is critical or the savings buffer is nearly exhausted; seek essential support.",
                priority=90,
                urgent=True,
                needs=["essential_support", "savings_buffer"],
                support_type="buffer_support",
            )
        # Job search is an intent; CSP will decide the suitable vacancy.
        if is_unemployed:
            return self._decision(
                activity="job_search",
                destination="city_center",
                reason_code="JOB_SEARCH",
                reason="The agent is unemployed or seeking work, so the civic center is the next useful destination.",
                priority=80,
                needs=["employment"],
                request_job_match=True,
                support_type="job_search_support",
            )

        if debt_ratio >= 0.25 or debt > max(income * 0.25, 5000.0):
            return self._decision(
                activity="banking",
                destination="bank",
                reason_code="HIGH_DEBT",
                reason="Debt is high compared with take-home income; visit the bank for repayment planning.",
                priority=75,
                needs=["debt_support", "repayment_plan"],
                support_type="debt_support",
            )

        if food_shock >= 0.15 and savings_months < 1.50:
            return self._decision(
                activity="shopping",
                destination="market",
                reason_code="FOOD_NEED",
                reason="Food prices are elevated and the household has a thin buffer, so essential food comes first.",
                priority=70,
                needs=["food", "essential_goods"],
                support_type="food_support",
            )

        if risk_score >= 0.50 or (risk_score >= 0.35 and savings_months < 1.0):
            return self._decision(
                activity="seeking_support",
                destination="city_center",
                reason_code="HIGH_FINANCIAL_RISK",
                reason="Financial risk is high, so the agent prioritizes recovery support over optional activity.",
                priority=65,
                needs=["recovery_support", "savings_buffer"],
                support_type="buffer_support",
            )

        schedule = agent.get("schedule", {}) or {}
        departure = int(schedule.get("departure_minute", 360))
        work_start = int(schedule.get("work_start_minute", departure + 30))
        work_end = int(schedule.get("work_end_minute", 960))
        errand_start = int(schedule.get("errand_start_minute", work_end + 30))
        errand_end = int(schedule.get("errand_end_minute", errand_start + 60))
        home_return = int(schedule.get("home_return_minute", errand_end + 30))
        errand_hub = str(schedule.get("errand_hub", "market"))
        work_hub = "education" if is_student else str(agent.get("workplace_hub", "workplace"))
        home_hub = str(agent.get("home_hub", "housing"))

        if minutes < departure:
            return self._decision(
                activity="at_home",
                destination=home_hub,
                reason_code="NORMAL_HOME_TIME",
                reason="It is before the agent's normal departure time.",
                priority=20,
            )

        if minutes < work_start:
            return self._decision(
                activity="learning" if is_student else "traveling",
                destination=work_hub,
                reason_code="NORMAL_DEPARTURE",
                reason="The normal daily routine has started; travel toward work or education.",
                priority=30,
            )

        if minutes < work_end:
            return self._decision(
                activity="learning" if is_student else "working",
                destination=work_hub,
                reason_code="NORMAL_WORK_ROUTINE",
                reason="It is normal working or learning time.",
                priority=30,
            )

        if minutes < errand_start:
            return self._decision(
                activity="traveling",
                destination=errand_hub,
                reason_code="NORMAL_ERRAND",
                reason="The work or learning block is complete; travel toward the planned errand.",
                priority=25,
            )

        if minutes < errand_end:
            activity = "banking" if errand_hub == "bank" else "shopping"
            return self._decision(
                activity=activity,
                destination=errand_hub,
                reason_code="NORMAL_ERRAND",
                reason="The agent is in its planned banking or essential-shopping window.",
                priority=25,
            )

        if minutes < home_return:
            return self._decision(
                activity="traveling",
                destination=home_hub,
                reason_code="NORMAL_RETURN",
                reason="The daily errand is complete; return home.",
                priority=20,
            )

        return self._decision(
            activity="at_home",
            destination=home_hub,
            reason_code="NORMAL_HOME_TIME",
            reason="The normal daily routine is complete.",
            priority=20,
        )

    @staticmethod
    def _decision(
        activity: str,
        destination: str,
        reason_code: str,
        reason: str,
        priority: int,
        urgent: bool = False,
        needs: List[str] = None,
        request_job_match: bool = False,
        support_type: str = "",
    ) -> Dict[str, Any]:
        return AgentDecision(
            activity=activity,
            destination=destination,
            reason_code=reason_code,
            reason=reason,
            priority=priority,
            urgent=urgent,
            needs=list(needs or []),
            request_job_match=request_job_match,
            support_type=support_type,
        ).to_dict()


decision_engine = DecisionEngine()