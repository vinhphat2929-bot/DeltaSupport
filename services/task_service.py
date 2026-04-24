from copy import deepcopy

import requests

from services.app_config import API_BASE_URL
from utils.timezone_utils import detect_local_timezone_name


TASK_STATUSES = [
    "FOLLOW",
    "FOLLOW REQUEST",
    "SHIP OUT",
    "SET UP & TRAINING",
    "2ND TRAINING",
    "MISS TIP / CHARGE BACK",
    "DONE",
    "DEMO",
]


def _normalize_text(value):
    return str(value or "").strip()


def _normalize_status(value):
    normalized = _normalize_text(value).upper()
    if normalized == "CHECK TRACKING NUMBER":
        return "SHIP OUT"
    return normalized


def _normalize_task(task):
    item = deepcopy(task or {})
    item["task_id"] = item.get("task_id")
    item["task_date"] = _normalize_text(item.get("task_date"))
    item["merchant_raw"] = _normalize_text(item.get("merchant_raw"))
    item["merchant_name"] = _normalize_text(item.get("merchant_name"))
    item["zip_code"] = _normalize_text(item.get("zip_code"))
    item["phone"] = _normalize_text(item.get("phone"))
    item["tracking_number"] = _normalize_text(item.get("tracking_number")).upper()
    item["problem"] = _normalize_text(item.get("problem"))
    item["handoff_from_username"] = _normalize_text(item.get("handoff_from_username"))
    item["handoff_from"] = _normalize_text(item.get("handoff_from"))
    item["handoff_to_type"] = _normalize_text(item.get("handoff_to_type")).upper() or "TEAM"
    item["handoff_to_username"] = _normalize_text(item.get("handoff_to_username"))
    item["handoff_to_usernames"] = [
        _normalize_text(value)
        for value in (item.get("handoff_to_usernames") or [])
        if _normalize_text(value)
    ]
    item["handoff_to_display_names"] = [
        _normalize_text(value)
        for value in (item.get("handoff_to_display_names") or [])
        if _normalize_text(value)
    ]
    item["handoff_to"] = _normalize_text(item.get("handoff_to")) or "Tech Team"
    item["status"] = _normalize_status(item.get("status")) or "FOLLOW"
    item["deadline"] = _normalize_text(item.get("deadline"))
    item["deadline_date"] = _normalize_text(item.get("deadline_date"))
    item["deadline_time"] = _normalize_text(item.get("deadline_time")) or "08:00"
    item["deadline_period"] = _normalize_text(item.get("deadline_period")).upper() or "AM"
    item["deadline_original_label"] = _normalize_text(item.get("deadline_original_label"))
    item["deadline_original_date"] = _normalize_text(item.get("deadline_original_date"))
    item["deadline_original_time"] = _normalize_text(item.get("deadline_original_time"))
    item["deadline_original_period"] = _normalize_text(item.get("deadline_original_period")).upper() or "AM"
    item["deadline_ust_label"] = _normalize_text(item.get("deadline_ust_label")) or item["deadline_original_label"]
    item["deadline_ust_date"] = _normalize_text(item.get("deadline_ust_date")) or item["deadline_original_date"]
    item["deadline_ust_time"] = _normalize_text(item.get("deadline_ust_time")) or item["deadline_original_time"]
    item["deadline_ust_period"] = _normalize_text(item.get("deadline_ust_period")).upper() or item["deadline_original_period"]
    item["deadline_vn_label"] = _normalize_text(item.get("deadline_vn_label"))
    item["deadline_vn_date"] = _normalize_text(item.get("deadline_vn_date"))
    item["deadline_vn_time"] = _normalize_text(item.get("deadline_vn_time"))
    item["deadline_vn_period"] = _normalize_text(item.get("deadline_vn_period")).upper() or "AM"
    item["deadline_timezone"] = _normalize_text(item.get("deadline_timezone"))
    item["deadline_viewer_timezone"] = _normalize_text(item.get("deadline_viewer_timezone"))
    item["deadline_at_utc"] = _normalize_text(item.get("deadline_at_utc"))
    item["note"] = _normalize_text(item.get("note"))
    item["updated_at"] = _normalize_text(item.get("updated_at"))
    item["training_form"] = item.get("training_form") or []
    item["has_training_form"] = bool(item.get("has_training_form")) or bool(item["training_form"])
    item["training_started_at"] = _normalize_text(item.get("training_started_at"))
    item["training_started_by_username"] = _normalize_text(item.get("training_started_by_username"))
    item["training_started_by_display_name"] = _normalize_text(item.get("training_started_by_display_name"))
    item["history"] = item.get("history") or []
    item["is_optimistic"] = bool(item.get("is_optimistic"))
    item["is_saving"] = bool(item.get("is_saving"))
    item["error"] = _normalize_text(item.get("error"))
    return item


