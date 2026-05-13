import requests

from services.app_config import API_BASE_URL


def _debug_task_update(message):
    print(f"[TaskFollow frontend update] {message}", flush=True)


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


def get_task_follow_handoff_options_api(action_by, task_date="", task_time="", task_period="", deadline_timezone=""):
    try:
        response = requests.get(
            f"{API_BASE_URL}/task-follows/handoff-options",
            params={
                "action_by": action_by,
                "task_date": str(task_date or "").strip(),
                "task_time": str(task_time or "").strip(),
                "task_period": str(task_period or "").strip(),
                "deadline_timezone": str(deadline_timezone or "").strip(),
            },
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
        url = f"{API_BASE_URL}/task-follows/{task_id}"
        _debug_task_update(f"before request task_id={task_id} url={url} method=PUT payload_keys={sorted((payload or {}).keys())}")
        response = requests.put(
            url,
            json=payload,
            timeout=25,
        )
        _debug_task_update(f"response status task_id={task_id} status={response.status_code}")
        try:
            result = response.json()
        except ValueError:
            result = {}
        if not isinstance(result, dict):
            result = {"data": result}
        _debug_task_update(f"parsed response task_id={task_id} result={result}")
        if response.ok and result.get("success") is not False:
            result["success"] = True
            result.setdefault("message", "Task updated successfully.")
        return result
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout while updating task."}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"API connection error: {e}"}
