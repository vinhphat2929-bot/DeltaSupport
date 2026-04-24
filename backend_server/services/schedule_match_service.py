import re
from datetime import date, datetime, timedelta

try:
    from services.timezone_service import (
        convert_local_to_utc,
        convert_utc_to_local,
        lookup_timezone_by_zip,
        normalize_timezone_name,
    )
except ModuleNotFoundError:
    from backend_server.services.timezone_service import (
        convert_local_to_utc,
        convert_utc_to_local,
        lookup_timezone_by_zip,
        normalize_timezone_name,
    )

EARLY_MORNING_SHIFT_CUTOFF_HOUR = 6
COMPANY_SCHEDULE_ZIP_CODE = "77072"
DEFAULT_COMPANY_SCHEDULE_TIMEZONE = "America/Chicago"


def normalize_schedule_text(value):
    return str(value or "").strip()


def get_company_schedule_timezone():
    return (
        normalize_timezone_name(lookup_timezone_by_zip(COMPANY_SCHEDULE_ZIP_CODE))
        or DEFAULT_COMPANY_SCHEDULE_TIMEZONE
    )


def get_schedule_time_range_text(us_time_range="", vn_time_range=""):
    return normalize_schedule_text(us_time_range) or normalize_schedule_text(vn_time_range)


def coerce_schedule_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = normalize_schedule_text(value)
    if not text:
        return None

    for pattern in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def normalize_meridiem_time_text(value):
    text = normalize_schedule_text(value).upper()
    if not text:
        return ""

    text = re.sub(r"(?<=\d)\.(?=\d)", ":", text)
    text = text.replace(".", "")
    text = re.sub(r"\s*:\s*", ":", text)
    text = re.sub(r"\bA\s*M\b", "AM", text)
    text = re.sub(r"\bP\s*M\b", "PM", text)
    text = re.sub(r"(?<=\d)(AM|PM)\b", r" \1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_schedule_time_value(value):
    normalized_text = normalize_meridiem_time_text(value)
    if not normalized_text:
        return None

    for pattern in ("%I:%M %p", "%I %p", "%H:%M", "%H"):
        try:
            return datetime.strptime(normalized_text, pattern).time()
        except ValueError:
            continue
    return None


def parse_schedule_time_range(range_text):
    text = normalize_schedule_text(range_text)
    if not text or "-" not in text:
        return None, None

    parts = re.split(r"\s*-\s*", text, maxsplit=1)
    if len(parts) != 2:
        return None, None

    start_time = parse_schedule_time_value(parts[0])
    end_time = parse_schedule_time_value(parts[1])
    if start_time is None or end_time is None:
        return None, None
    return start_time, end_time


def is_previous_workday_morning_shift(start_time, end_time):
    if start_time is None or end_time is None:
        return False

    return (
        start_time < end_time
        and start_time.hour < EARLY_MORNING_SHIFT_CUTOFF_HOUR
        and end_time.hour <= 12
    )


def get_schedule_candidate_dates(target_date, target_time=None):
    parsed_target_date = coerce_schedule_date(target_date)
    if parsed_target_date is None:
        return []

    candidate_dates = [parsed_target_date]
    if target_time is not None:
        candidate_dates.insert(0, parsed_target_date - timedelta(days=1))
    return candidate_dates


def convert_target_to_company_schedule_slot(target_date, target_time=None, source_timezone=""):
    parsed_target_date = coerce_schedule_date(target_date)
    if parsed_target_date is None:
        return None, None

    if target_time is None:
        return parsed_target_date, None

    normalized_source_timezone = normalize_timezone_name(source_timezone)
    if not normalized_source_timezone:
        return parsed_target_date, target_time

    target_utc = convert_local_to_utc(
        datetime.combine(parsed_target_date, target_time),
        normalized_source_timezone,
    )
    if target_utc is None:
        return parsed_target_date, target_time

    company_local_dt = convert_utc_to_local(
        target_utc,
        get_company_schedule_timezone(),
    )
    if company_local_dt is None:
        return parsed_target_date, target_time

    return (
        company_local_dt.date(),
        company_local_dt.time().replace(second=0, microsecond=0),
    )


def schedule_row_matches_target(work_date, status_code, time_range_text, target_date, target_time=None):
    if normalize_schedule_text(status_code).upper() != "WORK":
        return False

    work_date_value = coerce_schedule_date(work_date)
    target_date_value = coerce_schedule_date(target_date)
    if work_date_value is None or target_date_value is None:
        return False

    if target_time is None:
        return work_date_value == target_date_value

    start_time, end_time = parse_schedule_time_range(time_range_text)
    if start_time is None or end_time is None:
        return work_date_value == target_date_value

    shift_start = datetime.combine(work_date_value, start_time)
    shift_end = datetime.combine(work_date_value, end_time)
    if shift_end <= shift_start:
        shift_end += timedelta(days=1)
    elif (
        target_date_value == work_date_value + timedelta(days=1)
        and is_previous_workday_morning_shift(start_time, end_time)
    ):
        shift_start += timedelta(days=1)
        shift_end += timedelta(days=1)

    target_moment = datetime.combine(target_date_value, target_time)
    return shift_start <= target_moment <= shift_end
