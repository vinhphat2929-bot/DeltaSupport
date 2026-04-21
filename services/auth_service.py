import threading
import time
from copy import deepcopy
from datetime import date

import requests

from services.app_config import API_BASE_URL

PIN_STATUS_CACHE_TTL_SECONDS = 180
_pin_status_cache = {}
_pin_status_pending = {}
_pin_status_lock = threading.Lock()


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


def _normalize_pin_status_key(username):
    return str(username or "").strip().lower()


def _get_cached_pin_status(username):
    cache_key = _normalize_pin_status_key(username)
    if not cache_key:
        return None

    with _pin_status_lock:
        cache_entry = _pin_status_cache.get(cache_key)
        if not cache_entry:
            return None
        if time.monotonic() >= cache_entry.get("expires_at", 0):
            _pin_status_cache.pop(cache_key, None)
            return None
        return deepcopy(cache_entry.get("value") or {})


def _set_cached_pin_status(username, value):
    cache_key = _normalize_pin_status_key(username)
    if not cache_key:
        return

    with _pin_status_lock:
        _pin_status_cache[cache_key] = {
            "value": deepcopy(value or {}),
            "expires_at": time.monotonic() + PIN_STATUS_CACHE_TTL_SECONDS,
        }


def clear_pin_status_cache(username=""):
    cache_key = _normalize_pin_status_key(username)
    with _pin_status_lock:
        if cache_key:
            _pin_status_cache.pop(cache_key, None)
            return
        _pin_status_cache.clear()


def login_api(username, password):
    try:
        response = requests.post(
            f"{API_BASE_URL}/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        return _safe_json_response(response, fallback_message="Login failed.")

    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "KhÃ´ng káº¿t ná»‘i Ä‘Æ°á»£c tá»›i server"}

    except Exception as e:
        return {"success": False, "message": str(e)}


def change_password_api(username, old_password, new_password):
    try:
        response = requests.post(
            f"{API_BASE_URL}/change-password",
            json={
                "username": username,
                "old_password": old_password,
                "new_password": new_password,
            },
            timeout=10,
        )
        return _safe_json_response(response, fallback_message="Change password failed.")

    except Exception as e:
        return {"success": False, "message": str(e)}


def get_pin_status_api(username):
    cached_result = _get_cached_pin_status(username)
    if cached_result is not None:
        return cached_result

    cache_key = _normalize_pin_status_key(username)
    wait_event = None
    is_owner = False
    if cache_key:
        with _pin_status_lock:
            wait_event = _pin_status_pending.get(cache_key)
            if wait_event is None:
                wait_event = threading.Event()
                _pin_status_pending[cache_key] = wait_event
                is_owner = True

        if not is_owner:
            wait_event.wait(timeout=16)
            cached_after_wait = _get_cached_pin_status(username)
            if cached_after_wait is not None:
                return cached_after_wait

    try:
        response = requests.get(f"{API_BASE_URL}/pin-status/{username}", timeout=15)
        result = _safe_json_response(response, fallback_message="Unable to check PIN status.")
        if result.get("success"):
            _set_cached_pin_status(username, result)
        return result
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout khi kiá»ƒm tra PIN"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lá»—i káº¿t ná»‘i API: {e}"}
    finally:
        if cache_key and is_owner:
            with _pin_status_lock:
                event = _pin_status_pending.pop(cache_key, None)
            if event is not None:
                event.set()


def set_pin_api(username, pin_code, action_by):
    try:
        payload = {"username": username, "pin_code": pin_code, "action_by": action_by}
        response = requests.post(f"{API_BASE_URL}/set-pin", json=payload, timeout=15)
        result = _safe_json_response(response, fallback_message="Unable to set PIN.")
        if result.get("success"):
            clear_pin_status_cache(username)
        return result
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout khi táº¡o PIN"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lá»—i káº¿t ná»‘i API: {e}"}


def verify_pin_api(username, pin_code, action_by=""):
    try:
        payload = {
            "username": username,
            "pin_code": pin_code,
            "action_by": action_by or username,
        }
        response = requests.post(f"{API_BASE_URL}/verify-pin", json=payload, timeout=15)
        return _safe_json_response(response, fallback_message="Unable to verify PIN.")
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout khi xÃ¡c thá»±c PIN"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lá»—i káº¿t ná»‘i API: {e}"}


def change_pin_api(username, old_pin, new_pin, action_by):
    try:
        payload = {
            "username": username,
            "old_pin": old_pin,
            "new_pin": new_pin,
            "action_by": action_by,
        }
        response = requests.post(f"{API_BASE_URL}/change-pin", json=payload, timeout=15)
        result = _safe_json_response(response, fallback_message="Unable to change PIN.")
        if result.get("success"):
            clear_pin_status_cache(username)
        return result
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout khi Ä‘á»•i PIN"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lá»—i káº¿t ná»‘i API: {e}"}


def send_forgot_pin_otp_api(username):
    try:
        response = requests.post(
            f"{API_BASE_URL}/forgot-pin/send-otp",
            json={"username": username},
            timeout=15,
        )
        return _safe_json_response(response, fallback_message="Unable to send OTP.")
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout while sending OTP"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"API connection error: {e}"}


def reset_pin_with_otp_api(username, otp, new_pin, action_by=""):
    try:
        response = requests.post(
            f"{API_BASE_URL}/forgot-pin/reset",
            json={
                "username": username,
                "otp": otp,
                "new_pin": new_pin,
                "action_by": action_by or username,
            },
            timeout=15,
        )
        result = _safe_json_response(response, fallback_message="Unable to reset PIN.")
        if result.get("success"):
            clear_pin_status_cache(username)
        return result
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout while resetting PIN"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"API connection error: {e}"}


def get_tech_schedule_api(week_start):
    try:
        response = requests.get(
            f"{API_BASE_URL}/tech-schedule",
            params={"week_start": week_start},
            timeout=20,
        )
        return _safe_json_response(response, fallback_message="Unable to load tech schedule.")
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout khi láº¥y tech schedule"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lá»—i káº¿t ná»‘i API: {e}"}


def get_tech_schedule_month_summary_api(month, year):
    try:
        response = requests.get(
            f"{API_BASE_URL}/tech-schedule/month-summary",
            params={"month": month, "year": year},
            timeout=20,
        )
        return _safe_json_response(response, fallback_message="Unable to load month summary.")
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout khi láº¥y tá»•ng há»£p nghá»‰ theo thÃ¡ng"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lá»—i káº¿t ná»‘i API: {e}"}
