# DeltaSupport

Desktop app noi bo cho Delta Assistant, viet bang `CustomTkinter`, dung backend `FastAPI` + `SQL Server`.

## Vai tro tai lieu

- `docs/README.md`
  - gioi thieu project
  - stack
  - cau truc thu muc
  - cach chay
  - cac luong chinh
- `docs/AI_HANDOFF.md`
  - boi canh 2 may
  - rule deploy/copy backend
  - cach support user
  - vung nhay cam
  - cac phan da chot khong duoc tu sua
- `docs/WINDOW_AND_UI_GUARDRAILS.md`
  - rule rieng cho window/topbar/logout/dropdown
- `AGENTS.md`
  - luat lam viec ngan gon cho AI/dev den sau

## Tong quan

Project hien co 2 phan trong cung workspace:
- `frontend desktop app`: chay bang `main.py`
- `backend API`: nam trong thu muc `backend_server/`

Luong tong quat:
1. App mo `SplashScreen`
2. Sang `LoginPage`
3. Login goi API `/login`
4. Vao `MainAppPage`
5. Cac man hinh tiep tuc goi API backend khi can

## Cau truc chinh

Root:
- [main.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/main.py): entry point cua app desktop
- [main_app.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/main_app.py): layout chinh sau login, topbar, navigation, show page
- [splash_screen.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/splash_screen.py): man splash
- [requirements.txt](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/requirements.txt): dependency Python

Frontend pages:
- [pages/login_page.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/pages/login_page.py): login UI
- [pages/process_page.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/pages/process_page.py): task page hien tai; `Task Follow` dang giu UI cu tai day
- [pages/tech_schedule_page.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/pages/tech_schedule_page.py): lich lam viec theo tuan
- [pages/leave_summary_page.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/pages/leave_summary_page.py): tong hop nghi theo thang
- [pages/leave_request_page.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/pages/leave_request_page.py): tao request nghi
- [pages/admin_approval_page.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/pages/admin_approval_page.py): admin manager
- [pages/schedule_setup_page.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/pages/schedule_setup_page.py): cau hinh noi bo cho lich co dinh
- [pages/sql_page.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/pages/sql_page.py): function `Sync Card to Ticket`

Frontend services:
- [services/auth_service.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/services/auth_service.py): call API login / pin / schedule
- [services/signup_service.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/services/signup_service.py): call API sign up
- [services/schedule_config_service.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/services/schedule_config_service.py): luu config local cho `Schedule Setup`
- [services/sql_tool_service.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/services/sql_tool_service.py): call API log cho `Sync Card to Ticket`
- [services/task_service.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/services/task_service.py): API layer cho `Task Follow`

Frontend stores:
- [stores/base_store.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/stores/base_store.py): base in-memory store
- [stores/task_store.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/stores/task_store.py): local cache cho `Task Follow`

Backend:
- [backend_server/api_server.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/backend_server/api_server.py): FastAPI app
- [backend_server/database.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/backend_server/database.py): ket noi SQL Server
- [backend_server/models.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/backend_server/models.py): request models
- [backend_server/routers/auth.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/backend_server/routers/auth.py): login / change password / register
- [backend_server/routers/admin.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/backend_server/routers/admin.py): admin user management
- [backend_server/routers/pin.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/backend_server/routers/pin.py): PIN flow
- [backend_server/routers/work_schedule.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/backend_server/routers/work_schedule.py): work schedule APIs
- [backend_server/routers/tool_logs.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/backend_server/routers/tool_logs.py): log API cho `Sync Card to Ticket`
- [backend_server/routers/task_follow.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/backend_server/routers/task_follow.py): API cho `Task Follow`

## Cong nghe

Frontend:
- Python
- CustomTkinter
- requests
- Pillow

Backend:
- FastAPI
- Uvicorn
- pyodbc
- SQL Server

## Cach chay

### Chay frontend

Tu root project:

```powershell
python main.py
```

### Chay backend local

Tu thu muc `backend_server`:

```powershell
uvicorn api_server:app --reload
```

Hoac neu can host/port ro:

```powershell
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

## Cau hinh API

Frontend hien dang goi toi:
- `https://underline-steersman-crepe.ngrok-free.dev`

## Database

Ket noi DB local copy hien dang hard-code tai:
- [backend_server/database.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/backend_server/database.py)

Neu deploy that khac may:
- can sua file nay tren may chu hoac doi sang bien moi truong sau

## Cac luong chinh

### Dang nhap

Frontend:
- [pages/login_page.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/pages/login_page.py)

Backend:
- [backend_server/routers/auth.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/backend_server/routers/auth.py)

### Work Schedule

Frontend:
- [pages/tech_schedule_page.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/pages/tech_schedule_page.py)

Backend:
- [backend_server/routers/work_schedule.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/backend_server/routers/work_schedule.py)

### Sync Card to Ticket

Frontend:
- [pages/sql_page.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/pages/sql_page.py)

Backend log:
- [backend_server/routers/tool_logs.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/backend_server/routers/tool_logs.py)

Rule da chot:
- chi luu log khi user bam `GET SQL Code`
- moi lan bam `GET SQL Code` luu `1 dong`
- function nay da on theo y user, khong tu y chinh sua them neu user khong yeu cau truc tiep

### Task Follow

Frontend:
- [pages/process_page.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/pages/process_page.py)
- [stores/task_store.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/stores/task_store.py)
- [services/task_service.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/services/task_service.py)

Backend:
- [backend_server/routers/task_follow.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/backend_server/routers/task_follow.py)
- [backend_server/models.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/backend_server/models.py)

Rule da chot:
- giu UI cu cua `Task Follow`
- refactor theo tung buoc, khong dap ca page
- giai doan hien tai chi la cache/store local cho client
- neu chi sua frontend/store/service local thi khong can copy len may chu

## Goi y doc nhanh

Neu can hieu project nhanh, doc theo thu tu:
1. [AGENTS.md](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/AGENTS.md)
2. [docs/AI_HANDOFF.md](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/docs/AI_HANDOFF.md)
3. [docs/WINDOW_AND_UI_GUARDRAILS.md](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/docs/WINDOW_AND_UI_GUARDRAILS.md)
4. [main.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/main.py)
5. [main_app.py](/c:/Users/AIO%20Tech/Desktop/DeltaSupport/main_app.py)
