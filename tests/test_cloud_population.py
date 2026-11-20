import unittest
from unittest.mock import MagicMock, patch

from backend.simulation.engine import SimulationEngine


class CloudPopulationTests(unittest.TestCase):
    def test_citizens_are_loaded_from_database_fields(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [{
            "agent_id": "cloud-1", "name": "Resident", "occupation": "Teacher",
            "monthly_income": 20000, "essential_expense": 8000,
            "discretionary_expense": 3000, "savings": 5000, "debt": 0,
        }]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        instance = SimulationEngine.__new__(SimulationEngine)
        with patch("backend.simulation.engine.db_manager.get_mysql_connection", return_value=connection):
            instance._load_cloud_agents(1)
        self.assertEqual(instance.agents[0].id, "cloud-1")
        self.assertEqual(instance.agents[0].essential_expenses, 8000)
        connection.close.assert_called_once()

    def test_incomplete_cloud_population_fails_without_local_fallback(self):
        connection = MagicMock()
        connection.cursor.return_value.fetchall.return_value = []
        instance = SimulationEngine.__new__(SimulationEngine)
        with patch("backend.simulation.engine.db_manager.get_mysql_connection", return_value=connection):
            with self.assertRaisesRegex(RuntimeError, "50 are required"):
                instance._load_cloud_agents(50)
