import requests

API_BASE_URL = "https://underline-steersman-crepe.ngrok-free.dev"


def send_register_otp(email):
    try:
        response = requests.post(
            f"{API_BASE_URL}/send-register-otp", json={"email": email}, timeout=10
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Không kết nối được tới API server"}
    except requests.exceptions.Timeout:
        return {"success": False, "message": "API phản hồi quá chậm"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lỗi request: {str(e)}"}


def register_api(username, full_name, email, password, otp, department):
    try:
        response = requests.post(
            f"{API_BASE_URL}/register",
            json={
                "username": username,
                "full_name": full_name,
                "email": email,
                "password": password,
                "otp": otp,
                "department": department,
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Không kết nối được tới API server"}
    except requests.exceptions.Timeout:
        return {"success": False, "message": "API phản hồi quá chậm"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lỗi request: {str(e)}"}
