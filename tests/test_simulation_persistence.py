import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.config import config
from backend.database.db import db_manager
from backend.simulation.persistence import simulation_session
from backend.app import step_simulation


class SimulationPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path_patch = patch.object(config, "SQLITE_PATH", str(Path(self.tmp.name) / "test.db"))
        self.type_patch = patch.object(db_manager, "db_type", "sqlite")
        self.path_patch.start()
        self.type_patch.start()
        conn = db_manager.get_sqlite_connection()
        db_manager._create_sqlite_tables(conn.cursor())
        conn.commit()
        conn.close()

    def tearDown(self):
        self.type_patch.stop()
        self.path_patch.stop()
        self.tmp.cleanup()

    def test_state_restores_after_new_session_and_rollback(self):
        with simulation_session(write=True) as engine:
            engine.inject_event("cyclone_warning", 0.55)
            engine.step()
            expected = engine.get_state()
        with simulation_session() as restored:
            self.assertEqual(restored.get_state(), expected)
        with self.assertRaises(RuntimeError):
            with simulation_session(write=True) as engine:
                engine.step()
                raise RuntimeError("rollback")
        with simulation_session() as restored:
            self.assertEqual(restored.tick, expected["tick"])

    def test_concurrent_writers_do_not_lose_ticks(self):
        errors = []
        def advance():
            try:
                with simulation_session(write=True) as engine:
                    engine.step()
            except Exception as exc:
                errors.append(exc)
        threads = [threading.Thread(target=advance) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        with simulation_session() as restored:
            self.assertEqual(restored.tick, 4)

    def test_history_is_committed_with_the_fifth_tick(self):
        for _ in range(5):
            with simulation_session(write=True) as engine:
                engine.step()
        conn = db_manager.get_sqlite_connection()
        try:
            self.assertEqual(conn.execute("SELECT tick FROM simulation_history").fetchone()[0], 5)
        finally:
            conn.close()

    def test_multiple_automatic_requests_share_one_tick(self):
        with patch("backend.simulation.persistence.time.time", return_value=100.0):
            self.assertEqual(step_simulation(automatic=True)["tick"], 1)
            self.assertEqual(step_simulation(automatic=True)["tick"], 1)
            self.assertEqual(step_simulation(automatic=False)["tick"], 2)
        with patch("backend.simulation.persistence.time.time", return_value=101.1):
            self.assertEqual(step_simulation(automatic=True)["tick"], 3)