def _normalize_handoff_option(option):
    return {
        "username": _normalize_text((option or {}).get("username")),
        "display_name": _normalize_text((option or {}).get("display_name")) or "Tech Team",
        "type": _normalize_text((option or {}).get("type")).upper() or "TEAM",
    }


def _normalize_notification_item(item):
    payload = item or {}
    task_id = payload.get("task_id")
    return {
        "id": _normalize_text(payload.get("id")) or (f"task-{task_id}" if task_id not in ("", None) else ""),
        "task_id": task_id,
        "title": _normalize_text(payload.get("title")) or "New task assigned",
        "meta": _normalize_text(payload.get("meta")) or "Tap to open Task Follow",
        "task_section": _normalize_text(payload.get("task_section")) or "follow",
        "is_read": bool(payload.get("is_read")),
    }


class TaskService:
    def __init__(self, viewer_timezone=""):
        self.viewer_timezone = _normalize_text(viewer_timezone) or detect_local_timezone_name()

    def get_notification_unread_count(self, action_by):
        try:
            response = requests.get(
                f"{API_BASE_URL}/task-follows/notifications/count",
                params={
                    "action_by": action_by,
                    "viewer_timezone": self.viewer_timezone,
                },
                timeout=20,
            )
            payload = response.json()
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Timeout while loading notification count."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "message": f"API connection error: {exc}"}

        if not payload.get("success"):
            return payload

        return {
            "success": True,
            "unread_count": max(0, int(payload.get("unread_count", 0) or 0)),
            "latest_updated_at": _normalize_text(payload.get("latest_updated_at")),
        }

    def get_notification_items(self, action_by):
        try:
            response = requests.get(
                f"{API_BASE_URL}/task-follows/notifications",
                params={
                    "action_by": action_by,
                    "viewer_timezone": self.viewer_timezone,
                },
                timeout=20,
            )
            payload = response.json()
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Timeout while loading notifications."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "message": f"API connection error: {exc}"}

        if not payload.get("success"):
            return payload

        return {
            "success": True,
            "unread_count": max(0, int(payload.get("unread_count", 0) or 0)),
            "data": [_normalize_notification_item(item) for item in payload.get("data", [])],
        }

    def mark_notifications_as_read(self, action_by, task_ids):
        try:
            normalized_task_ids = []
            for raw_task_id in task_ids or []:
                try:
                    task_id = int(raw_task_id)
                except (TypeError, ValueError):
                    continue
                if task_id > 0 and task_id not in normalized_task_ids:
                    normalized_task_ids.append(task_id)

            response = requests.post(
                f"{API_BASE_URL}/task-follows/notifications/read",
                json={
                    "action_by_username": action_by,
                    "task_ids": normalized_task_ids,
                },
                timeout=20,
            )
            return response.json()
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Timeout while syncing notification read status."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "message": f"API connection error: {exc}"}

    def clear_notifications(self, action_by, task_ids):
        try:
            normalized_task_ids = []
            for raw_task_id in task_ids or []:
                try:
                    task_id = int(raw_task_id)
                except (TypeError, ValueError):
                    continue
                if task_id > 0 and task_id not in normalized_task_ids:
                    normalized_task_ids.append(task_id)

            response = requests.post(
                f"{API_BASE_URL}/task-follows/notifications/clear",
                json={
                    "action_by_username": action_by,
                    "task_ids": normalized_task_ids,
                },
                timeout=20,
            )
            return response.json()
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Timeout while clearing notifications."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "message": f"API connection error: {exc}"}

    def get_tasks(self, action_by, show_all=False, include_done=False, search_text=""):
        try:
            response = requests.get(
                f"{API_BASE_URL}/task-follows",
                params={
                    "action_by": action_by,
                    "search": _normalize_text(search_text),
                    "show_all": bool(show_all),
                    "include_done": bool(include_done),
                    "viewer_timezone": self.viewer_timezone,
                },
                timeout=20,
            )
            payload = response.json()
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Timeout while loading follow tasks."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "message": f"API connection error: {exc}"}

        if not payload.get("success"):
            return payload

        return {
            "success": True,
            "data": [_normalize_task(item) for item in payload.get("data", [])],
            "search_scope": _normalize_text(payload.get("search_scope")) or "board",
            "board_filter_applied": bool(payload.get("board_filter_applied")),
            "show_all": bool(payload.get("show_all")),
            "include_done": bool(payload.get("include_done")),
        }

    def get_task_detail(self, task_id, action_by=""):
        try:
            response = requests.get(
                f"{API_BASE_URL}/task-follows/{task_id}",
                params={
                    "action_by": action_by,
                    "viewer_timezone": self.viewer_timezone,
                },
                timeout=20,
            )
            payload = response.json()
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Timeout while loading task detail."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "message": f"API connection error: {exc}"}

        if not payload.get("success"):
            return payload

        return {"success": True, "data": _normalize_task(payload.get("data"))}

    def get_handoff_options(self, action_by, task_date="", task_time="", task_period="", deadline_timezone=""):
        try:
            response = requests.get(
                f"{API_BASE_URL}/task-follows/handoff-options",
                params={
                    "action_by": action_by,
                    "task_date": str(task_date or "").strip(),
                    "task_time": str(task_time or "").strip(),
                    "task_period": str(task_period or "").strip(),
                    "deadline_timezone": _normalize_text(deadline_timezone),
                },
                timeout=20,
            )
            payload = response.json()
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Timeout while loading handoff options."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "message": f"API connection error: {exc}"}

        if not payload.get("success"):
            return payload

        return {
            "success": True,
            "current_display_name": _normalize_text(payload.get("current_display_name")),
            "data": [_normalize_handoff_option(item) for item in payload.get("data", [])],
        }

    def create_task(self, payload):
        try:
            request_payload = deepcopy(payload or {})
            request_payload["viewer_timezone"] = self.viewer_timezone
            response = requests.post(
                f"{API_BASE_URL}/task-follows",
                json=request_payload,
                timeout=25,
            )
            result = response.json()
            if result.get("success") and result.get("data") is not None:
                result["data"] = _normalize_task(result.get("data"))
            return result
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Timeout while creating task."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "message": f"API connection error: {exc}"}

    def update_task(self, task_id, payload):
        try:
            request_payload = deepcopy(payload or {})
            request_payload["viewer_timezone"] = self.viewer_timezone
            response = requests.put(
                f"{API_BASE_URL}/task-follows/{task_id}",
                json=request_payload,
                timeout=25,
            )
            result = response.json()
            if result.get("success") and result.get("data") is not None:
                result["data"] = _normalize_task(result.get("data"))
            return result
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Timeout while updating task."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "message": f"API connection error: {exc}"}

    def delete_task(self, task_id, action_by=""):
        try:
            response = requests.delete(
                f"{API_BASE_URL}/task-follows/{task_id}",
                params={"action_by": action_by},
                timeout=25,
            )
            return response.json()
        except requests.exceptions.Timeout:
            return {"success": False, "message": "Timeout while deleting task."}
        except requests.exceptions.RequestException as exc:
            return {"success": False, "message": f"API connection error: {exc}"}
