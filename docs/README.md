# Delta One Project Handbook

This is the single source of truth for the Delta One project docs. Older docs were merged here to avoid duplicate or outdated instructions.

## 1. Project Summary

Delta One is an internal Windows desktop app for the Delta One tech support workflow.

Core architecture:

```text
Desktop app -> FastAPI backend -> SQL Server
```

Important rule: desktop clients must call the API. Do not make client machines write directly to SQL Server.

Main user-facing areas:
- `Task`
  - `Report`: Daily Case Note, Date Filter, Saved Reports.
  - `Follow`: task follow board, handoff, deadline, notice, history.
  - `Setup / Training`: hardware setup, POS setup, training checklist flow.
- `Work Schedule`: weekly schedule, leave request, monthly leave summary, schedule setup.
- `Link / Data`: internal links/data.
- `POS` and `SQL`: code still exists, but the demo nav currently hides both items.

## 2. How To Work With The User

The user wants small, exact changes. If the user says a section is "ok", "on", "dung y", or similar, treat that part as locked.

Working style:
- Explain slowly, clearly, and step by step.
- The user does not know how to code. Always say exactly which file to open, what to find, what to replace, and what command to run.
- Do not assume the user knows Git, deploy, API, backend restart, DB schema, build details, or how auto-update works.
- Prefer the easiest safe path first when there are choices.
- Avoid broad refactors unless the user explicitly asks.
- Keep changes tightly scoped to the requested area.
- If something cannot be done, say plainly what is blocked.

Window branding rule:
- Every new app window, popup, dialog, or `CTkToplevel` opened from Delta One must show the Delta One logo in two places: inside the window UI near the top-left header area, and in the native Windows title bar icon at the top-left corner.
- For the native Windows title bar icon, call `apply_app_window_icon(window, owner)` from [utils/window_icon_utils.py](../utils/window_icon_utils.py) immediately after creating/configuring the window.
- Do not ship any new window that falls back to the default blue Tkinter window icon.

Simple pattern for any new window:

```python
from utils.window_icon_utils import apply_app_window_icon

popup = ctk.CTkToplevel(self)
popup.title("Window Title")
popup.geometry("500x400")
popup.configure(fg_color=BG_MAIN)
apply_app_window_icon(popup, self)
```

The same window must also place the Delta One logo inside the UI near the top-left header area. Reuse the local page's existing logo helper when available, such as `get_content_icon_image(...)`, `safe_load_icon(...)`, or `safe_load_image_fit(...)`. If no helper exists yet, load from `data/icon.png` or `data/logo-goc.png` with Pillow/`CTkImage`.

Machine context:
- DEV machine: used for editing frontend/app code, local testing, and building `DELTA_ONE.exe`.
- SERVER machine: runs the real FastAPI backend, SQL Server, and production data.
- Every instruction must clearly say whether the step is done on the DEV machine or the SERVER machine.
- Do not say only "copy to server". Say exactly which file or folder to copy, and where it goes on the SERVER machine.

When backend files are changed, the final answer must include:
- which local backend files changed
- which files must be copied from the DEV machine to the SERVER machine
- the destination path on the SERVER machine, when known
- whether the SERVER backend must be restarted
- the exact restart command or service action, when known

If the change is frontend-only:
- say that no backend code copy is needed
- say whether a new exe must be built and published
- if existing users need the change through auto-update, explain that the update manifest config still has to be copied to the SERVER machine and the SERVER backend restarted

## 3. Current Stack

Frontend desktop:
- Python
- CustomTkinter
- requests
- Pillow
- PyInstaller one-file Windows exe

Backend:
- FastAPI
- Uvicorn
- pyodbc
- SQL Server
- Pydantic

Timezone/update support:
- `tzdata`
- `zip2tz`
- custom update service/dialog

Tests:
- Python `unittest`

## 4. Runtime Flow

Normal app flow:

```text
main.py
  -> SplashScreen
  -> LoginPage
  -> API /login
  -> MainAppPage
  -> pages call backend APIs as needed
```

