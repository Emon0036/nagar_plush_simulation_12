import unittest
from unittest.mock import MagicMock, patch
import certifi

from backend.app import get_database_status
from backend.database.db import db_manager


class DatabaseHealthTests(unittest.TestCase):
    def test_mysql_uses_bundled_ca_and_verifies_server_identity(self):
        with patch("mysql.connector.connect") as connect:
            db_manager.get_mysql_connection()
        self.assertTrue(connect.call_args.kwargs["use_pure"])
        self.assertEqual(connect.call_args.kwargs["ssl_ca"], certifi.where())
        self.assertTrue(connect.call_args.kwargs["ssl_verify_cert"])
        self.assertTrue(connect.call_args.kwargs["ssl_verify_identity"])

    def test_mysql_probe_executes_query_and_closes_connection(self):
        connection = MagicMock()
        with patch.object(db_manager, "db_type", "mysql"), patch.object(
            db_manager, "get_mysql_connection", return_value=connection
        ):
            result = db_manager.get_status()
        self.assertEqual(result, {"status": "ok", "active_storage": "mysql"})
        connection.cursor.return_value.execute.assert_called_once_with("SELECT 1")
        connection.close.assert_called_once()

    def test_unavailable_database_returns_503_without_details(self):
        with patch.object(db_manager, "db_type", "mysql"), patch.object(
            db_manager, "get_mysql_connection", return_value=None
        ):
            response = get_database_status()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.body, b'{"status":"unavailable","active_storage":"mysql"}')


if __name__ == "__main__":
    unittest.main()
