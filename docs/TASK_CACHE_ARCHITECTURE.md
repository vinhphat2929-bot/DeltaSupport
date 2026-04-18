Task Follow migration notes

- `pages/task_page.py` is the first full example of the new pattern:
  - page = render + collect user input
  - store = cache + optimistic update/create + queue events
  - service = API calls + response normalization
- Search is now local-first with a 400ms debounce. It no longer calls the API on every keypress.
- Cache TTL lives in `stores/task_store.py` and is currently 45 seconds for the task board.
- Background work never touches Tkinter directly. Worker threads only mutate store state and push events into `queue.Queue`; `TaskPage.after(...)` polls and applies UI changes on the main thread.
- `realtime/ws_client.py` is intentionally a skeleton. Later websocket events such as `task_updated` or `task_created` can be normalized into the same store event queue used today by background API workers.