Main entry files:
- [main.py](../main.py): app entry, root window, update check, login/main routing.
- [main_app.py](../main_app.py): app shell, topbar, navigation, settings, notices, lock/logout.
- [splash_screen.py](../splash_screen.py): startup splash screen.
- [app_version.py](../app_version.py): app name/version constant used by the client.
- [main.spec](../main.spec): PyInstaller one-file build config.

Current version note on 2026-04-26:
- `app_version.py` currently has `APP_VERSION = "2026.4.26.10"`.
- `backend_server/app_update_config.json` currently advertises update `2026.4.26.10`.
- Do not assume these two files always match. Verify both before publishing an update.

Current version note on 2026-04-27:
- `app_version.py` currently has `APP_VERSION = "2026.4.27.1"`.
- `backend_server/app_update_config.json` currently advertises update `2026.4.27.1`.
- This build includes the Task Follow speed/update work, Task Report FOLLOW popup flow, DELTA ONE branding fixes, app update hardening, and local dev startup helpers.

## 5. Recent Change History

Recent changes in the current workspace:
- Task Follow update speed:
  - Task Follow updates now use `PATCH /task-follows/{task_id}` with field-level payloads instead of always sending a full update.
  - The frontend merges lightweight `updated_fields` from the backend into the local Task cache.
  - The follow action cooldown is shorter for `save`, `update`, and `delete`; `refresh` keeps a longer cooldown to avoid repeated board reloads.
- Task Follow backend:
  - Added partial update handling in [backend_server/routers/task_follow.py](../backend_server/routers/task_follow.py).
  - Added support for tracking number, deadline UTC/timezone fields, training form metadata, recipient storage, notification read/dismiss storage, and recipient-aware notification checks.
  - Handoff supports Team, one user, and multiple users.
- Task Report:
  - `PROCESSING` now uses `DONE`, `FOLLOW`, and `SYNC`.
  - Saving a Task Report with `FOLLOW` opens a `Task Details` popup that creates a Task Follow item through the existing Task Follow API.
  - The popup includes merchant, phone, problem, deadline picker, assignee, status, and note.
  - The Task Report layout was changed to the current two-column Task-style layout with left-side Daily Case Note and right-side Date Filter/Saved Reports.
- DELTA ONE branding and window icon:
  - The main app uses DELTA ONE branding from the existing `data` assets.
  - Task Report follow popup title/icon handling was aligned so the titlebar uses the app-style icon/title instead of a squeezed horizontal logo.
  - The popup body uses the app logo asset in a compact brand area.
- Auto update:
  - Update download/replace/relaunch behavior was hardened.
  - Update tests were expanded.
  - `backend_server/app_update_config.json` must match the packaged `APP_VERSION` and exe file size before publishing.
- Local development:
  - Added `START_DEV_API.cmd` and `START_DEV_APP.cmd`.
  - Added PowerShell helpers under `scripts/` for starting the local API/app against `127.0.0.1:8000`.

## 6. Repository Map

Root:
- `main.py`: desktop app entry point.
- `main_app.py`: main shell after login.
- `app_version.py`: app name/version.
- `main.spec`: PyInstaller build recipe.
- `START_DEV_API.cmd`: starts local dev API on `127.0.0.1:8000`.
- `START_DEV_APP.cmd`: starts app against local dev API.
- `requirements.txt`: Python dependencies.

Frontend:
- `pages/`: desktop screens.
- `pages/process_page.py`: Task shell and shared Task lifecycle.
- `pages/process/follow_controller.py`: Task Follow flow.
- `pages/process/setup_training_controller.py`: Setup / Training flow.
- `pages/task_report_page.py`: Task Report UI and local report interactions.
- `services/`: client HTTP/API services and app config/update helpers.
- `stores/`: local cache/state stores.
- `widgets/`: reusable UI widgets/dialogs.
- `data/`: icons, images, local config/data files included in builds.

