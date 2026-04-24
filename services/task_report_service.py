from copy import deepcopy
import threading
import time

import requests

from services.app_config import API_BASE_URL


REPORT_LIST_CACHE_TTL_SECONDS = 60
TECHNICIAN_CACHE_TTL_SECONDS = 600

_report_list_cache = {}
_technician_cache = {}
_cache_lock = threading.Lock()


def _normalize_text(value):
    return str(value or "").strip()


def _safe_json_response(response, fallback_message="Server returned an invalid response."):
    content_type = str(response.headers.get("Content-Type", "")).lower()
    status = getattr(response, "status_code", None)
    text = ""
    try:
        text = response.text or ""
    except Exception:
        text = ""

    if "application/json" in content_type:
        try:
            return response.json()
        except Exception:
            preview = (text.strip()[:250] + "...") if len(text.strip()) > 250 else text.strip()
            return {
                "success": False,
                "message": f"{fallback_message} (HTTP {status}) JSON parse failed. Response: {preview}",
            }

    preview = (text.strip()[:250] + "...") if len(text.strip()) > 250 else text.strip()
    if not preview:
        preview = "<empty response body>"
    return {
        "success": False,
        "message": f"{fallback_message} (HTTP {status}) Content-Type: {content_type or '<missing>'}. Response: {preview}",
    }


def _normalize_report_item(item):
    payload = deepcopy(item or {})
    return {
        "report_id": payload.get("report_id"),
        "report_date": _normalize_text(payload.get("report_date")),
        "report_time": _normalize_text(payload.get("report_time")),
        "merchant": _normalize_text(payload.get("merchant")),
        "caller_phone": _normalize_text(payload.get("caller_phone")),
        "problem": _normalize_text(payload.get("problem")),
        "solution": _normalize_text(payload.get("solution")),
        "processing": _normalize_text(payload.get("processing")),
        "technician_username": _normalize_text(payload.get("technician_username")),
        "technician_display_name": _normalize_text(payload.get("technician_display_name")),
        "created_by_username": _normalize_text(payload.get("created_by_username")),
        "created_by_display_name": _normalize_text(payload.get("created_by_display_name")),
        "updated_by_username": _normalize_text(payload.get("updated_by_username")),
        "updated_by_display_name": _normalize_text(payload.get("updated_by_display_name")),
        "created_at": _normalize_text(payload.get("created_at")),
        "updated_at": _normalize_text(payload.get("updated_at")),
    }


def _normalize_technician_option(item):
    payload = item or {}
    return {
        "username": _normalize_text(payload.get("username")),
        "display_name": _normalize_text(payload.get("display_name")) or _normalize_text(payload.get("username")),
    }


def _report_cache_key(action_by, from_date, to_date, search_text=""):
    return (
        _normalize_text(action_by).lower(),
        _normalize_text(from_date),
        _normalize_text(to_date),
        _normalize_text(search_text).lower(),
    )


def _technician_cache_key(action_by, work_date, work_time):
    return (
        _normalize_text(action_by).lower(),
        _normalize_text(work_date),
        _normalize_text(work_time),
    )


def _get_cache(cache_dict, key):
    with _cache_lock:
        entry = cache_dict.get(key)
        if not entry:
            return None
        if time.monotonic() >= entry.get("expires_at", 0):
            cache_dict.pop(key, None)
            return None
        return deepcopy(entry.get("value"))


def _set_cache(cache_dict, key, value, ttl_seconds):
    with _cache_lock:
        cache_dict[key] = {
            "value": deepcopy(value),
            "expires_at": time.monotonic() + max(1, int(ttl_seconds)),
        }


def clear_task_report_cache():
    with _cache_lock:
        _report_list_cache.clear()
        _technician_cache.clear()


def clear_task_report_list_cache():
    with _cache_lock:
        _report_list_cache.clear()


class TaskReportService:
    def get_reports(self, action_by, from_date, to_date, search_text="", force=False):
        cache_key = _report_cache_key(action_by, from_date, to_date, search_text)
        if not force:
            cached = _get_cache(_report_list_cache, cache_key)
            if cached is not None:
                return cached

        try:
            response = requests.get(
                f"{API_BASE_URL}/task-reports",
                params={
                    "action_by": action_by,
                    "from_date": from_date,
                    "to_date": to_date,
                    "search": _normalize_text(search_text),
                },
                timeout=25,
            )
            payload = _safe_json_response(response, fallback_message="Unable to load task reports.")
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Timeout while loading task reports."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "message": f"API connection error: {exc}"}

        if not payload.get("success"):
            return payload

        result = {
            "success": True,
            "data": [_normalize_report_item(item) for item in payload.get("data", [])],
            "from_date": _normalize_text(payload.get("from_date")),
            "to_date": _normalize_text(payload.get("to_date")),
        }
        _set_cache(_report_list_cache, cache_key, result, REPORT_LIST_CACHE_TTL_SECONDS)
        return result

    def get_technicians(self, action_by, work_date="", work_time="", force=False):
        cache_key = _technician_cache_key(action_by, work_date, work_time)
        if not force:
            cached = _get_cache(_technician_cache, cache_key)
            if cached is not None:
                return cached

        try:
            response = requests.get(
                f"{API_BASE_URL}/task-reports/technicians",
                params={
                    "action_by": action_by,
                    "work_date": _normalize_text(work_date),
                    "work_time": _normalize_text(work_time),
                },
                timeout=20,
            )
            payload = _safe_json_response(response, fallback_message="Unable to load technicians.")
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Timeout while loading technicians."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "message": f"API connection error: {exc}"}

        if not payload.get("success"):
            return payload

        result = {
            "success": True,
            "data": [_normalize_technician_option(item) for item in payload.get("data", [])],
        }
        _set_cache(_technician_cache, cache_key, result, TECHNICIAN_CACHE_TTL_SECONDS)
        return result

    def create_report(self, payload):
        try:
            response = requests.post(
                f"{API_BASE_URL}/task-reports",
                json=payload,
                timeout=25,
            )
            result = _safe_json_response(response, fallback_message="Unable to save task report.")
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Timeout while saving task report."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "message": f"API connection error: {exc}"}

        if result.get("success") and result.get("data") is not None:
            result["data"] = _normalize_report_item(result.get("data"))
            clear_task_report_list_cache()
        return result

    def update_report(self, report_id, payload):
        try:
            response = requests.put(
                f"{API_BASE_URL}/task-reports/{report_id}",
                json=payload,
                timeout=25,
            )
            result = _safe_json_response(response, fallback_message="Unable to update task report.")
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Timeout while updating task report."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "message": f"API connection error: {exc}"}

        if result.get("success") and result.get("data") is not None:
            result["data"] = _normalize_report_item(result.get("data"))
            clear_task_report_list_cache()
        return result

    def delete_report(self, report_id, action_by):
        try:
            response = requests.delete(
                f"{API_BASE_URL}/task-reports/{report_id}",
                params={"action_by": action_by},
                timeout=25,
            )
            result = _safe_json_response(response, fallback_message="Unable to delete task report.")
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Timeout while deleting task report."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "message": f"API connection error: {exc}"}

        if result.get("success"):
            clear_task_report_list_cache()
        return result
