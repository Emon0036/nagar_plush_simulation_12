import unittest

from backend.simulation.engine import SimulationEngine


class CycloneDashboardTests(unittest.TestCase):
    def make_engine(self):
        return SimulationEngine(agent_count=5)

    def test_normal_mode_has_cyclone_summary(self):
        state = self.make_engine().get_state()
        dashboard = state["cyclone_dashboard"]
        self.assertEqual(dashboard["mode"], "normal")
        self.assertEqual(dashboard["stage"], "normal")
        self.assertIn("feed", dashboard)

    def test_warning_switches_to_emergency_and_routes_agents(self):
        engine = self.make_engine()
        engine.inject_event("cyclone_warning", 0.55, "Test warning")
        dashboard = engine.get_state()["cyclone_dashboard"]
        self.assertEqual(dashboard["mode"], "emergency")
        self.assertEqual(dashboard["stage"], "warning")
        self.assertGreater(dashboard["evacuating_agents"], 0)
        self.assertEqual(dashboard["movement_speed_factor"], 0.82)
        self.assertTrue(any("warning" in item["message"].lower() for item in dashboard["feed"]))

    def test_landfall_records_damage_and_slow_movement(self):
        engine = self.make_engine()
        engine.inject_event("cyclone_warning", 0.55)
        engine.inject_event("cyclone_landfall", 0.85)
        dashboard = engine.get_state()["cyclone_dashboard"]
        self.assertEqual(dashboard["stage"], "landfall")
        self.assertEqual(dashboard["movement_speed_factor"], 0.55)
        self.assertGreater(dashboard["financial_damage_bdt"], 0)

    def test_recovery_switches_mode_and_starts_home_routes(self):
        engine = self.make_engine()
        engine.inject_event("cyclone_warning", 0.55)
        engine.inject_event("cyclone_landfall", 0.85)
        engine.inject_event("cyclone_recovery", 0)
        dashboard = engine.get_state()["cyclone_dashboard"]
        self.assertEqual(dashboard["mode"], "recovery")
        self.assertEqual(dashboard["stage"], "recovery")
        self.assertGreater(dashboard["returning_agents"], 0)
        self.assertTrue(any("recovery" in item["message"].lower() for item in dashboard["feed"]))


if __name__ == "__main__":
    unittest.main()
