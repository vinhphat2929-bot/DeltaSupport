from stores.base_store import BaseStore


class PosStore(BaseStore):
    """Placeholder cache container for the next migration step."""

    def __init__(self):
        super().__init__(ttl_seconds=60)
