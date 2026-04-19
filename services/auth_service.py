import requests
from datetime import date

API_BASE_URL = "https://underline-steersman-crepe.ngrok-free.dev"

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


def login_api(username, password):
    try:
        response = requests.post(
            f"{API_BASE_URL}/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        return _safe_json_response(response, fallback_message="Login failed.")

    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Không kết nối được tới server"}

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
    try:
        response = requests.get(f"{API_BASE_URL}/pin-status/{username}", timeout=15)
        return _safe_json_response(response, fallback_message="Unable to check PIN status.")
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout khi kiểm tra PIN"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lỗi kết nối API: {e}"}


def set_pin_api(username, pin_code, action_by):
    try:
        payload = {"username": username, "pin_code": pin_code, "action_by": action_by}
        response = requests.post(f"{API_BASE_URL}/set-pin", json=payload, timeout=15)
        return _safe_json_response(response, fallback_message="Unable to set PIN.")
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout khi tạo PIN"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lỗi kết nối API: {e}"}


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
        return {"success": False, "message": "Timeout khi xác thực PIN"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lỗi kết nối API: {e}"}


def change_pin_api(username, old_pin, new_pin, action_by):
    try:
        payload = {
            "username": username,
            "old_pin": old_pin,
            "new_pin": new_pin,
            "action_by": action_by,
        }
        response = requests.post(f"{API_BASE_URL}/change-pin", json=payload, timeout=15)
        return _safe_json_response(response, fallback_message="Unable to change PIN.")
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout khi đổi PIN"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lỗi kết nối API: {e}"}


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
        return _safe_json_response(response, fallback_message="Unable to reset PIN.")
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
        return {"success": False, "message": "Timeout khi lấy tech schedule"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lỗi kết nối API: {e}"}


def get_tech_schedule_month_summary_api(month, year):
    try:
        response = requests.get(
            f"{API_BASE_URL}/tech-schedule/month-summary",
            params={"month": month, "year": year},
            timeout=20,
        )
        return _safe_json_response(response, fallback_message="Unable to load month summary.")
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout khi lấy tổng hợp nghỉ theo tháng"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lỗi kết nối API: {e}"}
