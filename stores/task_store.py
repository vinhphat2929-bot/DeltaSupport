import threading
import threading
import time
from copy import deepcopy
from datetime import datetime, timedelta

from services.task_service import TaskService
from stores.base_store import BaseStore


class TaskStore(BaseStore):
    def __init__(self, service=None, ttl_seconds=45):
        super().__init__(ttl_seconds=ttl_seconds)
        self.service = service or TaskService()
        self.handoff_options = [{"username": "", "display_name": "Tech Team", "type": "TEAM"}]
        self.current_display_name = ""
        self.search_scope = "board"
        self.show_all = False
        self.include_done = False
        self._view_cache = {}
        self._temp_id_seed = -1
        self._handoff_cache = {}
        self._handoff_loading_keys = set()
        self._last_handoff_key = None

    def _view_key(self, show_all=None, include_done=None):
        return (bool(self.show_all if show_all is None else show_all), bool(self.include_done if include_done is None else include_done))

    def _handoff_request_key(self, action_by, task_date="", task_time="", task_period=""):
        return (
            f"handoff:{str(action_by or '').strip().lower()}:"
            f"{str(task_date or '').strip()}:"
            f"{str(task_time or '').strip()}:"
            f"{str(task_period or '').strip().upper()}"
        )

    def _snapshot_state(self):
        return {
            "items_by_id": deepcopy(self.items_by_id),
            "ordered_ids": list(self.ordered_ids),
            "last_loaded_at": self.last_loaded_at,
            "is_loaded": self.is_loaded,
            "search_scope": self.search_scope,
        }

    def _apply_snapshot(self, snapshot):
        with self._lock:
            self.items_by_id = deepcopy(snapshot.get("items_by_id", {}))
            self.ordered_ids = list(snapshot.get("ordered_ids", []))
            self.last_loaded_at = snapshot.get("last_loaded_at")
            self.is_loaded = bool(snapshot.get("is_loaded"))
            self.search_scope = snapshot.get("search_scope", "board")
            self.is_loading = False

    def _save_active_snapshot(self):
        self._view_cache[self._view_key()] = self._snapshot_state()

    def _cache_valid_for(self, key):
        snapshot = self._view_cache.get(key)
        if not snapshot:
            return False
        loaded_at = snapshot.get("last_loaded_at")
        return bool(loaded_at and datetime.now() - loaded_at <= self.ttl)

    def set_view(self, show_all=False, include_done=False):
        key = self._view_key(show_all, include_done)
        self.show_all = bool(show_all)
        self.include_done = bool(include_done)
        snapshot = self._view_cache.get(key)
        if snapshot:
            self._apply_snapshot(snapshot)
            return True

        self.clear()
        return False

    def load(self, action_by, force=False, background_if_stale=True):
        key = self._view_key()
        snapshot = self._view_cache.get(key)
        if snapshot:
            self._apply_snapshot(snapshot)

        if not force and self._cache_valid_for(key):
            self.push_event(
                "tasks_loaded",
                items=self.get_all(),
                search_scope=self.search_scope,
                source="cache",
            )
            return

        if snapshot and background_if_stale and not force:
            self.push_event(
                "tasks_loaded",
                items=self.get_all(),
                search_scope=self.search_scope,
                source="cache-stale",
            )

        if self.is_loading:
            return

        with self._lock:
            self.is_loading = True
        self.push_event("tasks_loading", show_all=self.show_all, include_done=self.include_done)
        threading.Thread(target=self._load_worker, args=(action_by, key), daemon=True).start()

    def _load_worker(self, action_by, view_key):
        result = self.service.get_tasks(
            action_by=action_by,
            show_all=view_key[0],
            include_done=view_key[1],
        )
        if not result.get("success"):
            with self._lock:
                self.is_loading = False
            self.push_event("tasks_load_failed", message=result.get("message", "Unable to load tasks."))
            return

        items = result.get("data", [])
        with self._lock:
            self.items_by_id = {item["task_id"]: deepcopy(item) for item in items if item.get("task_id") is not None}
            self.ordered_ids = [item["task_id"] for item in items if item.get("task_id") is not None]
            self.search_scope = result.get("search_scope", "board")
            self.mark_loaded()
            self._save_active_snapshot()

        self.push_event(
            "tasks_loaded",
            items=self.get_all(),
            search_scope=self.search_scope,
            source="network",
        )

    def load_handoff_options(self, action_by, task_date="", task_time="", task_period=""):
        key = self._handoff_request_key(action_by, task_date, task_time, task_period)
        cached = self._handoff_cache.get(key)
        if cached:
            self.handoff_options = deepcopy(cached["options"])
            self.current_display_name = cached["current_display_name"]
            self._last_handoff_key = key
            self.push_event(
                "handoff_options_loaded",
                options=deepcopy(self.handoff_options),
                current_display_name=self.current_display_name,
                source="cache",
            )
            return

        if key == self._last_handoff_key or key in self._handoff_loading_keys:
            return

        self._handoff_loading_keys.add(key)
        threading.Thread(
            target=self._handoff_worker,
            args=(key, action_by, task_date, task_time, task_period),
            daemon=True,
        ).start()

    def _handoff_worker(self, key, action_by, task_date, task_time, task_period):
        try:
            result = self.service.get_handoff_options(
                action_by,
                task_date=task_date,
                task_time=task_time,
                task_period=task_period,
            )
            if not result.get("success"):
                self.push_event("handoff_options_failed", message=result.get("message", "Unable to load handoff options."))
                return

            self.handoff_options = result.get("data") or self.handoff_options
            self.current_display_name = result.get("current_display_name", "") or action_by
            self._handoff_cache[key] = {
                "loaded_at": time.monotonic(),
                "options": deepcopy(self.handoff_options),
                "current_display_name": self.current_display_name,
            }
            self._last_handoff_key = key
            self.push_event(
                "handoff_options_loaded",
                options=deepcopy(self.handoff_options),
                current_display_name=self.current_display_name,
                source="network",
            )
        finally:
            self._handoff_loading_keys.discard(key)

    def filter_local(self, query):
        keyword = str(query or "").strip().lower()
        items = self.get_all()
        if not keyword:
            return items

        filtered = []
        for item in items:
            haystack = " ".join(
                [
                    str(item.get("merchant_raw", "")),
                    str(item.get("merchant_name", "")),
                    str(item.get("phone", "")),
                    str(item.get("tracking_number", "")),
                    str(item.get("problem", "")),
                    str(item.get("handoff_to", "")),
                    str(item.get("status", "")),
                ]
            ).lower()
            if keyword in haystack:
                filtered.append(item)
        return filtered

    def ensure_detail(self, task_id, action_by=""):
        try:
            if int(task_id) < 0:
                item = self.get_by_id(task_id)
                if item:
                    self.push_event("task_detail_loaded", item=item)
                return
        except Exception:
            return

        item = self.get_by_id(task_id)
        if not item or item.get("history"):
            if item:
                self.push_event("task_detail_loaded", item=item)
            return

        threading.Thread(target=self._detail_worker, args=(task_id, action_by), daemon=True).start()

    def _detail_worker(self, task_id, action_by):
        result = self.service.get_task_detail(task_id, action_by=action_by)
        if not result.get("success"):
            self.push_event("task_detail_failed", task_id=task_id, message=result.get("message", "Unable to load task detail."))
            return

        item = result.get("data")
        self.upsert_one(item)
        self._save_active_snapshot()
        self.push_event("task_detail_loaded", item=self.get_by_id(task_id))

    def _task_matches_current_view(self, item):
        if not item:
            return False

        if not self.show_all:
            if item.get("status") == "DONE":
                return False
            return self._is_in_board_window(item.get("deadline_date"))

        if not self.include_done and item.get("status") == "DONE":
            return False

        return True

    def _is_in_board_window(self, deadline_date_text):
        text = str(deadline_date_text or "").strip()
        if not text:
            return False
        try:
            deadline = datetime.strptime(text, "%d-%m-%Y").date()
        except ValueError:
            return False
        today = datetime.now().date()
        return deadline < today or deadline <= today + timedelta(days=3)

    def _sort_current_ids(self):
        def sort_key(item_id):
            item = self.items_by_id.get(item_id, {})
            try:
                deadline_date = datetime.strptime(item.get("deadline_date") or "", "%d-%m-%Y")
            except ValueError:
                deadline_date = datetime.max

            try:
                deadline_time = datetime.strptime(item.get("deadline_time") or "", "%I:%M")
            except ValueError:
                deadline_time = datetime.max
            return (
                1 if item.get("deadline_date") in ("", None) else 0,
                deadline_date,
                1 if item.get("deadline_time") in ("", None) else 0,
                deadline_time,
                item.get("updated_at") or "",
                item_id,
            )

        self.ordered_ids.sort(key=sort_key)

    def _build_task_from_payload(self, payload, task_id, actor_display_name, existing=None):
        source = deepcopy(existing or {})
        source.update(
            {
                "task_id": task_id,
                "merchant_raw": payload.get("merchant_raw_text", source.get("merchant_raw", "")),
                "merchant_name": payload.get("merchant_raw_text", source.get("merchant_name", "")),
                "zip_code": source.get("zip_code", ""),
                "phone": payload.get("phone", source.get("phone", "")),
                "tracking_number": payload.get("tracking_number", source.get("tracking_number", "")),
                "problem": payload.get("problem_summary", source.get("problem", "")),
                "handoff_from_username": payload.get("action_by_username", source.get("handoff_from_username", "")),
                "handoff_from": actor_display_name or source.get("handoff_from", ""),
                "handoff_to_type": payload.get("handoff_to_type", source.get("handoff_to_type", "TEAM")),
                "handoff_to_username": payload.get("handoff_to_username", source.get("handoff_to_username", "")),
                "handoff_to_usernames": deepcopy(
                    payload.get("handoff_to_usernames", source.get("handoff_to_usernames", []))
                ),
                "handoff_to_display_names": deepcopy(
                    payload.get("handoff_to_display_names", source.get("handoff_to_display_names", []))
                ),
                "handoff_to": payload.get("handoff_to_display_name", source.get("handoff_to", "Tech Team")),
                "status": payload.get("status", source.get("status", "FOLLOW")),
                "deadline_date": payload.get("deadline_date", source.get("deadline_date", "")),
                "deadline_time": payload.get("deadline_time", source.get("deadline_time", "02:00")),
                "deadline_period": payload.get("deadline_period", source.get("deadline_period", "AM")),
                "note": payload.get("note", source.get("note", "")),
                "training_form": deepcopy(payload.get("training_form", source.get("training_form", []))),
                "training_started_at": payload.get("training_started_at", source.get("training_started_at", "")),
                "training_started_by_username": payload.get(
                    "training_started_by_username",
                    source.get("training_started_by_username", ""),
                ),
                "training_started_by_display_name": payload.get(
                    "training_started_by_display_name",
                    source.get("training_started_by_display_name", ""),
                ),
                "training_completed_tabs": deepcopy(payload.get("training_completed_tabs", source.get("training_completed_tabs", []))),
                "updated_at": datetime.now().strftime("%d-%m-%Y %I:%M %p"),
                "history": source.get("history", []),
                "is_optimistic": True,
                "is_saving": True,
                "error": "",
            }
        )
        if source["deadline_date"]:
            source["deadline"] = source["deadline_date"]
            if source["deadline_time"]:
                source["deadline"] = f"{source['deadline_date']} {source['deadline_time']} {source['deadline_period']}"
        else:
            source["deadline"] = ""
        return source

    def create_item(self, payload, actor_display_name, action_by):
        temp_id = self._temp_id_seed
        self._temp_id_seed -= 1
        optimistic_item = self._build_task_from_payload(payload, temp_id, actor_display_name)
        with self._lock:
            self.upsert_one(optimistic_item)
            self.ordered_ids = [temp_id] + [item_id for item_id in self.ordered_ids if item_id != temp_id]
            self.dirty_ids.add(temp_id)
            self._save_active_snapshot()
        self.push_event("task_upserted", item=self.get_by_id(temp_id), item_id=temp_id, optimistic=True)
        threading.Thread(
            target=self._create_worker,
            args=(temp_id, deepcopy(payload), actor_display_name, action_by),
            daemon=True,
        ).start()
        return temp_id

    def _create_worker(self, temp_id, payload, actor_display_name, action_by):
        result = self.service.create_task(payload)
        if not result.get("success"):
            failed_item = self.get_by_id(temp_id)
            self.remove(temp_id)
            self._save_active_snapshot()
            self.push_event("task_removed", item_id=temp_id, optimistic=False)
            self.push_event(
                "task_save_failed",
                action="create",
                item_id=temp_id,
                message=result.get("message", "Unable to create task."),
                rollback_item=failed_item,
            )
            return

        new_task_id = result.get("task_id")
        self.remove(temp_id)
        self.dirty_ids.discard(temp_id)
        self.push_event("task_removed", item_id=temp_id, optimistic=False)

        item = result.get("data")
        if not item:
            item = self._build_task_from_payload(payload, new_task_id, actor_display_name)
            item["is_optimistic"] = False
            item["is_saving"] = False

        if self._task_matches_current_view(item):
            with self._lock:
                self.upsert_one(item)
                self._sort_current_ids()
                self._save_active_snapshot()
            self.push_event("task_upserted", item=self.get_by_id(new_task_id), item_id=new_task_id, optimistic=False)
        else:
            self._save_active_snapshot()

        self.push_event(
            "task_save_succeeded",
            action="create",
            item_id=new_task_id,
            message=result.get("message", "Task created successfully."),
            visible_on_board=bool(result.get("visible_on_board")),
            notification_relevant=bool(result.get("notification_relevant")),
            recipient_changed=bool(result.get("recipient_changed")),
            status_changed=bool(result.get("status_changed")),
        )

    def update_item(self, task_id, payload, actor_display_name, action_by):
        original_item = self.get_by_id(task_id)
        if not original_item:
            self.push_event("task_save_failed", action="update", item_id=task_id, message="Task not found in cache.")
            return

        optimistic_item = self._build_task_from_payload(payload, task_id, actor_display_name, existing=original_item)
        with self._lock:
            if self._task_matches_current_view(optimistic_item):
                self.upsert_one(optimistic_item)
                self._sort_current_ids()
            else:
                self.remove(task_id)
            self.dirty_ids.add(task_id)
            self._save_active_snapshot()

        if self._task_matches_current_view(optimistic_item):
            self.push_event("task_upserted", item=self.get_by_id(task_id), item_id=task_id, optimistic=True)
        else:
            self.push_event("task_removed", item_id=task_id, optimistic=True)

        threading.Thread(
            target=self._update_worker,
            args=(task_id, deepcopy(original_item), deepcopy(payload), actor_display_name, action_by),
            daemon=True,
        ).start()

    def _update_worker(self, task_id, original_item, payload, actor_display_name, action_by):
        result = self.service.update_task(task_id, payload)
        if not result.get("success"):
            with self._lock:
                self.upsert_one(original_item)
                self._sort_current_ids()
                self.dirty_ids.discard(task_id)
                self._save_active_snapshot()
            self.push_event(
                "task_save_failed",
                action="update",
                item_id=task_id,
                message=result.get("message", "Unable to update task."),
                rollback_item=self.get_by_id(task_id),
            )
            return

        item = result.get("data")
        if not item:
            item = self._build_task_from_payload(payload, task_id, actor_display_name, existing=original_item)
            item["is_optimistic"] = False
            item["is_saving"] = False

        with self._lock:
            self.dirty_ids.discard(task_id)
            if self._task_matches_current_view(item):
                item["is_optimistic"] = False
                item["is_saving"] = False
                self.upsert_one(item)
                self._sort_current_ids()
            else:
                self.remove(task_id)
            self._save_active_snapshot()

        if self._task_matches_current_view(item):
            self.push_event("task_upserted", item=self.get_by_id(task_id), item_id=task_id, optimistic=False)
        else:
            self.push_event("task_removed", item_id=task_id, optimistic=False)

        self.push_event(
            "task_save_succeeded",
            action="update",
            item_id=task_id,
            message=result.get("message", "Task updated successfully."),
            visible_on_board=bool(result.get("visible_on_board")),
            notification_relevant=bool(result.get("notification_relevant")),
            recipient_changed=bool(result.get("recipient_changed")),
            status_changed=bool(result.get("status_changed")),
        )

    def delete_item(self, task_id, action_by):
        original_item = self.get_by_id(task_id)
        if not original_item:
            self.push_event("task_delete_failed", item_id=task_id, message="Task not found in cache.")
            return

        with self._lock:
            self.remove(task_id)
            self.dirty_ids.add(task_id)
            self._save_active_snapshot()
        self.push_event("task_removed", item_id=task_id, optimistic=True)

        threading.Thread(
            target=self._delete_worker,
            args=(task_id, deepcopy(original_item), action_by),
            daemon=True,
        ).start()

    def _delete_worker(self, task_id, original_item, action_by):
        result = self.service.delete_task(task_id, action_by=action_by)
        if not result.get("success"):
            with self._lock:
                self.upsert_one(original_item)
                self._sort_current_ids()
                self.dirty_ids.discard(task_id)
                self._save_active_snapshot()
            self.push_event(
                "task_delete_failed",
                item_id=task_id,
                message=result.get("message", "Unable to delete task."),
            )
            self.push_event("task_upserted", item=self.get_by_id(task_id), item_id=task_id, optimistic=False)
            return

        with self._lock:
            self.dirty_ids.discard(task_id)
            self.remove(task_id)
            self._save_active_snapshot()

        self.push_event(
            "task_delete_succeeded",
            item_id=task_id,
            message=result.get("message", "Task deleted successfully."),
            notification_relevant=bool(result.get("notification_relevant")),
        )
