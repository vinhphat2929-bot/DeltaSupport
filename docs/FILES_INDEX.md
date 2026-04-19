# File map (Delta Assistant / Technical Support Tool)

Muc tieu: doc nhanh **toan bo file quan trong trong repo** (frontend desktop app + backend API), biet file nao lien quan khi can sua/ho tro.

> Luu y: repo co them `build/` va `dist/` (artifact build) va `__pycache__/` (file sinh ra khi chay). Khi doc code, uu tien nhom `.py`, `docs/`, `backend_server/sql/`, `data/`.

## Tong quan luong chay

- **Frontend desktop (CustomTkinter)**: `main.py` → `SplashScreen` → `LoginPage` → `MainAppPage` → (pages trong `pages/`)
- **Backend API (FastAPI)**: `backend_server/api_server.py` tao `FastAPI()` va include routers trong `backend_server/routers/*`
- **Database (SQL Server qua pyodbc)**: `backend_server/database.py` tao connection string

## Root (entry points)

- `main.py`
  - Entry point desktop app.
  - Setup window mode (windowed/maximized) va native window style (Windows API).
  - Mo splash, sau do show login, login xong vao `MainAppPage`.
- `main_app.py`
  - UI chinh sau login: top bar, menu, phan quyen theo role/department.
  - Dieu huong den pages: POS / SQL / Link-Data / Task / Work Schedule / Leave / Settings / Admin.
- `splash_screen.py`
  - Man hinh splash (logo + progress).
- `requirements.txt`
  - Dependency cho ca frontend + backend.
- `main.spec`
  - PyInstaller spec (build exe).

## Thu muc `pages/` (UI pages)

`pages/` la cac man hinh UI duoc `MainAppPage` goi.

- `pages/login_page.py`
  - Login UI, goi API login (qua `services/*`).
- `pages/signup_page.py`
  - UI dang ky tai khoan (OTP).
- `pages/pin_verify_dialog.py`
  - Dialog nhap PIN/OTP (lock/unlock, forgot pin).
- `pages/pos_page.py`
  - UI POS (doc/ghi du lieu POS tu JSON va/hoac goi API).
- `pages/sql_page.py`
  - UI cho chuc nang **Sync Card to Ticket** (co rule “da chot” trong `docs/README.md`).
- `pages/link_data_page.py`
  - UI link/data noi bo (doc tu `data/link_data.json`).
- `pages/process_page.py`
  - UI **Task Follow** (rule: giu UI cu, refactor theo tung buoc).
- `pages/task_page.py`
  - Task page/phan tach (neu co su dung: xem `MainAppPage.show_process_page` dang goi `ProcessPage`).
- `pages/tech_schedule_page.py`
  - UI work schedule theo tuan.
- `pages/leave_summary_page.py`
  - UI tong hop nghi theo thang.
- `pages/leave_request_page.py`
  - UI tao request nghi.
- `pages/schedule_setup_page.py`
  - UI cau hinh schedule setup (noi bo).
- `pages/admin_approval_page.py`
  - UI/Window danh cho admin manager (approve/reject/block/update user...).

## Thu muc `services/` (API clients / business helpers)

`services/` la lop goi API (requests) va cac helper lien quan.

- `services/auth_service.py`
  - API cho login/PIN flow (get/set/verify/change/reset PIN, forgot pin OTP), schedule...
- `services/login_service.py`
  - Helper login (neu duoc tach rieng).
- `services/signup_service.py`
  - API sign up + OTP.
- `services/user_service.py`
  - API thao tac user (admin).
- `services/task_service.py`
  - API layer cho Task Follow (frontend).
- `services/task_follow_api_service.py`
  - API wrapper rieng cho task follow (neu co tach endpoint).
- `services/schedule_service.py`
  - API work schedule.
- `services/schedule_people_service.py`
  - API lay danh sach nhan su / mapping (phuc vu schedule).
- `services/schedule_setup_api_service.py`
  - API cho schedule setup (save/active...).
