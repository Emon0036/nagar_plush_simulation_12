import unittest

from backend.ai.decision_engine import decision_engine


class DecisionEngineTests(unittest.TestCase):
    def setUp(self):
        self.agent = {
            "id": "test-1",
            "occupation": "Programmer",
            "income": 30000,
            "essential_expenses": 17000,
            "savings": 5000,
            "debt": 0,
            "dependents": 1,
            "risk_score": 0.01,
            "home_hub": "housing",
            "workplace_hub": "workplace",
            "schedule": {
                "departure_minute": 390,
                "work_start_minute": 420,
                "work_end_minute": 960,
                "errand_start_minute": 1000,
                "errand_end_minute": 1060,
                "home_return_minute": 1100,
                "errand_hub": "market",
            },
        }
        self.normal = {
            "food_shock_pct": 0.0,
            "tax_rate": 0.10,
            "simulation_clock": {"minutes": 480},
            "environment": {"stage": "normal", "shelter_hub": "city_center"},
        }

    def test_normal_work_routine(self):
        decision = decision_engine.choose(self.agent, self.normal)
        self.assertEqual(decision["activity"], "working")
        self.assertEqual(decision["destination"], "workplace")

    def test_unemployed_requests_csp(self):
        agent = {**self.agent, "occupation": "Unemployed / Seeking", "income": 3000, "savings": 500}
        decision = decision_engine.choose(agent, self.normal)
        self.assertEqual(decision["activity"], "job_search")
        self.assertTrue(decision["request_job_match"])

    def test_debt_routes_to_bank(self):
        agent = {**self.agent, "debt": 12000}
        decision = decision_engine.choose(agent, self.normal)
        self.assertEqual(decision["destination"], "bank")

    def test_food_need_routes_to_market(self):
        agent = {**self.agent, "savings": 500}
        macro = {**self.normal, "food_shock_pct": 0.30}
        decision = decision_engine.choose(agent, macro)
        self.assertEqual(decision["destination"], "market")

    def test_cyclone_overrides_normal_routine(self):
        macro = {**self.normal, "environment": {"stage": "warning", "shelter_hub": "city_center"}}
        decision = decision_engine.choose(self.agent, macro)
        self.assertEqual(decision["reason_code"], "CYCLONE_OVERRIDE")
        self.assertEqual(decision["destination"], "city_center")

    def test_recovery_returns_home(self):
        macro = {**self.normal, "environment": {"stage": "recovery", "shelter_hub": "city_center"}}
        decision = decision_engine.choose(self.agent, macro)
        self.assertEqual(decision["reason_code"], "CYCLONE_RECOVERY")
        self.assertEqual(decision["destination"], "housing")

    def test_high_model_risk_seeks_support(self):
        agent = {**self.agent, "risk_score": 0.80}
        decision = decision_engine.choose(agent, self.normal)
        self.assertEqual(decision["activity"], "seeking_support")


if __name__ == "__main__":
    unittest.main()