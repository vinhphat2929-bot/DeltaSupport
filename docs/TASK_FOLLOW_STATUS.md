# Task Follow Status

Cap nhat: 18-04-2026

## 1. Pham vi hien tai

Task Follow dang di theo huong:
- Frontend `pages/process_page.py`
- Frontend API service `services/task_follow_api_service.py`
- Backend FastAPI router `backend_server/routers/task_follow.py`
- SQL tables:
  - `dbo.TaskFollow`
  - `dbo.TaskFollowLog`

Khong co bang status rieng.

## 2. Timeline

### 18-04-2026

- Da noi UI `Follow` voi backend that.
- Da co create task / update task / load detail / load history.
- Da co handoff options theo user cung department + `Tech Team`.
- Da co `Show All` + `Include Done`.
- Search hien tai di theo mode dang xem:
  - board mode: overdue + 3 ngay toi
  - show all mode: tat ca task active
  - include done mode: co hien task `DONE`
- Da chot flow form:
  - task dang chon thi dung `Update`
  - `Save` khong duoc dung de tao nham task moi khi dang sua task cu
- Khi `Status = DONE`:
  - bat buoc phai nhap note
  - history se ghi cau tieng Anh dang `Hoang has marked the task as done with note: ...`
- Khi `Update`:
  - note duoc ghi vao history/log
  - `CurrentNote` tren task duoc clear ve rong
- Da chinh mau board theo deadline gan:
  - hom nay: do
  - ngay mai: vang
  - ngay mot: xanh duong
- Da chinh sort board theo deadline gan nhat, xet ca ngay + gio.
- Da chinh lai layout `Task Board` de khong bi scale cao bat thuong khi it task.

## 3. Da lam duoc

### UI / Frontend

- Man `Follow` da co canvas board + task detail.
- Chon status bang button tren UI.
- Chon nguoi nhan ban giao bang button.
- Co option `Tech Team`.
- Click task de xem detail + history/log.
- Phone format theo dang `(XXX) XXX-XXXX`.
- Deadline date co validate input tren UI.
- Deadline time chon bang `time + AM/PM`.
- Co mau phan biet task theo deadline gan:
  - hom nay: do
  - ngay mai: vang
  - ngay mot: xanh duong
- Board co scrollbar doc + ngang.
- Da co `Show All` + `Include Done`.
- Board da sort task theo deadline gan nhat, xet ca ngay + gio.
- Board khong con bi scale cao bat thuong khi it task.
- Form da tach ro che do:
  - task moi -> `Save`
  - task cu -> `Update`
- Khi `DONE` bat buoc phai co note.
- Sau khi `Update`, note tren form/task se duoc clear va chi giu trong history/log.

### Frontend call API

- Da them `services/task_follow_api_service.py`.
- Da co ham:
  - load board
  - load handoff options
  - load task detail
  - create task
  - update task

### Backend API

- Da them router `backend_server/routers/task_follow.py`.
- Da register router trong `backend_server/api_server.py`.
- Da them model request `TaskFollowUpsertRequest` trong `backend_server/models.py`.
- Da co endpoint:
  - `GET /task-follows/handoff-options`
  - `GET /task-follows`
  - `GET /task-follows/{task_id}`
  - `POST /task-follows`
  - `PUT /task-follows/{task_id}`

### SQL / Logic

- Data dang di theo `TaskFollow` + `TaskFollowLog`.
- Search theo `MerchantName`.
- Board chi load task:
  - `IsActive = 1`
  - `Status <> DONE`
  - co `DeadlineDate`
  - qua han hoac trong 3 ngay toi
- Task qua han chua done duoc day len dau.
- Khi create/update co ghi log vao `TaskFollowLog`.
- Log luu:
  - ai update / note
  - note gi
  - status
  - handoff from / to
  - thoi gian

## 4. Da noi den dau

### Main app

- `main_app.py` da truyen `current_user` vao `ProcessPage`.
- `login_page.py` da giu them `full_name` trong user context.

### Display Name

- Backend dang uu tien lay `DisplayName` tu `TechScheduleEmployeeConfig`.
- Neu khong co thi fallback ve `Users.FullName`.

### Handoff options

- API `handoff-options` dang tra:
  - current display name
  - danh sach user active trong cung department
  - `Tech Team`

## 5. Van de / ghi chu quan trong

- Schema DB that te co kha nang dang lech voi file SQL script.
- Da gap truong hop `TaskID` / `LogID` tren DB that khong dong nhat voi ky vong `IDENTITY`.
- Backend dang co logic retry/fallback de xu ly 2 truong hop:
  - cot ID la `IDENTITY`
  - cot ID la cot thuong `NOT NULL`

Neu sau nay van loi insert, can check schema that cua:
- `dbo.TaskFollow`
- `dbo.TaskFollowLog`

## 6. Chua hoan tat / pending

- Chua co notification that cho truong hop handoff `Tech Team`.
  - Hien tai moi luu du lieu handoff/log.
- Chua co co che realtime refresh board.
- Chua co phan trang / lazy load.
- Chua co rule loai user ra khoi handoff list neu task duoc tao vao ngay off cua user do.
- Chua co co che chon nhieu user trong cung 1 task handoff.
- Chua co UI / backend notification that de thong bao task toi user.
- Chua co audit doc lap / test automation cho luong Task Follow.

## 7. Files lien quan chinh

- `pages/process_page.py`
- `services/task_follow_api_service.py`
- `backend_server/routers/task_follow.py`
- `backend_server/models.py`
- `backend_server/api_server.py`
- `backend_server/sql/create_task_follow_tables.sql`

## 8. Next steps de uu tien

1. Task tao vao ngay trung ngay off cua user nao thi user do se khong duoc hien trong danh sach handoff.
2. Bo sung co che chon nhieu user de handoff trong cung 1 task.
3. Thiet ke nut / luong thong bao de co the gui notification toi user khi co task moi.
4. Khi task quá hạn mà chưa cập nhật done, hiện lên trên cùng