Backend:
- `backend_server/api_server.py`: FastAPI app and router registration.
- `backend_server/database.py`: SQL Server connection config.
- `backend_server/models.py`: request/response models.
- `backend_server/routers/`: API routes.
- `backend_server/services/`: backend business helpers.
- `backend_server/sql/`: SQL helper scripts.
- `backend_server/app_update_config.json`: update manifest config.

Tests:
- `tests/test_update_service.py`
- `tests/test_app_update_router.py`
- `tests/test_task_report_router.py`
- `tests/test_schedule_match_service.py`
- `tests/test_timezone_service.py`
- `tests/test_timezone_utils.py`
- `tests/test_process_logic.py`
- `tests/test_send_otp.py`

## 7. Frontend Notes

API base URL is resolved in [services/app_config.py](../services/app_config.py).

Priority order:
1. Environment variable `DELTA_API_BASE_URL`.
2. `api_base_url` in [data/app_config.json](../data/app_config.json).
3. Auto candidate probing if config is set to `auto`.

Current `data/app_config.json`:

```json
{
  "api_base_url": "auto",
  "api_base_url_candidates": [
    "http://192.168.80.110:8000",
    "http://100.111.27.65:8000",
    "http://127.0.0.1:8000"
  ]
}
```

For dev/testing, use `START_DEV_APP.cmd` or `scripts/start_dev_app.ps1` so the app is forced to `http://127.0.0.1:8000`.

Important frontend modules:
- `services/auth_service.py`: login/PIN/auth calls.
- `services/task_service.py`: Task Follow API layer.
- `services/task_follow_api_service.py`: helper API layer for Task Follow flows.
- `services/task_report_service.py`: Task Report API layer.
- `services/update_service.py`: app update checking, download, replace, relaunch.
- `stores/base_store.py`: shared cache/load/event pattern.
- `stores/task_store.py`: Task Follow state/cache/optimistic updates.
- `stores/notification_store.py`: notice state and polling.

## 8. Backend Notes

The local backend in this workspace is only a local copy. The real backend runs on the server.

Registered routers in [backend_server/api_server.py](../backend_server/api_server.py):
- `auth`
- `admin`
- `pin`
- `work_schedule`
- `tool_logs`
- `task_follow`
- `task_report`
- `app_update`

Backend root endpoint:

```text
GET / -> {"status": "API OK"}
```

Startup bootstraps schemas for:
- Task Follow
- Task Report
- PIN

Backend services include:
- `audit_service.py`
- `email_service.py`
- `schedule_match_service.py`
- `timezone_service.py`

## 9. Database Notes

SQL Server config lives in [backend_server/database.py](../backend_server/database.py).

Defaults:
- driver: `ODBC Driver 17 for SQL Server`
- server: `localhost`
- database: `DeltaSupport`
- username: `delta_user`
- password: `Delta@123456`

Environment overrides:
- `DELTA_DB_DRIVER`
- `DELTA_DB_SERVER`
- `DELTA_DB_NAME`
- `DELTA_DB_USER`
- `DELTA_DB_PASSWORD`
- `DELTA_DB_TRUSTED_CONNECTION`

Important dev rule:
- `START_DEV_API.cmd` sets DB to `DeltaSupport_DEV` and uses trusted Windows connection.
- Running backend directly without `DELTA_DB_NAME` uses default `DeltaSupport`.

## 10. Dev Run Commands

Recommended Windows CMD flow:

```bat
START_DEV_API.cmd
START_DEV_APP.cmd
```

Recommended PowerShell flow:

```powershell
.\scripts\start_dev_api.ps1
.\scripts\start_dev_app.ps1
```

What these do:
- API runs at `http://127.0.0.1:8000`.
- Dev API uses `DeltaSupport_DEV`.
- Dev app uses `DELTA_API_BASE_URL=http://127.0.0.1:8000`.

Manual backend run:

```powershell
cd backend_server
python -m uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload
```

Manual frontend run:

```powershell
python main.py
```

Be careful: manual `python main.py` can auto-probe and select the production API depending on `data/app_config.json`.

## 11. Build Exe

Build is done on the DEV machine.

