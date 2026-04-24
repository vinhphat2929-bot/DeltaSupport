import unittest

from utils.timezone_utils import build_deadline_preview, format_deadline_hint_text


class TimezoneUtilsTests(unittest.TestCase):
    def test_build_deadline_preview_infers_timezone_and_formats_vn_and_ust(self):
        preview = build_deadline_preview(
            deadline_date_text="25-04-2026",
            deadline_time_text="05:00",
            deadline_period_text="PM",
            merchant_raw_text="SAPPHIRE NAILS 90012",
            viewer_timezone="Asia/Ho_Chi_Minh",
        )

        self.assertEqual("America/Los_Angeles", preview["deadline_timezone"])
        self.assertEqual("25-04-2026 05:00 PM PDT", preview["deadline_ust_label"])
        self.assertEqual("26-04-2026 07:00 AM ICT", preview["deadline_vn_label"])
        self.assertEqual("26-04-2026", preview["deadline_date"])
        self.assertEqual("07:00", preview["deadline_time"])
        self.assertEqual("AM", preview["deadline_period"])

    def test_build_deadline_preview_accepts_combined_time_text(self):
        preview = build_deadline_preview(
            deadline_date_text="25-04-2026",
            deadline_time_text="05:00 PM",
            merchant_raw_text="DIAMOND NAILS 10001",
            viewer_timezone="Asia/Ho_Chi_Minh",
        )

        self.assertEqual("America/New_York", preview["deadline_timezone"])
        self.assertEqual("25-04-2026 05:00 PM EDT", preview["deadline_ust_label"])
        self.assertEqual("26-04-2026 04:00 AM ICT", preview["deadline_vn_label"])

    def test_format_deadline_hint_text_uses_vnt_then_ust(self):
        hint_text = format_deadline_hint_text(
            {
                "deadline_vn_label": "26-04-2026 07:00 AM ICT",
                "deadline_ust_label": "25-04-2026 05:00 PM PDT",
            }
        )

        self.assertEqual(
            "Nhap theo gio bang khach.\nVNT: 26-04-2026 07:00 AM ICT\nUST: 25-04-2026 05:00 PM PDT",
            hint_text,
        )


if __name__ == "__main__":
    unittest.main()