- `services/schedule_config_service.py`
  - Luu config local (thuong doc/ghi JSON trong `data/`).
- `services/sql_tool_service.py`
  - API log cho Sync Card to Ticket (rule: log chi khi bam GET SQL Code).
- `services/pos_service.py`
  - POS-related service layer.

## Thu muc `stores/` (client-side state/cache)

- `stores/base_store.py`
  - Base in-memory store.
- `stores/task_store.py`
  - Cache/store cho Task Follow (rule: uu tien refactor store/service, khong dap UI).
- `stores/schedule_store.py`
  - Cache/store cho schedule.
- `stores/pos_store.py`
  - Cache/store cho POS data.
- `stores/__init__.py`
  - Package init.

## Thu muc `utils/` (shared utilities)

- `utils/theme.py`
  - Theme helpers (neu co).
- `utils/auth.py`
  - Auth-related helper (token/header, etc.).

## Thu muc `widgets/` (UI components)

- `widgets/work_schedule_menu.py`
  - Widget/menu lien quan Work Schedule (dropdown/menu items).

## Thu muc `realtime/` (websocket / realtime)

- `realtime/ws_client.py`
  - Websocket client (neu co su dung).
- `realtime/__init__.py`
  - Package init.

## Thu muc `backend_server/` (FastAPI backend)

- `backend_server/api_server.py`
  - FastAPI app, include routers.
- `backend_server/models.py`
  - Pydantic models cho request body.
- `backend_server/database.py`
  - Ket noi SQL Server qua `pyodbc`.
  - **Hien dang hard-code** server/db/user/pass.
- `backend_server/routers/`
  - `auth.py`: login/change password/register...
  - `admin.py`: admin user management (approve/reject/block/update/delete...).
  - `pin.py`: PIN flows (set/verify/change/forgot/reset).
  - `work_schedule.py`: work schedule APIs.
  - `tool_logs.py`: log cho Sync Card to Ticket.
  - `task_follow.py`: APIs cho Task Follow.
- `backend_server/services/`
  - `email_service.py`: gui email/OTP (neu co).
  - `audit_service.py`: ghi log/audit (neu co).
- `backend_server/sql/`
  - `create_task_follow_tables.sql`: tao table cho Task Follow.
  - `create_sync_card_to_ticket_log_tables.sql`: tao table log cho Sync Card to Ticket.
  - `seed_schedule_employee_config.sql`: seed/cau hinh schedule.

## Thu muc `data/` va `dist/data/`

- `data/*.json`: du lieu local cho app (POS/link_data/users/schedule_config...).
- `dist/data/*.json`: ban copy khi build/dist (phu thuoc quy trinh build).

## Thu muc `tests/`

- `tests/test_send_otp.py`
  - Test flow send OTP (backend/email).

## Thu muc `build/` va `dist/`

- `build/`: artifact tam khi build (PyInstaller) — khong can doc.
- `dist/`: output build (co `dist/data/*`) — dung khi dong goi.

---

## Huong dan chay tiep (Windows + PowerShell)

### 1) Setup moi truong Python (khuyen nghi)

Mo PowerShell tai root project:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r .\requirements.txt
```

### 2) Chay frontend (desktop app)

```powershell
python .\main.py
```

Neu loi import/GUI:
- Kiem tra Python version va da cai `customtkinter`, `pillow`.
- Kiem tra thu muc `data/` co `app.ico`, `logo.png`...

### 3) Chay backend local (FastAPI)

```powershell
cd .\backend_server
uvicorn api_server:app --reload
```

Neu loi DB:
- Cai “ODBC Driver 17 for SQL Server”
- Kiem tra `backend_server/database.py` (server/db/user/pass)

### 4) Debug nhanh: app dang goi API nao?

Trong `docs/README.md` co muc “Cau hinh API” (frontend dang goi endpoint remote). Khi can test local:
- Tim trong `services/*` xem base URL dang la gi
- Doi sang `http://127.0.0.1:8000` (neu can), sau do chay backend local nhu buoc (3)