Before building:
1. Open [app_version.py](../app_version.py) on the DEV machine.
2. Find the line:

```python
APP_VERSION = "..."
```

3. Replace it with the next version number. Example:

```python
APP_VERSION = "2026.4.26.10"
```

4. Save the file.

Build command on the DEV machine, from the project root:

```powershell
python -m PyInstaller --noconfirm --clean main.spec
```

Output on the DEV machine:

```text
dist/DELTA_ONE.exe
```

`main.spec` currently:
- builds one-file `DELTA_ONE.exe`
- includes the `data` folder
- collects `tzdata`
- collects `zip2tz`
- uses `data/app_v3.ico` or `data/app.ico` if present
- falls back to generating an icon from `data/icon.png`

After a build, test at least:
- app opens
- login works against intended API
- logo/window icon appears
- update check does not break startup
- the feature changed by the build still works in packaged exe

After building, get the exe file size on the DEV machine:

```powershell
Get-Item dist\DELTA_ONE.exe | Select-Object FullName,Length,LastWriteTime
```

Use the `Length` value as `file_size` in `backend_server/app_update_config.json`.

## 12. Auto Update

Client update flow:
- App checks `GET /app-update`.
- If the backend advertises a newer version, the app shows update UI.
- User starts update from the update dialog.
- Packaged exe downloads the new exe, closes, replaces itself, then relaunches.

Backend config:
- [backend_server/app_update_config.json](../backend_server/app_update_config.json)

Current config style:
- Uses Google Drive `download_url`.
- `windows_exe_path` is empty.
- This means the download URL is external, not served from a local backend release path.

Publishing an update with Google Drive:
1. On the DEV machine, open [app_version.py](../app_version.py).
2. Find `APP_VERSION = "..."`.
3. Replace it with the new version.
4. On the DEV machine, build the exe:

```powershell
python -m PyInstaller --noconfirm --clean main.spec
```

5. On the DEV machine, confirm the new exe exists:

```powershell
Get-Item dist\DELTA_ONE.exe
```

6. Upload or replace this exact file on Google Drive:

```text
dist/DELTA_ONE.exe
```

7. On the DEV machine, get the new file size:

```powershell
Get-Item dist\DELTA_ONE.exe | Select-Object Length
```

8. On the DEV machine, open [backend_server/app_update_config.json](../backend_server/app_update_config.json).
9. Replace these fields:
   - `version`: must match `APP_VERSION`
   - `release_notes`: short English description
   - `published_at`: current Vietnam time
   - `file_size`: exact `Length` of `dist\DELTA_ONE.exe`
   - `download_url`: keep the same if the Google Drive file ID did not change
   - `windows_exe_path`: keep empty when using Google Drive

Example:

```json
{
  "version": "2026.4.26.10",
  "release_notes": "Task Report window scroll and save redraw fix.",
  "minimum_supported_version": "",
  "published_at": "2026-04-26 06:47:21 +07:00",
  "mandatory": false,
  "file_name": "DELTA_ONE.exe",
  "file_size": 23960236,
  "download_url": "https://drive.google.com/uc?export=download&id=...",
  "windows_exe_path": ""
}
```

10. Copy this file from the DEV machine:

```text
backend_server/app_update_config.json
```

to this destination on the SERVER machine:

```text
<SERVER_BACKEND_FOLDER>/app_update_config.json
```

`<SERVER_BACKEND_FOLDER>` means the backend folder on the SERVER machine that contains `api_server.py`. In this repo, that folder is named `backend_server`.

11. On the SERVER machine, restart the FastAPI backend so `/app-update` returns the new manifest.

If the SERVER backend is started by a terminal window, close that backend process and start it again from the backend folder:

```powershell
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000
```

If the SERVER backend is managed by a Windows service or scheduled task, restart that service/task instead.

Important:
- Auto-update only works from the packaged `.exe`, not from `python main.py`.
- Source-only frontend changes do not reach users until a new exe is built and published.
- Frontend code changes do not require copying backend code to the SERVER machine, but auto-update still requires copying `backend_server/app_update_config.json` to the SERVER machine and restarting the SERVER backend.
- `app_version.py` and `backend_server/app_update_config.json` must advertise the same new version. If the exe still has the old `APP_VERSION`, clients may keep seeing the update again after installing it.

