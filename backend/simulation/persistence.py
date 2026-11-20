"""Transactional storage for the shared, complete simulation state."""
import json
import time
from contextlib import contextmanager
from datetime import datetime

from backend.database.db import db_manager
from backend.simulation.agent import CitizenAgent
from backend.simulation.engine import SimulationEngine, engine as initial_engine

SNAPSHOT_ID = "shared-city"
SCHEMA_VERSION = 1


def encode_snapshot(engine):
    state = dict(vars(engine))
    state.pop("_database_now", None)
    state["agents"] = [dict(vars(agent)) for agent in engine.agents]
    state["snapshot_managed"] = True
    def convert(value):
        if hasattr(value, "item"):
            return value.item()
        raise TypeError(f"Cannot serialize simulation value: {type(value).__name__}")
    return json.dumps(state, default=convert, allow_nan=False, separators=(",", ":"))


def decode_snapshot(payload):
    state = json.loads(payload)
    if not isinstance(state, dict) or not isinstance(state.get("agents"), list):
        raise ValueError("Invalid simulation snapshot")
    instance = SimulationEngine.__new__(SimulationEngine)
    agents = []
    for agent_state in state.pop("agents"):
        agent = CitizenAgent.__new__(CitizenAgent)
        agent.__dict__.update(agent_state)
        agents.append(agent)
    instance.__dict__.update(state)
    instance.agents = agents
    instance.snapshot_managed = True
    return instance


@contextmanager
def simulation_session(write=False):
    """Load the shared city; writers hold a database lock until commit."""
    mysql = db_manager.db_type == "mysql"
    connection = db_manager.get_mysql_connection() if mysql else db_manager.get_sqlite_connection()
    if connection is None:
        raise RuntimeError("Simulation database is unavailable")
    cursor = None
    try:
        cursor = connection.cursor()
        if mysql:
            # TiDB's pessimistic transaction acquires the row lock before changes.
            cursor.execute("BEGIN PESSIMISTIC")
            cursor.execute("INSERT IGNORE INTO citypulse_snapshot (snapshot_id, schema_version, state_json) VALUES (%s, %s, %s)", (SNAPSHOT_ID, SCHEMA_VERSION, encode_snapshot(initial_engine)))
            cursor.execute("SELECT schema_version, state_json FROM citypulse_snapshot WHERE snapshot_id = %s FOR UPDATE", (SNAPSHOT_ID,))
        else:
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute("INSERT OR IGNORE INTO citypulse_snapshot (snapshot_id, schema_version, state_json) VALUES (?, ?, ?)", (SNAPSHOT_ID, SCHEMA_VERSION, encode_snapshot(initial_engine)))
            cursor.execute("SELECT schema_version, state_json FROM citypulse_snapshot WHERE snapshot_id = ?", (SNAPSHOT_ID,))
        row = cursor.fetchone()
        if row is None or row[0] != SCHEMA_VERSION:
            raise RuntimeError("Unsupported or missing simulation snapshot version")
        instance = decode_snapshot(row[1])
        if mysql:
            cursor.execute("SELECT UNIX_TIMESTAMP(CURRENT_TIMESTAMP(3))")
            instance._database_now = float(cursor.fetchone()[0])
        else:
            instance._database_now = time.time()
        previous_tick = instance.tick
        yield instance
        if write:
            placeholder = "%s" if mysql else "?"
            cursor.execute(f"UPDATE citypulse_snapshot SET state_json = {placeholder} WHERE snapshot_id = {placeholder}", (encode_snapshot(instance), SNAPSHOT_ID))
            if instance.tick != previous_tick and (instance.tick % 5 == 0 or instance.macro_state["food_shock_pct"] > 0):
                metrics = instance.metrics_history[-1]
                columns = ("tick", "run_id", "food_shock_pct", "tax_rate", "inflation_rate", "gini_coefficient", "poverty_rate", "avg_savings", "avg_income", "distressed_count")
                values = [metrics[name] for name in columns]
                if not mysql:
                    columns += ("created_at",)
                    values.append(datetime.now().isoformat())
                cursor.execute("INSERT INTO simulation_history (" + ", ".join(columns) + ") VALUES (" + ", ".join([placeholder] * len(columns)) + ")", values)
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
