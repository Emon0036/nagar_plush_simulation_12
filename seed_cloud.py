"""Seed Aiven MySQL with a Bangladesh-calibrated synthetic simulation population."""
from backend.data.bangladesh_seed import generate_population
from backend.database.db import db_manager


def main():
    records = generate_population()
    if db_manager.db_type != "mysql":
        raise RuntimeError(
            "Aiven MySQL is not connected. Check MYSQL_* values in .env before seeding. "
            "No data was inserted into the SQLite fallback."
        )
    if not db_manager.save_citizens([
        {**record, "income": record["monthly_income"]} for record in records
    ]):
        raise RuntimeError("Cloud insert failed.")

    connection = db_manager.get_mysql_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM citizens WHERE agent_id LIKE 'bd2022_%'")
    inserted = cursor.fetchone()[0]
    cursor.close()
    connection.close()
    print(f"Seeded and verified {inserted} Bangladesh-calibrated synthetic profiles in Aiven MySQL.")


if __name__ == "__main__":
    main()