## 13. Deploy Rules

Frontend-only source change:
- Done on the DEV machine.
- No backend code copy is needed.
- If only testing locally, no SERVER action is needed.
- If real users need the change, build `dist/DELTA_ONE.exe` on the DEV machine and publish it through the auto-update flow.
- For auto-update, copy `backend_server/app_update_config.json` from the DEV machine to `<SERVER_BACKEND_FOLDER>/app_update_config.json` on the SERVER machine, then restart the SERVER backend.

Backend code change:
- Edit files on the DEV machine first.
- Copy each changed backend file from the DEV machine to the matching backend path on the SERVER machine.
- Example: if [backend_server/routers/task_report.py](../backend_server/routers/task_report.py) changed locally, copy:

```text
DEV:    backend_server/routers/task_report.py
SERVER: <SERVER_BACKEND_FOLDER>/routers/task_report.py
```

- Restart the SERVER backend after copying.
- Mention exact files and restart requirement in the final answer.

Update manifest change:
- Edit [backend_server/app_update_config.json](../backend_server/app_update_config.json) on the DEV machine.
- Copy this exact file from the DEV machine to the SERVER machine:

```text
DEV:    backend_server/app_update_config.json
SERVER: <SERVER_BACKEND_FOLDER>/app_update_config.json
```

- Restart the SERVER backend.
- Make sure the advertised `file_size` and `download_url` match the uploaded exe.

Database/schema change:
- Treat this as a SERVER machine / production database action unless explicitly testing on `DeltaSupport_DEV`.
- Do not assume local schema equals production schema.
- State the SQL/script required and whether production DB needs a manual update.
- Task Follow has had real-schema differences before, especially ID/IDENTITY behavior.

## 14. Locked And Risky Areas

Do not change these unless the user explicitly asks:
- topbar layout
- window mode/resize behavior
- landing/start screen behavior
- Lock Screen
- `Sync Card to Ticket`
- Task Follow layout/redesign

High-risk files:
- `main.py`: root window, native Windows behavior, close/maximize/update startup.
- `main_app.py`: topbar, routing, notice, lock, logout, settings.
- `services/app_config.py`: central API target resolution.
- `stores/base_store.py`: shared store/thread/cache behavior.
- `stores/task_store.py`: Task Follow state and optimistic updates.
- `backend_server/routers/task_follow.py`: large Task Follow API surface.
- `backend_server/routers/admin.py`: admin API surface.

Window/topbar guardrails:
- Keep only the expected window states: `windowed` and `maximized`.
- Do not add custom maximize controls unless asked.
- Do not break the Windows `X` close button.
- Do not break `Log out -> Yes/No`.
- Do not break `Work Schedule` dropdown/click-outside.
- If touching destroyed widgets, guard with `winfo_exists()`.

If touching `main.py` or the logout/dropdown parts of `main_app.py`, manually test:
1. Open app.
2. Press Windows maximize button.
3. Return to windowed mode.
4. Hover window edges/corners.
5. Press `X`.
6. Use `Log out`, then `No`.
7. Use `Log out`, then `Yes`.
8. Open `Work Schedule` dropdown.
9. Click outside to close it.
10. Check terminal for Tkinter/Tcl/callback errors.

## 15. Task Follow Status

Task Follow is considered done for the current phase. Do not reopen, refactor, or redesign it unless the user asks.

Current behavior:
- UI remains in the existing Task area.
- `pages/process/follow_controller.py` owns the Follow flow.
- `stores/task_store.py` provides cache and optimistic updates.
- Search is local-first with about 400ms debounce.
- Board cache TTL is about 45 seconds.
- Worker threads do not touch Tkinter directly.
- Notice is polling/cache based, not true websocket push.
- Notice read/unread is persistent through backend + SQL.
- Handoff supports:
  - `Tech Team`
  - one user
  - multiple users in one task

