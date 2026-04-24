import unittest
from datetime import date, datetime, time

from backend_server.services.timezone_service import (
    convert_local_to_utc,
    infer_timezone_from_merchant,
    normalize_timezone_name,
    resolve_deadline_timezone,
    serialize_deadline_for_view,
)


class TimezoneServiceTests(unittest.TestCase):
    def test_infer_timezone_from_zip_for_california(self):
        timezone_name, source = infer_timezone_from_merchant(zip_code="90012")
        self.assertEqual("America/Los_Angeles", timezone_name)
        self.assertEqual("zip_dataset", source)

    def test_infer_timezone_from_zip_for_california_desert(self):
        timezone_name, source = infer_timezone_from_merchant(zip_code="92260")
        self.assertEqual("America/Los_Angeles", timezone_name)
        self.assertEqual("zip_dataset", source)

    def test_infer_timezone_from_zip_for_new_york(self):
        timezone_name, source = infer_timezone_from_merchant(zip_code="20003")
        self.assertEqual("America/New_York", timezone_name)
        self.assertEqual("zip_dataset", source)

    def test_infer_timezone_from_zip_for_arizona(self):
        timezone_name, source = infer_timezone_from_merchant(zip_code="85001")
        self.assertEqual("America/Phoenix", timezone_name)
        self.assertEqual("zip_dataset", source)

    def test_infer_timezone_from_zip_for_south_dakota_mountain(self):
        timezone_name, source = infer_timezone_from_merchant(zip_code="57701")
        self.assertEqual("America/Denver", timezone_name)
        self.assertEqual("zip_dataset", source)

    def test_infer_timezone_from_zip_for_north_dakota_mountain(self):
        timezone_name, source = infer_timezone_from_merchant(zip_code="58601")
        self.assertEqual("America/Denver", timezone_name)
        self.assertEqual("zip_dataset", source)

    def test_infer_timezone_from_zip_for_florida_panhandle_central(self):
        timezone_name, source = infer_timezone_from_merchant(zip_code="32501")
        self.assertEqual("America/Chicago", timezone_name)
        self.assertEqual("zip_dataset", source)

    def test_infer_timezone_from_zip_for_texas_mountain(self):
        timezone_name, source = infer_timezone_from_merchant(zip_code="79901")
        self.assertEqual("America/Denver", timezone_name)
        self.assertEqual("zip_dataset", source)

    def test_infer_timezone_from_zip_for_idaho_pacific(self):
        timezone_name, source = infer_timezone_from_merchant(zip_code="83814")
        self.assertEqual("America/Los_Angeles", timezone_name)
        self.assertEqual("zip_dataset", source)

    def test_infer_timezone_from_zip_for_oregon_eastern_time_zone(self):
        timezone_name, source = infer_timezone_from_merchant(zip_code="97914")
        self.assertEqual("America/Boise", timezone_name)
        self.assertEqual("zip_dataset", source)

    def test_normalize_timezone_name_accepts_windows_and_iana_aliases(self):
        self.assertEqual("Asia/Ho_Chi_Minh", normalize_timezone_name("SE Asia Standard Time"))
        self.assertEqual("Asia/Ho_Chi_Minh", normalize_timezone_name("Asia/Saigon"))
        self.assertEqual("America/New_York", normalize_timezone_name("america/new_york"))
        self.assertEqual("America/Boise", normalize_timezone_name("America/Boise"))

    def test_resolve_deadline_timezone_prefers_manual_over_existing_and_zip(self):
        timezone_name, source = resolve_deadline_timezone(
            explicit_timezone="Pacific Standard Time",
            existing_timezone="America/New_York",
            zip_code="57701",
            viewer_timezone="Asia/Ho_Chi_Minh",
        )
        self.assertEqual("America/Los_Angeles", timezone_name)
        self.assertEqual("manual", source)

    def test_resolve_deadline_timezone_reuses_existing_before_zip_lookup(self):
        timezone_name, source = resolve_deadline_timezone(
            existing_timezone="America/New_York",
            zip_code="57701",
            viewer_timezone="Asia/Ho_Chi_Minh",
        )
        self.assertEqual("America/New_York", timezone_name)
        self.assertEqual("existing", source)

    def test_resolve_deadline_timezone_rejects_invalid_manual_timezone(self):
        timezone_name, source = resolve_deadline_timezone(
            explicit_timezone="Mars/Olympus_Mons",
            zip_code="20003",
        )
        self.assertEqual("", timezone_name)
        self.assertEqual("invalid", source)

    def test_california_deadline_converts_to_vietnam_with_pdt_label(self):
        deadline_at_utc = convert_local_to_utc(
            datetime.combine(date(2026, 4, 25), time(17, 0)),
            "America/Los_Angeles",
        )
        payload = serialize_deadline_for_view(
            legacy_deadline_date=date(2026, 4, 25),
            legacy_deadline_time=time(17, 0),
            deadline_at_utc=deadline_at_utc,
            deadline_timezone="America/Los_Angeles",
            viewer_timezone="Asia/Ho_Chi_Minh",
        )
        self.assertEqual("26-04-2026 07:00 AM", payload["deadline"])
        self.assertEqual("25-04-2026 05:00 PM PDT", payload["deadline_original_label"])
        self.assertEqual("26-04-2026 07:00 AM ICT", payload["deadline_vn_label"])

    def test_new_york_deadline_converts_to_vietnam_with_edt_label(self):
        deadline_at_utc = convert_local_to_utc(
            datetime.combine(date(2026, 4, 25), time(17, 0)),
            "America/New_York",
        )
        payload = serialize_deadline_for_view(
            legacy_deadline_date=date(2026, 4, 25),
            legacy_deadline_time=time(17, 0),
            deadline_at_utc=deadline_at_utc,
            deadline_timezone="America/New_York",
            viewer_timezone="Asia/Ho_Chi_Minh",
        )
        self.assertEqual("26-04-2026 04:00 AM", payload["deadline"])
        self.assertEqual("25-04-2026 05:00 PM EDT", payload["deadline_original_label"])
        self.assertEqual("26-04-2026 04:00 AM ICT", payload["deadline_vn_label"])

    def test_arizona_deadline_keeps_mst_in_summer(self):
        deadline_at_utc = convert_local_to_utc(
            datetime.combine(date(2026, 7, 25), time(17, 0)),
            "America/Phoenix",
        )
        payload = serialize_deadline_for_view(
            legacy_deadline_date=date(2026, 7, 25),
            legacy_deadline_time=time(17, 0),
            deadline_at_utc=deadline_at_utc,
            deadline_timezone="America/Phoenix",
            viewer_timezone="Asia/Ho_Chi_Minh",
        )
        self.assertEqual("26-07-2026 07:00 AM", payload["deadline"])
        self.assertEqual("25-07-2026 05:00 PM MST", payload["deadline_original_label"])
        self.assertEqual("26-07-2026 07:00 AM ICT", payload["deadline_vn_label"])

    def test_south_dakota_zip_uses_mdt_in_summer(self):
        timezone_name, _source = infer_timezone_from_merchant(zip_code="57701")
        deadline_at_utc = convert_local_to_utc(
            datetime.combine(date(2026, 7, 25), time(17, 0)),
            timezone_name,
        )
        payload = serialize_deadline_for_view(
            legacy_deadline_date=date(2026, 7, 25),
            legacy_deadline_time=time(17, 0),
            deadline_at_utc=deadline_at_utc,
            deadline_timezone=timezone_name,
            viewer_timezone="Asia/Ho_Chi_Minh",
        )
        self.assertEqual("25-07-2026 05:00 PM MDT", payload["deadline_original_label"])


if __name__ == "__main__":
    unittest.main()
