import re
from datetime import datetime, time, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from zip2tz import timezone as lookup_zip_timezone_dataset


DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"

_TIMEZONE_ALIASES = {
    "asia/saigon": "Asia/Ho_Chi_Minh",
    "se asia standard time": "Asia/Ho_Chi_Minh",
    "utc": "UTC",
    "eastern standard time": "America/New_York",
    "central standard time": "America/Chicago",
    "mountain standard time": "America/Denver",
    "us mountain standard time": "America/Phoenix",
    "pacific standard time": "America/Los_Angeles",
    "alaskan standard time": "America/Anchorage",
    "hawaiian standard time": "Pacific/Honolulu",
}

_DISPLAY_ABBREVIATION_ALIASES = {
    "Asia/Ho_Chi_Minh": "ICT",
    "UTC": "UTC",
}


def normalize_timezone_name(value):
    text = str(value or "").strip()
    if not text:
        return ""

    alias_value = _TIMEZONE_ALIASES.get(text.lower(), "")
    candidates = [alias_value] if alias_value else []

    casefold_match = _get_timezone_casefold_map().get(text.casefold(), "")
    if casefold_match:
        candidates.append(casefold_match)
    else:
        candidates.append(text)

    for candidate in candidates:
        if _is_valid_timezone(candidate):
            return candidate
    return ""


def is_supported_timezone(value):
    return bool(normalize_timezone_name(value))


def get_timezone_abbreviation(timezone_name, dt_value):
    canonical_name = normalize_timezone_name(timezone_name) or DEFAULT_TIMEZONE
    if dt_value is None:
        return _DISPLAY_ABBREVIATION_ALIASES.get(canonical_name, "")

    localized_dt = _ensure_local_datetime(dt_value, canonical_name)
    return _DISPLAY_ABBREVIATION_ALIASES.get(
        canonical_name,
        localized_dt.tzname() or canonical_name,
    )


def convert_local_to_utc(dt_value, timezone_name):
    canonical_name = normalize_timezone_name(timezone_name) or DEFAULT_TIMEZONE
    if dt_value is None:
        return None

    localized_dt = _ensure_local_datetime(dt_value, canonical_name)
    return localized_dt.astimezone(timezone.utc).replace(tzinfo=None)


def convert_utc_to_local(dt_value, timezone_name):
    canonical_name = normalize_timezone_name(timezone_name) or DEFAULT_TIMEZONE
    if dt_value is None:
        return None

    utc_dt = _ensure_utc_datetime(dt_value)
    return utc_dt.astimezone(ZoneInfo(canonical_name)).replace(tzinfo=None)


def current_local_datetime(timezone_name):
    canonical_name = normalize_timezone_name(timezone_name) or DEFAULT_TIMEZONE
    return datetime.now(timezone.utc).astimezone(ZoneInfo(canonical_name)).replace(tzinfo=None)


def current_local_date(timezone_name):
    return current_local_datetime(timezone_name).date()


def extract_zip_code(*values):
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        match = re.search(r"\b(\d{5})(?:-\d{4})?\b", text)
        if match:
            return match.group(1)
    return ""


@lru_cache(maxsize=10000)
def lookup_timezone_by_zip(zip_code):
    normalized_zip = extract_zip_code(zip_code)
    if not normalized_zip:
        return ""

    dataset_timezone = lookup_zip_timezone_dataset(normalized_zip)
    return normalize_timezone_name(dataset_timezone)


def infer_timezone_from_merchant(raw_text="", merchant_name="", zip_code=""):
    normalized_zip = extract_zip_code(zip_code, raw_text, merchant_name)
    if not normalized_zip:
        return "", ""

    timezone_name = lookup_timezone_by_zip(normalized_zip)
    if not timezone_name:
        return "", ""
    return timezone_name, "zip_dataset"


def resolve_deadline_timezone(
    explicit_timezone="",
    merchant_raw_text="",
    merchant_name="",
    zip_code="",
    existing_timezone="",
    viewer_timezone="",
):
    explicit_text = str(explicit_timezone or "").strip()
    if explicit_text:
        normalized_explicit = normalize_timezone_name(explicit_timezone)
        if not normalized_explicit:
            return "", "invalid"
        return normalized_explicit, "manual"

    normalized_existing = normalize_timezone_name(existing_timezone)
    if normalized_existing:
        return normalized_existing, "existing"

    inferred_timezone, inferred_source = infer_timezone_from_merchant(
        raw_text=merchant_raw_text,
        merchant_name=merchant_name,
        zip_code=zip_code,
    )
    if inferred_timezone:
        return inferred_timezone, inferred_source

    normalized_viewer = normalize_timezone_name(viewer_timezone)
    if normalized_viewer:
        return normalized_viewer, "viewer"

    return DEFAULT_TIMEZONE, "default"


