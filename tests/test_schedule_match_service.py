import unittest
from datetime import date, time

from backend_server.services.schedule_match_service import (
    convert_target_to_company_schedule_slot,
    get_company_schedule_timezone,
    get_schedule_time_range_text,
    schedule_row_matches_target,
)


class ScheduleMatchServiceTests(unittest.TestCase):
    def test_company_schedule_timezone_uses_77072_reference(self):
        self.assertEqual("America/Chicago", get_company_schedule_timezone())

    def test_convert_target_to_company_schedule_slot_from_mountain_time(self):
        converted_date, converted_time = convert_target_to_company_schedule_slot(
            date(2026, 7, 25),
            time(17, 0),
            "America/Denver",
        )
        self.assertEqual(date(2026, 7, 25), converted_date)
        self.assertEqual(time(18, 0), converted_time)

    def test_convert_target_to_company_schedule_slot_rolls_to_next_day(self):
        converted_date, converted_time = convert_target_to_company_schedule_slot(
            date(2026, 7, 25),
            time(23, 30),
            "America/Los_Angeles",
        )
        self.assertEqual(date(2026, 7, 26), converted_date)
        self.assertEqual(time(1, 30), converted_time)

    def test_get_schedule_time_range_text_prefers_us_range(self):
        self.assertEqual(
            "08:00 AM - 11:00 PM",
            get_schedule_time_range_text("08:00 AM - 11:00 PM", "08:00 PM - 10:00 AM"),
        )

    def test_schedule_row_matches_target_in_company_time_window(self):
        self.assertTrue(
            schedule_row_matches_target(
                "2026-07-25",
                "WORK",
                "08:00 AM - 11:00 PM",
                date(2026, 7, 25),
                time(18, 0),
            )
        )


if __name__ == "__main__":
    unittest.main()
