import threading


class WSClient:
    """
    Skeleton WebSocket client for future realtime sync.

    Intended flow later:
    - network thread receives websocket messages
    - callback pushes normalized events into a store queue
    - Tkinter UI polls store queue via after(...)
    """

    def __init__(self):
        self._callback = None
        self._channels = set()
        self._is_connected = False
        self._lock = threading.RLock()

    def connect(self):
        with self._lock:
            self._is_connected = True

    def disconnect(self):
        with self._lock:
            self._is_connected = False

    def subscribe(self, channel):
        with self._lock:
            self._channels.add(str(channel or "").strip())

    def on_message(self, callback):
        self._callback = callback

    def emit_local_event(self, event):
        if callable(self._callback):
            self._callback(event)