def serialize_deadline_for_view(
    legacy_deadline_date,
    legacy_deadline_time,
    deadline_at_utc=None,
    deadline_timezone="",
    viewer_timezone="",
):
    has_time = legacy_deadline_time is not None
    canonical_deadline_timezone = normalize_timezone_name(deadline_timezone) or DEFAULT_TIMEZONE
    canonical_viewer_timezone = normalize_timezone_name(viewer_timezone) or canonical_deadline_timezone
    normalized_deadline_at_utc = _coerce_datetime_value(deadline_at_utc)

    if normalized_deadline_at_utc is None and legacy_deadline_date:
        base_local_dt = datetime.combine(
            legacy_deadline_date,
            legacy_deadline_time or time(0, 0),
        )
        normalized_deadline_at_utc = convert_local_to_utc(base_local_dt, canonical_deadline_timezone)

    if normalized_deadline_at_utc is None:
        original_local_dt = None
        viewer_local_dt = None
        vn_local_dt = None
    else:
        original_local_dt = convert_utc_to_local(normalized_deadline_at_utc, canonical_deadline_timezone)
        viewer_local_dt = convert_utc_to_local(normalized_deadline_at_utc, canonical_viewer_timezone)
        vn_local_dt = convert_utc_to_local(normalized_deadline_at_utc, DEFAULT_TIMEZONE)

    original_date_text = _format_date(
        original_local_dt.date() if original_local_dt else legacy_deadline_date
    )
    original_time_text, original_period = _format_time_parts(
        original_local_dt.time() if (original_local_dt and has_time) else legacy_deadline_time
    )
    original_full = _compose_deadline_text(
        original_date_text,
        original_time_text,
        original_period,
        _format_abbreviation(
            canonical_deadline_timezone,
            original_local_dt,
            has_time,
        ),
    )

    viewer_date_text = _format_date(
        viewer_local_dt.date() if viewer_local_dt else legacy_deadline_date
    )
    viewer_time_text, viewer_period = _format_time_parts(
        viewer_local_dt.time() if (viewer_local_dt and has_time) else legacy_deadline_time
    )
    viewer_full = _compose_deadline_text(
        viewer_date_text,
        viewer_time_text,
        viewer_period,
        "",
    )

    vn_date_text = _format_date(
        vn_local_dt.date() if vn_local_dt else legacy_deadline_date
    )
    vn_time_text, vn_period = _format_time_parts(
        vn_local_dt.time() if (vn_local_dt and has_time) else legacy_deadline_time
    )
    vn_full = _compose_deadline_text(
        vn_date_text,
        vn_time_text,
        vn_period,
        _format_abbreviation(
            DEFAULT_TIMEZONE,
            vn_local_dt,
            has_time,
        ),
    )

    return {
        "deadline": viewer_full,
        "deadline_date": viewer_date_text,
        "deadline_time": viewer_time_text,
        "deadline_period": viewer_period,
        "deadline_original_label": original_full,
        "deadline_original_date": original_date_text,
        "deadline_original_time": original_time_text,
        "deadline_original_period": original_period,
        "deadline_ust_label": original_full,
        "deadline_ust_date": original_date_text,
        "deadline_ust_time": original_time_text,
        "deadline_ust_period": original_period,
        "deadline_vn_label": vn_full,
        "deadline_vn_date": vn_date_text,
        "deadline_vn_time": vn_time_text,
        "deadline_vn_period": vn_period,
        "deadline_timezone": canonical_deadline_timezone,
        "deadline_viewer_timezone": canonical_viewer_timezone,
        "deadline_at_utc": (
            normalized_deadline_at_utc.strftime("%Y-%m-%d %H:%M:%S")
            if normalized_deadline_at_utc
            else ""
        ),
    }


@lru_cache(maxsize=512)
def _is_valid_timezone(timezone_name):
    try:
        ZoneInfo(timezone_name)
        return True
    except ZoneInfoNotFoundError:
        return False


@lru_cache(maxsize=1)
def _get_timezone_casefold_map():
    return {
        timezone_name.casefold(): timezone_name
        for timezone_name in available_timezones()
    }


def _ensure_local_datetime(dt_value, timezone_name):
    local_timezone = ZoneInfo(timezone_name)
    if dt_value.tzinfo is not None:
        return dt_value.astimezone(local_timezone)
    return dt_value.replace(tzinfo=local_timezone)


def _ensure_utc_datetime(dt_value):
    if dt_value.tzinfo is not None:
        return dt_value.astimezone(timezone.utc)
    return dt_value.replace(tzinfo=timezone.utc)


def _coerce_datetime_value(value):
    if isinstance(value, datetime):
        return value

    text = str(value or "").strip()
    if not text:
        return None

    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return None


def _format_date(value):
    if not value:
        return ""
    return value.strftime("%d-%m-%Y")


def _format_time_parts(value):
    if not value:
        return "", "AM"
    return value.strftime("%I:%M"), value.strftime("%p")


def _format_abbreviation(timezone_name, local_dt, has_time):
    if not has_time or not local_dt:
        return ""
    return get_timezone_abbreviation(timezone_name, local_dt)


def _compose_deadline_text(date_text, time_text, period_text, abbreviation_text=""):
    if not date_text:
        return ""

    if not time_text:
        return date_text

    full_text = f"{date_text} {time_text} {period_text}"
    if abbreviation_text:
        full_text = f"{full_text} {abbreviation_text}"
    return full_text


__all__ = [
    "DEFAULT_TIMEZONE",
    "convert_local_to_utc",
    "convert_utc_to_local",
    "current_local_date",
    "current_local_datetime",
    "extract_zip_code",
    "get_timezone_abbreviation",
    "infer_timezone_from_merchant",
    "is_supported_timezone",
    "lookup_timezone_by_zip",
    "normalize_timezone_name",
    "resolve_deadline_timezone",
    "serialize_deadline_for_view",
]
