# Delta One

Desktop app noi bo cho Delta One, viet bang `CustomTkinter`, dung backend `FastAPI` + `SQL Server`.

## Vai tro tai lieu

- `docs/README.md`
  - gioi thieu project
  - stack
  - cau truc thu muc
  - cach chay
  - cac luong chinh
- `docs/FILES_INDEX.md`
  - ban do file (doc nhanh: file nao dung de lam gi)
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
- [main.py](../main.py): entry point cua app desktop
- [main_app.py](../main_app.py): layout chinh sau login, topbar, navigation, show page
- [splash_screen.py](../splash_screen.py): man splash
- [requirements.txt](../requirements.txt): dependency Python

Frontend pages:
- [pages/login_page.py](../pages/login_page.py): login UI
- [pages/process_page.py](../pages/process_page.py): shell chung cho module `Task`
- [pages/task_report_page.py](../pages/task_report_page.py): `Task -> Report`, daily case note + saved reports
- [pages/tech_schedule_page.py](../pages/tech_schedule_page.py): lich lam viec theo tuan
- [pages/leave_summary_page.py](../pages/leave_summary_page.py): tong hop nghi theo thang
- [pages/leave_request_page.py](../pages/leave_request_page.py): tao request nghi
- [pages/admin_approval_page.py](../pages/admin_approval_page.py): admin manager
- [pages/schedule_setup_page.py](../pages/schedule_setup_page.py): cau hinh noi bo cho lich co dinh
- [pages/link_data_page.py](../pages/link_data_page.py): link, sheet va data noi bo
- [pages/pos_page.py](../pages/pos_page.py): POS lookup
- [pages/sql_page.py](../pages/sql_page.py): function `Sync Card to Ticket`

Frontend services:
- [services/auth_service.py](../services/auth_service.py): call API login / pin / schedule
- [services/signup_service.py](../services/signup_service.py): call API sign up
- [services/schedule_config_service.py](../services/schedule_config_service.py): luu config local cho `Schedule Setup`
- [services/sql_tool_service.py](../services/sql_tool_service.py): call API log cho `Sync Card to Ticket`
- [services/task_service.py](../services/task_service.py): API layer cho `Task Follow`
- [services/task_report_service.py](../services/task_report_service.py): API layer cho `Task -> Report`

Frontend stores:
- [stores/base_store.py](../stores/base_store.py): base in-memory store
- [stores/task_store.py](../stores/task_store.py): local cache cho `Task Follow`

Backend:
- [backend_server/api_server.py](../backend_server/api_server.py): FastAPI app
- [backend_server/database.py](../backend_server/database.py): ket noi SQL Server
- [backend_server/models.py](../backend_server/models.py): request models
- [backend_server/routers/auth.py](../backend_server/routers/auth.py): login / change password / register
- [backend_server/routers/admin.py](../backend_server/routers/admin.py): admin user management
- [backend_server/routers/pin.py](../backend_server/routers/pin.py): PIN flow
- [backend_server/routers/work_schedule.py](../backend_server/routers/work_schedule.py): work schedule APIs
- [backend_server/routers/tool_logs.py](../backend_server/routers/tool_logs.py): log API cho `Sync Card to Ticket`
- [backend_server/routers/task_follow.py](../backend_server/routers/task_follow.py): API cho `Task Follow`
- [backend_server/routers/task_report.py](../backend_server/routers/task_report.py): API cho `Task -> Report`

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
- [backend_server/database.py](../backend_server/database.py)

Neu deploy that khac may:
- can sua file nay tren may chu hoac doi sang bien moi truong sau

## Cac luong chinh

### Ban do chuc nang / tien trinh hien tai

Top menu hien tai dang map voi nghiep vu nhu sau:

- `Task`
  - `Report`: daily case note, saved reports, local search, filter theo ngay
  - `Follow`: theo doi task follow merchant, handoff, deadline, note, notice
  - `Setup / Training`: checklist `I. SET UP HARDWARE`, `II. SET UP POS`, `III. TRAINING`; flow `1st Training` -> `2nd Training` -> `DONE`
- `Link / Data`
  - khu vuc link, sheet va data noi bo
- `Work Schedule`
  - `Work Schedule`: xem lich lam theo tuan
  - `Monthly Leave Summary`: tong hop nghi theo thang
  - `Schedule Setup`: cau hinh employee active / shift cho schedule
  - `Create Leave Request`: gui don nghi
- `POS`
  - POS lookup
- `SQL`
  - `Sync Card to Ticket`

Ghi chu demo build hien tai:

- `POS` va `SQL` dang duoc tam an khoi top menu de build demo.
- Code va page cua 2 muc nay van con trong repo; chi an navigation, khong xoa logic.

### Dang nhap

Frontend:
- [pages/login_page.py](../pages/login_page.py)

Backend:
- [backend_server/routers/auth.py](../backend_server/routers/auth.py)

### Work Schedule

Frontend:
- [pages/tech_schedule_page.py](../pages/tech_schedule_page.py)

Backend:
- [backend_server/routers/work_schedule.py](../backend_server/routers/work_schedule.py)

### Sync Card to Ticket

Frontend:
- [pages/sql_page.py](../pages/sql_page.py)

Backend log:
- [backend_server/routers/tool_logs.py](../backend_server/routers/tool_logs.py)

Rule da chot:
- chi luu log khi user bam `GET SQL Code`
- moi lan bam `GET SQL Code` luu `1 dong`
- function nay da on theo y user, khong tu y chinh sua them neu user khong yeu cau truc tiep

### Task Follow

Frontend:
- [pages/process_page.py](../pages/process_page.py)
- [stores/task_store.py](../stores/task_store.py)
- [services/task_service.py](../services/task_service.py)

Backend:
- [backend_server/routers/task_follow.py](../backend_server/routers/task_follow.py)
- [backend_server/models.py](../backend_server/models.py)

Rule da chot:
- giu UI cu cua `Task Follow`
- refactor theo tung buoc, khong dap ca page
- Task Follow dot hien tai da chot xong
- da co cache/store local + persistent notice read/unread + handoff nhieu user
- neu chi sua frontend/store/service local thi khong can copy len may chu
- can context day du thi doc them `docs/TASK_FOLLOW_STATUS.md`

### Task Report

Frontend:
- [pages/process_page.py](../pages/process_page.py)
- [pages/task_report_page.py](../pages/task_report_page.py)
- [services/task_report_service.py](../services/task_report_service.py)

Backend:
- [backend_server/routers/task_report.py](../backend_server/routers/task_report.py)
- [backend_server/models.py](../backend_server/models.py)

Mo ta:
- `Task -> Report` la daily case note form kem danh sach `Saved Reports`
- dang ho tro create / update / delete report, local search, filter theo ngay
- technician duoc map theo user dang login va co su dung du lieu schedule de xu ly phan lien quan

## Goi y doc nhanh

Neu can hieu project nhanh, doc theo thu tu:
1. [AGENTS.md](../AGENTS.md)
2. [docs/AI_HANDOFF.md](./AI_HANDOFF.md)
3. [docs/WINDOW_AND_UI_GUARDRAILS.md](./WINDOW_AND_UI_GUARDRAILS.md)
4. [main.py](../main.py)
5. [main_app.py](../main_app.py)
