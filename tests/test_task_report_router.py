import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend_server"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend_server.routers import task_report


class FakeCursor:
    def __init__(self, fetchone_results=None, fetchall_results=None):
        self.fetchone_results = list(fetchone_results or [])
        self.fetchall_results = list(fetchall_results or [])
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        if self.fetchone_results:
            return self.fetchone_results.pop(0)
        return None

    def fetchall(self):
        if self.fetchall_results:
            return self.fetchall_results.pop(0)
        return []


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


class TaskReportRouterTests(unittest.TestCase):
    def test_schedule_matched_technician_uses_display_name_column(self):
        cursor = FakeCursor(
            fetchone_results=[("hoang",)],
            fetchall_results=[
                [
                    (
                        "hoang",
                        "2026-04-25",
                        "WORK",
                        "08:00 AM - 11:00 PM",
                        "08:00 PM - 10:00 AM",
                        "Hoang Nguyen",
                    )
                ]
            ],
        )
        connection = FakeConnection(cursor)

        with patch.object(task_report, "get_connection", return_value=connection), patch.object(
            task_report,
            "table_exists",
            return_value=True,
        ), patch.object(
            task_report,
            "get_schedule_candidate_dates",
            return_value=[date(2026, 4, 25)],
        ), patch.object(
            task_report,
            "schedule_row_matches_target",
            return_value=True,
        ), patch.object(
            task_report,
            "get_company_schedule_timezone",
            return_value="America/Chicago",
        ):
            result = task_report.get_task_report_technicians(
                action_by="hoang",
                work_date="25-04-2026",
                work_time="10:00",
            )

        self.assertTrue(result["success"])
        self.assertEqual(
            [{"username": "hoang", "display_name": "Hoang Nguyen"}],
            result["data"],
        )
        self.assertTrue(connection.closed)


if __name__ == "__main__":
    unittest.main()
