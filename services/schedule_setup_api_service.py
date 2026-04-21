import requests

from services.app_config import API_BASE_URL


def get_schedule_setup_employees_api(action_by, department, team="General"):
    try:
        response = requests.get(
            f"{API_BASE_URL}/schedule-setup/employees",
            params={"action_by": action_by, "department": department, "team": team},
            timeout=20,
        )
        return response.json()
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout while loading employees."}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"API connection error: {e}"}


def save_schedule_setup_employee_api(payload):
    try:
        response = requests.post(
            f"{API_BASE_URL}/schedule-setup/save",
            json=payload,
            timeout=25,
        )
        return response.json()
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout while saving employee setup."}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"API connection error: {e}"}


def set_schedule_setup_active_api(username, active, action_by):
    try:
        response = requests.post(
            f"{API_BASE_URL}/schedule-setup/set-active",
            json={"username": username, "active": active, "action_by": action_by},
            timeout=20,
        )
        return response.json()
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout while updating employee status."}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"API connection error: {e}"}