Setup / Training current locked flow:
- Exact sections:
  - `I. SET UP HARDWARE`
  - `II. SET UP POS`
  - `III. TRAINING`
- `1st Training` complete moves to `2ND TRAINING`.
- `2nd Training` complete moves to `DONE`.
- `DONE` requires a note; frontend can fill the training-complete note.
- Saved training info is shown through the read-only review popup.
- Done setup/training tasks still depend on `Show All` and `Include Done`; do not special-case them into the board unless asked.

Task Follow backend tables involved:
- `dbo.TaskFollow`
- `dbo.TaskFollowLog`
- `dbo.TaskFollowNotificationRead`
- `dbo.TaskFollowRecipient`

If the user says notice order, zip code, or read/unread is wrong in the real app, check first:
- Was `backend_server/routers/task_follow.py` copied to the server?
- Was the backend restarted?
- Is production schema different from local schema?

## 16. Task Report Status

Task Report lives in [pages/task_report_page.py](../pages/task_report_page.py).

Current behavior:
- Daily Case Note form.
- Date Filter.
- Saved Reports.
- Create, update, delete report.
- Local search/filtering.
- Date range loading.
- Current technician/user mapping through backend/schedule logic.

Current layout:
- Two-column Task-style layout.
- Left small panel: `Daily Case Note`.
- Right large panel: `Date Filter` and `Saved Reports`.
- Page-level scroll was reduced/removed; Saved Reports keeps its own scroll behavior.

Task Report backend:
- `backend_server/routers/task_report.py`
- `backend_server/models.py`
- `services/task_report_service.py`

Recent Task Report work was intended to be frontend layout only. Avoid touching report API or unrelated Task flows unless requested.

## 17. Sync Card To Ticket

This flow is considered locked unless the user directly asks for it.

Rules already accepted:
- Save log only when user clicks `GET SQL Code`.
- Each click saves exactly one log row.
- Do not change UI, wording, or flow without a direct request.

Frontend:
- `pages/sql_page.py`
- `services/sql_tool_service.py`

Backend:
- `backend_server/routers/tool_logs.py`
- `backend_server/sql/create_sync_card_to_ticket_log_tables.sql`

## 18. Demo Hidden Navigation

[main_app.py](../main_app.py) currently has:

```python
DEMO_HIDDEN_NAV_ITEMS = {"POS", "SQL"}
```

This hides `POS` and `SQL` from the demo top navigation. Their code remains in the repo.

Do not delete POS/SQL logic just because the nav is hidden.

## 19. Useful Test Commands

Focused update tests:

```powershell
python -m unittest tests.test_update_service tests.test_app_update_router
```

Task Report router test:

```powershell
python -m unittest tests.test_task_report_router
```

Timezone/schedule tests:

```powershell
python -m unittest tests.test_timezone_service tests.test_timezone_utils tests.test_schedule_match_service
```

All tests:

```powershell
python -m unittest discover tests
```

Run targeted tests after small changes. Run broader tests when touching shared services, backend routers, update flow, timezone/schedule logic, or build/update behavior.

## 20. Quick AI Checklist Before Editing

Before changing code:
1. Identify whether the request is frontend-only, backend, build/update, or database.
2. Read the specific files involved; do not guess from old memory.
3. Check for existing dirty changes and do not revert unrelated work.
4. Keep the patch small.
5. For every instruction, label the machine: DEV machine or SERVER machine.
6. If touching backend, prepare exact file-copy and SERVER restart instructions.
7. If touching packaged-app behavior, state whether a new exe/update config is needed.
8. If the user must edit manually, say exactly which file to open, what text to find, what to replace it with, and what command to run.
9. If touching locked areas, test the related manual checklist.

Before final reply:
1. State what changed.
2. State what was not changed if the user asked for narrow scope.
3. State tests or checks run.
4. For backend changes, include copy/restart instructions.
5. For frontend changes, say whether users need a new exe build/publish.
6. For docs-only changes, say no app/backend behavior changed.
