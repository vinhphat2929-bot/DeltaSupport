import requests

from services.auth_service import API_BASE_URL


def get_task_follows_api(action_by, search="", show_all=False, include_done=False):
    try:
        response = requests.get(
            f"{API_BASE_URL}/task-follows",
            params={
                "action_by": action_by,
                "search": search,
                "show_all": show_all,
                "include_done": include_done,
            },
            timeout=20,
        )
        return response.json()
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout while loading follow tasks."}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"API connection error: {e}"}


def get_task_follow_handoff_options_api(action_by):
    try:
        response = requests.get(
            f"{API_BASE_URL}/task-follows/handoff-options",
            params={"action_by": action_by},
            timeout=20,
        )
        return response.json()
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout while loading handoff options."}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"API connection error: {e}"}


def get_task_follow_detail_api(task_id, action_by=""):
    try:
        response = requests.get(
            f"{API_BASE_URL}/task-follows/{task_id}",
            params={"action_by": action_by},
            timeout=20,
        )
        return response.json()
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout while loading task detail."}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"API connection error: {e}"}


def create_task_follow_api(payload):
    try:
        response = requests.post(
            f"{API_BASE_URL}/task-follows",
            json=payload,
            timeout=25,
        )
        return response.json()
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout while creating task."}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"API connection error: {e}"}


def update_task_follow_api(task_id, payload):
    try:
        response = requests.put(
            f"{API_BASE_URL}/task-follows/{task_id}",
            json=payload,
            timeout=25,
        )
        return response.json()
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout while updating task."}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"API connection error: {e}"}
