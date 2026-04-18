import queue
import threading
from copy import deepcopy
from datetime import datetime, timedelta


class BaseStore:
    def __init__(self, ttl_seconds=60):
        self.ttl = timedelta(seconds=max(1, int(ttl_seconds)))
        self.items_by_id = {}
        self.ordered_ids = []
        self.last_loaded_at = None
        self.is_loaded = False
        self.is_loading = False
        self.dirty_ids = set()
        self.event_queue = queue.Queue()
        self._lock = threading.RLock()

    def get_all(self):
        with self._lock:
            return [deepcopy(self.items_by_id[item_id]) for item_id in self.ordered_ids if item_id in self.items_by_id]

    def get_by_id(self, item_id):
        with self._lock:
            item = self.items_by_id.get(item_id)
            return deepcopy(item) if item is not None else None

    def upsert_one(self, item):
        if item is None:
            return None

        item_id = item.get("task_id") if isinstance(item, dict) else None
        if item_id is None:
            return None

        with self._lock:
            self.items_by_id[item_id] = deepcopy(item)
            if item_id not in self.ordered_ids:
                self.ordered_ids.append(item_id)
        return item_id

    def upsert_many(self, items):
        new_ids = []
        with self._lock:
            for item in items or []:
                item_id = item.get("task_id") if isinstance(item, dict) else None
                if item_id is None:
                    continue
                self.items_by_id[item_id] = deepcopy(item)
                new_ids.append(item_id)
            self.ordered_ids = list(new_ids)
        return list(new_ids)

    def remove(self, item_id):
        with self._lock:
            self.items_by_id.pop(item_id, None)
            self.ordered_ids = [current_id for current_id in self.ordered_ids if current_id != item_id]
            self.dirty_ids.discard(item_id)

    def mark_loaded(self, loaded_at=None):
        with self._lock:
            self.is_loaded = True
            self.is_loading = False
            self.last_loaded_at = loaded_at or datetime.now()

    def clear(self):
        with self._lock:
            self.items_by_id = {}
            self.ordered_ids = []
            self.last_loaded_at = None
            self.is_loaded = False
            self.is_loading = False
            self.dirty_ids = set()

    def is_cache_valid(self):
        with self._lock:
            if not self.is_loaded or self.last_loaded_at is None:
                return False
            return datetime.now() - self.last_loaded_at <= self.ttl

    def push_event(self, event_type, **payload):
        event = {"type": event_type, **payload}
        self.event_queue.put(event)
        return event

    def drain_events(self):
        events = []
        while True:
            try:
                events.append(self.event_queue.get_nowait())
            except queue.Empty:
                break
        return events
