import requests

from services.app_config import API_BASE_URL


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

        response.raise_for_status()
        return response.json()

    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Không kết nối được tới API server"}
    except requests.exceptions.Timeout:
        return {"success": False, "message": "API phản hồi quá chậm"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lỗi request: {str(e)}"}
