import requests

API_BASE_URL = "https://underline-steersman-crepe.ngrok-free.dev"


def login_api(username, password):
    try:
        response = requests.post(
            f"{API_BASE_URL}/login",
            json={"username": username, "password": password},
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
