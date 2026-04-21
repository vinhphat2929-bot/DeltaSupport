from copy import deepcopy
import threading
import time
from datetime import datetime

from services.task_service import TaskService
from stores.base_store import BaseStore


class NotificationStore(BaseStore):
    def __init__(self, service=None, ttl_seconds=30):
        super().__init__(ttl_seconds=ttl_seconds)
        self.service = service or TaskService()
        self.unread_count = 0
        self.last_action_by = ""
        self.pending_read_task_ids = set()
        self.read_sync_delay_seconds = 1.2
        self._read_sync_lock = threading.Lock()
        self._read_sync_thread = None
        self.is_count_loading = False
        self.count_last_loaded_at = None
        self.latest_updated_at = ""
        self._pending_count_request_keys = set()
        self._pending_list_request_keys = set()

    def _build_request_key(self, request_type, action_by):
        return f"notifications:{request_type}:{str(action_by or '').strip().lower()}"

    def _mark_count_loaded(self, loaded_at=None):
        with self._lock:
            self.is_count_loading = False
            self.count_last_loaded_at = loaded_at or datetime.now()

    def _is_count_cache_valid(self):
        with self._lock:
            if self.count_last_loaded_at is None:
                return False
            return datetime.now() - self.count_last_loaded_at <= self.ttl

    def _recount_unread(self):
        self.unread_count = len(
            [
                item_id
                for item_id in self.ordered_ids
                if not bool((self.items_by_id.get(item_id) or {}).get("is_read"))
            ]
        )

    def _get_all_task_ids(self):
        task_ids = []
        with self._lock:
            for item_id in self.ordered_ids:
                item = self.items_by_id.get(item_id) or {}
                try:
                    task_id = int(item.get("task_id"))
                except (TypeError, ValueError):
                    continue
                if task_id > 0 and task_id not in task_ids:
                    task_ids.append(task_id)
        return task_ids

    def _is_task_pending_read(self, task_id):
        try:
            normalized_task_id = int(task_id)
        except (TypeError, ValueError):
            return False

        if normalized_task_id <= 0:
            return False

        with self._read_sync_lock:
            return normalized_task_id in self.pending_read_task_ids

    def _normalize_items(self, items):
        normalized_items = []
        for index, item in enumerate(items or []):
            payload = deepcopy(item or {})
            payload["task_id"] = payload.get("task_id", -(index + 1))
            payload["id"] = str(payload.get("id", f"notif-{index}")).strip() or f"notif-{index}"
            payload["title"] = str(payload.get("title", "")).strip() or "New task assigned"
            payload["meta"] = str(payload.get("meta", "")).strip() or "Tap to open Task Follow"
            payload["task_section"] = str(payload.get("task_section", "follow")).strip() or "follow"
            backend_is_read = bool(payload.get("is_read"))
            payload["is_read"] = backend_is_read or self._is_task_pending_read(payload.get("task_id"))
            normalized_items.append(payload)
        return normalized_items

    def seed(self, items=None, unread_count=0):
        normalized_items = self._normalize_items(items)
        self.upsert_many(normalized_items)
        self.unread_count = max(
            len([item for item in normalized_items if not item.get("is_read")]),
            max(0, int(unread_count or 0)),
        )
        self.latest_updated_at = ""
        if normalized_items:
            self.mark_loaded()

    def load_unread_count(self, action_by, force=False):
        self.last_action_by = str(action_by or "").strip()
        if not force and self._is_count_cache_valid():
            self.push_event(
                "notifications_count_loaded",
                unread_count=self.unread_count,
                latest_updated_at=self.latest_updated_at,
                source="cache",
            )
            return

        request_key = self._build_request_key("count", action_by)
        with self._lock:
            if request_key in self._pending_count_request_keys:
                return
            self._pending_count_request_keys.add(request_key)
            self.is_count_loading = True
        threading.Thread(target=self._load_unread_count_worker, args=(action_by, request_key), daemon=True).start()

    def _load_unread_count_worker(self, action_by, request_key):
        try:
            result = self.service.get_notification_unread_count(action_by)
            if not result.get("success"):
                self.push_event(
                    "notifications_count_load_failed",
                    message=result.get("message", "Unable to load notification count."),
                )
                return

            unread_count = max(0, int(result.get("unread_count", 0) or 0))
            latest_updated_at = str(result.get("latest_updated_at", "") or "").strip()
            with self._lock:
                self.unread_count = unread_count
                self.latest_updated_at = latest_updated_at
                self._mark_count_loaded()

            self.push_event(
                "notifications_count_loaded",
                unread_count=self.unread_count,
                latest_updated_at=self.latest_updated_at,
                source="network",
            )
        finally:
            with self._lock:
                self._pending_count_request_keys.discard(request_key)
                self.is_count_loading = bool(self._pending_count_request_keys)

    def load_full_list(self, action_by, force=False, background_if_stale=True):
        self.last_action_by = str(action_by or "").strip()
        if not force and self.is_cache_valid():
            self.push_event(
                "notifications_loaded",
                items=self.get_all(),
                unread_count=self.unread_count,
                source="cache",
            )
            return

        if self.is_loaded and background_if_stale and not force:
            self.push_event(
                "notifications_loaded",
                items=self.get_all(),
                unread_count=self.unread_count,
                source="cache-stale",
            )

        request_key = self._build_request_key("list", action_by)
        with self._lock:
            if request_key in self._pending_list_request_keys:
                return
            self._pending_list_request_keys.add(request_key)
            self.is_loading = True
        self.push_event("notifications_loading")
        threading.Thread(target=self._load_worker, args=(action_by, request_key), daemon=True).start()

    def load(self, action_by, force=False, background_if_stale=True):
        self.load_full_list(
            action_by,
            force=force,
            background_if_stale=background_if_stale,
        )

    def _load_worker(self, action_by, request_key):
        try:
            result = self.service.get_notification_items(action_by)
            if not result.get("success"):
                self.push_event(
                    "notifications_load_failed",
                    message=result.get("message", "Unable to load notifications."),
                )
                return

            items = self._normalize_items(result.get("data", []) or [])
            unread_count = len([item for item in items if not item.get("is_read")])
            with self._lock:
                self.upsert_many(items)
                self.unread_count = unread_count
                self.latest_updated_at = ""
                self.mark_loaded()
                self._mark_count_loaded(self.last_loaded_at)

            self.push_event(
                "notifications_loaded",
                items=self.get_all(),
                unread_count=self.unread_count,
                source="network",
            )
            self._schedule_read_sync(action_by, delay_seconds=0.2)
        finally:
            with self._lock:
                self._pending_list_request_keys.discard(request_key)
                self.is_loading = bool(self._pending_list_request_keys)

    def _extract_task_ids_for_notice(self, notice_id):
        task_ids = set()
        with self._lock:
            for item in list(self.items_by_id.values()):
                current_id = str((item or {}).get("id", "")).strip()
                if current_id != notice_id:
                    continue
                try:
                    task_id = int((item or {}).get("task_id"))
                except (TypeError, ValueError):
                    continue
                if task_id > 0:
                    task_ids.add(task_id)
        return task_ids

    def mark_as_read(self, notification_id, action_by=""):
        notice_id = str(notification_id or "").strip()
        if not notice_id:
            return

        action_by = str(action_by or "").strip() or self.last_action_by
        task_ids = self._extract_task_ids_for_notice(notice_id)
        if task_ids:
            with self._read_sync_lock:
                self.pending_read_task_ids.update(task_ids)
                if action_by:
                    self.last_action_by = action_by
        with self._lock:
            for item_id, item in list(self.items_by_id.items()):
                current_id = str((item or {}).get("id", "")).strip()
                if current_id == notice_id:
                    updated_item = deepcopy(item)
                    updated_item["is_read"] = True
                    self.items_by_id[item_id] = updated_item
            self._recount_unread()
        self.push_event(
            "notifications_loaded",
            items=self.get_all(),
            unread_count=self.unread_count,
            source="local-read",
        )
        self._schedule_read_sync(action_by)

    def mark_all_as_read(self, action_by=""):
        action_by = str(action_by or "").strip() or self.last_action_by
        task_ids = self._get_all_task_ids()
        if not task_ids:
            return

        with self._lock:
            for item_id, item in list(self.items_by_id.items()):
                updated_item = deepcopy(item)
                updated_item["is_read"] = True
                self.items_by_id[item_id] = updated_item
            self._recount_unread()

        with self._read_sync_lock:
            self.pending_read_task_ids.update(task_ids)
            if action_by:
                self.last_action_by = action_by

        self.push_event(
            "notifications_loaded",
            items=self.get_all(),
            unread_count=self.unread_count,
            source="local-read-all",
        )
        self._schedule_read_sync(action_by, delay_seconds=0.1)

    def clear_all(self, action_by=""):
        action_by = str(action_by or "").strip() or self.last_action_by
        task_ids = self._get_all_task_ids()
        if not task_ids:
            self.push_event(
                "notifications_cleared",
                items=[],
                unread_count=0,
                cleared_count=0,
            )
            return

        result = self.service.clear_notifications(action_by, task_ids)
        if not result.get("success"):
            self.push_event(
                "notifications_clear_failed",
                message=result.get("message", "Unable to clear notifications."),
            )
            return

        cleared_task_ids = {
            int(task_id)
            for task_id in (result.get("task_ids") or [])
            if str(task_id).strip().isdigit() and int(task_id) > 0
        }
        with self._lock:
            if cleared_task_ids:
                keep_ids = []
                new_items = {}
                for item_id in self.ordered_ids:
                    item = self.items_by_id.get(item_id) or {}
                    try:
                        task_id = int(item.get("task_id"))
                    except (TypeError, ValueError):
                        task_id = None
                    if task_id in cleared_task_ids:
                        continue
                    keep_ids.append(item_id)
                    new_items[item_id] = deepcopy(item)
                self.items_by_id = new_items
                self.ordered_ids = keep_ids
            self._recount_unread()

        self.push_event(
            "notifications_cleared",
            items=self.get_all(),
            unread_count=self.unread_count,
            cleared_count=int(result.get("cleared_count", 0) or 0),
        )

    def _schedule_read_sync(self, action_by="", delay_seconds=None):
        action_by = str(action_by or "").strip() or self.last_action_by
        if not action_by:
            return

        with self._read_sync_lock:
            if not self.pending_read_task_ids:
                return
            self.last_action_by = action_by
            thread = self._read_sync_thread
            if thread is not None and thread.is_alive():
                return

            wait_seconds = self.read_sync_delay_seconds if delay_seconds is None else max(0.0, float(delay_seconds))
            self._read_sync_thread = threading.Thread(
                target=self._read_sync_worker,
                args=(wait_seconds,),
                daemon=True,
            )
            self._read_sync_thread.start()

    def _read_sync_worker(self, delay_seconds):
        if delay_seconds > 0:
            time.sleep(delay_seconds)

        while True:
            with self._read_sync_lock:
                action_by = self.last_action_by
                task_ids = sorted(self.pending_read_task_ids)
                self.pending_read_task_ids.clear()

            if not action_by or not task_ids:
                break

            result = self.service.mark_notifications_as_read(action_by, task_ids)
            if not result.get("success"):
                with self._read_sync_lock:
                    self.pending_read_task_ids.update(task_ids)
                self.push_event(
                    "notifications_read_sync_failed",
                    message=result.get("message", "Unable to sync notice read status."),
                )
                break

            self.push_event(
                "notifications_read_synced",
                task_ids=task_ids,
            )
            time.sleep(0.05)

        with self._read_sync_lock:
            self._read_sync_thread = None
            has_more_pending = bool(self.pending_read_task_ids) and bool(self.last_action_by)

        if has_more_pending:
            self._schedule_read_sync(self.last_action_by, delay_seconds=0.2)

    def flush_pending_reads(self):
        with self._read_sync_lock:
            action_by = self.last_action_by
            task_ids = sorted(self.pending_read_task_ids)
            self.pending_read_task_ids.clear()

        if not action_by or not task_ids:
            return True

        result = self.service.mark_notifications_as_read(action_by, task_ids)
        if result.get("success"):
            self.push_event(
                "notifications_read_synced",
                task_ids=task_ids,
            )
            return True

        with self._read_sync_lock:
            self.pending_read_task_ids.update(task_ids)
        self.push_event(
            "notifications_read_sync_failed",
            message=result.get("message", "Unable to sync notice read status."),
        )
        return False
