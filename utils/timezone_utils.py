import os
import platform
from datetime import datetime

try:
    import winreg
except ImportError:  # pragma: no cover - non-Windows fallback
    winreg = None


DEFAULT_VIEWER_TIMEZONE = "Asia/Ho_Chi_Minh"

_WINDOWS_TO_IANA = {
    "UTC": "UTC",
    "SE Asia Standard Time": "Asia/Ho_Chi_Minh",
    "Eastern Standard Time": "America/New_York",
    "Central Standard Time": "America/Chicago",
    "Mountain Standard Time": "America/Denver",
    "US Mountain Standard Time": "America/Phoenix",
    "Pacific Standard Time": "America/Los_Angeles",
    "Alaskan Standard Time": "America/Anchorage",
    "Hawaiian Standard Time": "Pacific/Honolulu",
}


def detect_local_timezone_name():
    env_value = str(os.environ.get("DELTA_VIEWER_TIMEZONE", "") or "").strip()
    if env_value:
        return env_value

    if platform.system() == "Windows" and winreg is not None:
        registry_value = _read_windows_timezone_key_name()
        if registry_value:
            mapped_value = _WINDOWS_TO_IANA.get(registry_value)
            if mapped_value:
                return mapped_value

    return DEFAULT_VIEWER_TIMEZONE


def _read_windows_timezone_key_name():
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation",
        ) as registry_key:
            try:
                return str(winreg.QueryValueEx(registry_key, "TimeZoneKeyName")[0] or "").strip()
            except FileNotFoundError:
                return str(winreg.QueryValueEx(registry_key, "StandardName")[0] or "").strip()
    except Exception:
        return ""


try:  # pragma: no cover - thin wrapper around shared backend logic
    from services.timezone_service import (
        normalize_timezone_name as _normalize_timezone_name,
        resolve_deadline_timezone as _resolve_deadline_timezone,
        serialize_deadline_for_view as _serialize_deadline_for_view,
    )
except ModuleNotFoundError:
    try:
        from backend_server.services.timezone_service import (
            normalize_timezone_name as _normalize_timezone_name,
            resolve_deadline_timezone as _resolve_deadline_timezone,
            serialize_deadline_for_view as _serialize_deadline_for_view,
        )
    except ModuleNotFoundError:  # pragma: no cover - fallback for alternate launch paths
        _normalize_timezone_name = None
        _resolve_deadline_timezone = None
        _serialize_deadline_for_view = None


def build_deadline_preview(
    deadline_date_text="",
    deadline_time_text="",
    deadline_period_text="",
    merchant_timezone="",
    merchant_raw_text="",
    merchant_name="",
    zip_code="",
    existing_timezone="",
    viewer_timezone="",
):
    parsed_date, parsed_time = _parse_deadline_inputs(
        deadline_date_text,
        deadline_time_text,
        deadline_period_text,
    )
    if parsed_date is None:
        return {}

    if (
        _normalize_timezone_name is None
        or _resolve_deadline_timezone is None
        or _serialize_deadline_for_view is None
    ):
        return {}

    resolved_viewer_timezone = (
        _normalize_timezone_name(viewer_timezone)
        or detect_local_timezone_name()
    )
    resolved_timezone, timezone_source = _resolve_deadline_timezone(
        explicit_timezone=merchant_timezone,
        merchant_raw_text=merchant_raw_text,
        merchant_name=merchant_name or merchant_raw_text,
        zip_code=zip_code,
        existing_timezone=existing_timezone,
        viewer_timezone=resolved_viewer_timezone,
    )
    preview = _serialize_deadline_for_view(
        parsed_date,
        parsed_time,
        deadline_timezone=resolved_timezone,
        viewer_timezone=resolved_viewer_timezone,
    )
    preview["deadline_timezone_source"] = timezone_source
    return preview


def format_deadline_hint_text(preview=None):
    preview = preview or {}
    lines = ["Nhap theo gio bang khach."]
    vnt_text = str(preview.get("deadline_vn_label", "")).strip()
    ust_text = (
        str(preview.get("deadline_ust_label", "")).strip()
        or str(preview.get("deadline_original_label", "")).strip()
    )
    if vnt_text:
        lines.append(f"VNT: {vnt_text}")
    if ust_text:
        lines.append(f"UST: {ust_text}")
    if len(lines) == 1:
        lines.append("VNT se hien sau khi xac dinh timezone.")
    return "\n".join(lines)


def _parse_deadline_inputs(deadline_date_text, deadline_time_text, deadline_period_text):
    parsed_date = _parse_deadline_date(deadline_date_text)
    if parsed_date is None:
        return None, None

    parsed_time = _parse_deadline_time(deadline_time_text, deadline_period_text)
    return parsed_date, parsed_time


def _parse_deadline_date(value):
    text = str(value or "").strip()
    if not text:
        return None

    for pattern in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def _parse_deadline_time(deadline_time_text, deadline_period_text):
    time_text = str(deadline_time_text or "").strip().upper()
    period_text = str(deadline_period_text or "").strip().upper()
    if not time_text:
        return None

    if period_text:
        for pattern in ("%I:%M %p", "%I %p"):
            try:
                return datetime.strptime(f"{time_text} {period_text}", pattern).time()
            except ValueError:
                continue

    for pattern in ("%I:%M %p", "%I %p", "%H:%M", "%H"):
        try:
            return datetime.strptime(time_text, pattern).time()
        except ValueError:
            continue
    return None
