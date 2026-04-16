import requests

API_BASE_URL = "https://underline-steersman-crepe.ngrok-free.dev"


def login_api(username, password):
    try:
        response = requests.post(
            f"{API_BASE_URL}/login",
            json={"username": username, "password": password},
            timeout=10,
        )

        return response.json()

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

        return response.json()

    except Exception as e:
        return {"success": False, "message": str(e)}


def get_pin_status_api(username):
    try:
        response = requests.get(f"{API_BASE_URL}/pin-status/{username}", timeout=15)
        return response.json()
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout khi kiểm tra PIN"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lỗi kết nối API: {e}"}


def set_pin_api(username, pin_code, action_by):
    try:
        payload = {"username": username, "pin_code": pin_code, "action_by": action_by}
        response = requests.post(f"{API_BASE_URL}/set-pin", json=payload, timeout=15)
        return response.json()
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
        return response.json()
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
        return response.json()
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout khi đổi PIN"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lỗi kết nối API: {e}"}


def get_tech_schedule_api(week_start):
    try:
        response = requests.get(
            f"{API_BASE_URL}/tech-schedule",
            params={"week_start": week_start},
            timeout=20,
        )
        return response.json()
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
        return response.json()
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout khi lấy tổng hợp nghỉ theo tháng"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lỗi kết nối API: {e}"}
