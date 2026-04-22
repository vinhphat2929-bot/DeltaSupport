# Task Follow Status

Cap nhat: 22-04-2026

## 0. Trang thai chot

- Task Follow cho dot nay da chot.
- Cac hang muc `Setup & Training review` va `2ND TRAINING flow` da chot UI + chuc nang.
- Tru van de lag / hieu nang neu user mo yeu cau rieng, khong tu y sua tiep 2 hang muc nay.
- Neu khong co yeu cau moi tu user, khong tu y mo lai / refactor tiep / redesign them.
- File nay dung de danh dau ro phan nao da lam xong de AI/dev den sau khong dung vao nham.

## 1. Pham vi hien tai

Task Follow dang di theo huong:
- Frontend `pages/process_page.py`
- Frontend state/cache:
  - `stores/task_store.py`
  - `stores/notification_store.py`
- Frontend services:
  - `services/task_service.py`
  - `services/task_follow_api_service.py`
- Backend FastAPI router `backend_server/routers/task_follow.py`
- SQL tables:
  - `dbo.TaskFollow`
  - `dbo.TaskFollowLog`
  - `dbo.TaskFollowNotificationRead`
  - `dbo.TaskFollowRecipient`

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

### 19-04-2026

- Da doi `Ngay / Gio hen` sang popup nho ngay duoi nut `Choose Date & Time`.
- Popup deadline da co:
  - lich chon ngay
  - dropdown gio trong cung popup
  - `Confirm`
  - `Cancel`
- `Cancel`:
  - khong doi gia tri dang hien tren form
  - khong goi API
- `Confirm`:
  - moi cap nhat gia tri ngay gio hen len form
  - moi bat dau load lai handoff options
- Da bo flow goi API khi user dang go tung phan `date/time`.
- Da them cache cho handoff options theo bo gia tri:
  - `action_by`
  - `task_date`
  - `task_time`
  - `task_period`
- Neu `Confirm` cung gia tri cu thi khong goi lai API.
- Neu da co cache thi dung cache thay vi goi lai API.
- Da chot dai gio popup theo thu tu:
  - `08:00 PM`
  - `08:30 PM`
  - ...
  - `11:00 AM`
- Da giam khoang cach trong popup cho gon hon.
- Da sua loi create task bi hien popup gia `Task not found` do optimistic temp id.
- Da sua popup deadline de click chon gio trong dropdown khong bi dong popup qua som.
- Da co `NOTICE` popup tren topbar:
  - mo duoc popup
  - click notice de vao dung `Task Follow`
  - focus duoc task vua click
- Da them local cache/store rieng cho `NOTICE`:
  - load notice sau login
  - poll theo chu ky
  - co nut refresh tay
  - local read/unread trong session hien tai
- Da chinh `NOTICE` UI theo huong:
  - popup canvas nhe
  - card mem hon
  - unread dam mau hon + co cham tron
  - read nhat mau hon + khong con cham tron
  - toi da 4 notice trong khung thay ngay
  - co scrollbar de keo xem notice cu
- Da noi backend local endpoint `GET /task-follows/notifications` de:
  - sort theo `UpdatedAt DESC`, `TaskID DESC`
  - hien `MerchantName + ZipCode`
- Da doi `NOTICE` polling tu fixed interval sang dynamic polling:
  - fast poll tam thoi khi vua vao app / mo popup / co notice moi
  - normal poll khi app o trang thai binh thuong
- Da them cooldown cuc bo 3 giay cho cac nut goi API chu dong:
  - `NOTICE` refresh
  - `Task Follow` refresh
  - `Save`
  - `Update`
- Da co `read/unread` persistent that cho `NOTICE`:
  - local read ngay khi user bam notice
  - sync batch len backend theo user + task
  - luc dong app se flush not phan pending neu con
- Da them backend local endpoint `POST /task-follows/notifications/read`.
- Da bo sung co che chon nhieu user trong cung 1 task handoff:
  - UI handoff button chuyen tu single-select sang multi-select
  - `Tech Team` la option exclusive
  - backend luu recipient theo tung user cho moi task
  - notice co the map theo tung recipient user
- Da bo sung notification that cho truong hop handoff `Tech Team`:
  - user thuoc department `Technical Support` se nhan duoc notice cho task handoff `Tech Team`
- Da tach log `ASSIGN` rieng khoi note khi create/update task.
- UI history/log da gom dong `ASSIGN` va dong `note` vao cung 1 card:
  - dong assign nam tren
  - duoc to mau de nhin ro hon
  - note nam ben duoi trong cung card
- User da chot Task Follow tai day, khong mo rong them trong dot nay.

### 22-04-2026

- Da chot luong `SET UP & TRAINING` / `2ND TRAINING` theo huong dung chung 1 checklist training da luu.
- Da them popup `View Setup & Training Info` de xem lai noi dung setup/training da luu.
- Popup review hien:
  - merchant
  - zip code
  - stage
  - deadline
  - `training started at`
  - `training started by`
  - tung section / step / result / note dang read-only
- Popup review doc du lieu da luu tu `active_task.training_form`, backend map tu `dbo.TaskFollow.TrainingFormJson`.
- Nut `View Setup & Training Info` chi hien khi task co du lieu training da luu; task `DONE` chi giu nut xem lai, khong hien nut start training nua.
- Da chot ten 3 tab / section dung exact text:
  - `I. SET UP HARDWARE`
  - `II. SET UP POS`
  - `III. TRAINING`
- Da sua callback textbox de nhap note trong setup/training khong con loi bind event.
- Da chot flow `2ND TRAINING`:
  - van dung checklist training hien co
  - khi complete `1st training` -> task sang `2ND TRAINING`
  - khi complete `2nd training` -> task len `DONE` ngay
  - khong mo popup bat handoff moi cho buoc complete `2nd training`
  - deadline/handoff dang co duoc giu nguyen
  - backend van yeu cau note khi `DONE`, frontend da tu dien note tu noi dung `2nd training` hoac fallback `Completed 2nd Training`
- Da chot lai filter cho nhom setup/training theo co che cu:
  - van ton trong `Show All`
  - van ton trong `Include Done`
  - khong tu y ep task `DONE` hien ra chi vi la task setup/training
- Da co nut xem lai thong tin training ngay trong detail panel cua task setup/training khi task co saved training info.

## 3. Da lam duoc

### UI / Frontend

- Man `Follow` da co canvas board + task detail.
- Chon status bang button tren UI.
- Chon nguoi nhan ban giao bang button.
- Co option `Tech Team`.
- Click task de xem detail + history/log.
- Phone format theo dang `(XXX) XXX-XXXX`.
- Deadline chon qua popup nho ngay duoi nut `Choose Date & Time`.
- Deadline time da gop thanh 1 dropdown duy nhat trong popup.
- Chi `Confirm` moi commit gia tri ngay gio hen va goi cache/API handoff.
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
- Da sua optimistic create de khong spam popup loi gia trong luc task vua duoc tao.

### Setup / Training UI / Frontend

- Da co giao dien setup/training theo 3 tab:
  - `I. SET UP HARDWARE`
  - `II. SET UP POS`
  - `III. TRAINING`
- Da co popup `View Setup & Training Info` dang read-only de xem lai du lieu training da luu.
- Popup review chi hien khi task dang chon co `training_form`.
- Task `DONE` thuoc setup/training:
  - van xem lai duoc training info
  - khong bat dau training lai trong flow da chot
- Setup/training khong co behavior hien `DONE` dac cach; van phu thuoc `Show All` + `Include Done` nhu truoc.

### Notice UI / Frontend

- Topbar da co nut `NOTICE`.
- Dang co popup notice nho ngay duoi khu vuc notice.
- Notice click vao duoc task dung trong `Task Follow`.
- Notice da co local read/unread trong session:
  - unread: dam mau hon + co cham tron
  - read: nhat mau hon + khong con cham tron
- Badge notice giam ngay trong session sau khi user bam notice.
- Hien tai notice toi da 4 item trong khung, co scrollbar de xem item cu.
- `NOTICE` hien tai van la polling + local cache, chua phai realtime push.
- `NOTICE` da co persistent read/unread theo backend + SQL, khong con chi local session.
- Task handoff da ho tro:
  - `Tech Team`
  - 1 user
  - nhieu user trong cung 1 task

### Frontend call API

- Da them `services/task_follow_api_service.py`.
- Da co ham:
  - load board
  - load handoff options
  - load task detail
  - create task
  - update task
- `main_app.py` da goi notice qua store/cache, khong goi API truc tiep moi lan chi vi UI mo ra.
- Notice read da di theo huong:
  - local read ngay
  - gom nhieu task vua doc de sync batch
  - tranh goi API tung item neu user bam lien tiep
- Setup/training submit dang gui them:
  - `training_form`
  - `training_completed_tabs`
  - `training_started_at`
  - `training_started_by_username`
  - `training_started_by_display_name`

### Backend API

- Da them router `backend_server/routers/task_follow.py`.
- Da register router trong `backend_server/api_server.py`.
- Da them model request `TaskFollowUpsertRequest` trong `backend_server/models.py`.
- Da co endpoint:
  - `GET /task-follows/handoff-options`
  - `GET /task-follows`
  - `GET /task-follows/notifications`
  - `POST /task-follows/notifications/read`
  - `GET /task-follows/{task_id}`
  - `POST /task-follows`
  - `PUT /task-follows/{task_id}`
- `GET /task-follows` va `GET /task-follows/{task_id}` dang tra them:
  - `training_form`
  - `training_completed_tabs`
  - `training_started_at`
  - `training_started_by_username`
  - `training_started_by_display_name`

### SQL / Logic

- Data dang di theo `TaskFollow` + `TaskFollowLog`.
- Recipient cua task dang di theo `TaskFollowRecipient`.
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
- `NOTICE` backend local dang sort theo thoi diem cap nhat gan nhat (`UpdatedAt DESC`) va fallback tie-break theo `TaskID DESC`.
- `NOTICE` backend local da join recipient theo tung user, nen task handoff cho nhieu user van vao dung notice cua moi nguoi.
- Du lieu phuc vu `View Setup & Training Info` dang luu o:
  - `dbo.TaskFollow.TrainingFormJson`
  - `dbo.TaskFollow.TrainingCompletedTabsJson`
  - `dbo.TaskFollow.TrainingStartedAt`
  - `dbo.TaskFollow.TrainingStartedByUsername`
  - `dbo.TaskFollow.TrainingStartedByDisplayName`
- `View Setup & Training Info` khong co bang rieng; doc tu task detail cua `dbo.TaskFollow`.

## 4. Da noi den dau

### Main app

- `main_app.py` da truyen `current_user` vao `ProcessPage`.
- `login_page.py` da giu them `full_name` trong user context.
- Sau login vao `MainAppPage`, app dang dung home mot nhip ngan de load `NOTICE` nen truoc khi vao luong function.

### Display Name

- Backend dang uu tien lay `DisplayName` tu `TechScheduleEmployeeConfig`.
- Neu khong co thi fallback ve `Users.FullName`.

### Handoff options

- API `handoff-options` dang tra:
  - current display name
  - danh sach user active trong cung department
  - `Tech Team`

### Notice

- `NOTICE` hien tai la notification cho task handoff den user:
  - 1 user
  - nhieu user recipient trong cung 1 task
- `NOTICE` cung da vao duoc user department `Technical Support` khi task handoff cho `Tech Team`.
- Click notice da mo duoc dung task tren `Task Follow`.
- Trang thai `read/unread` da duoc luu persistent theo:
  - user
  - task
- Flow hien tai:
  - user bam notice -> local read ngay
  - store gom task da doc -> sync batch len backend
  - tat app mo lai -> backend tra `is_read` that neu da sync xong
- Task handoff cho nhieu user:
  - van hien summary tren task
  - notice se vao tung user co trong recipient list
- Neu backend server chua copy file local moi thi:
  - thu tu notice
  - `zip code`
  - endpoint notice moi
  - read/unread persistent
  se chua len dung tren app that.

## 5. Van de / ghi chu quan trong

- Schema DB that te co kha nang dang lech voi file SQL script.
- Da gap truong hop `TaskID` / `LogID` tren DB that khong dong nhat voi ky vong `IDENTITY`.
- Backend dang co logic retry/fallback de xu ly 2 truong hop:
  - cot ID la `IDENTITY`
  - cot ID la cot thuong `NOT NULL`

Neu sau nay van loi insert, can check schema that cua:
- `dbo.TaskFollow`
- `dbo.TaskFollowLog`
- `dbo.TaskFollowNotificationRead`
- `dbo.TaskFollowRecipient`

Neu user noi `NOTICE` van sai thu tu / khong co zip / khong doi theo code local:
- check da copy `backend_server/routers/task_follow.py` len may chu chua
- check da restart backend chua

Neu user gap timeout dang:
- `HTTPSConnectionPool(...ngrok-free.dev...)`
- `Read timed out`

thi uu tien nghi `ngrok` bi rot/chap chon truoc, khong voi ket luan la loi `Task Follow`.
User da xac nhan co truong hop restart `ngrok` xong la app dung lai binh thuong.

## 6. Ngoai pham vi dot nay

- Chua co notification realtime true push; hien tai la local cache + polling.
- Chua co co che realtime refresh board.
- Chua co phan trang / lazy load.
- Chua co audit doc lap / test automation cho luong Task Follow.
- Van de lag / hieu nang cua setup-training neu con ton tai khong nam trong muc "da chot", co the mo task rieng neu user yeu cau.

Ghi chu:
- Cac muc tren la backlog xa hon, khong phai viec dang mo.
- AI/dev den sau khong tu y lay cac muc nay ra lam tiep neu user chua mo yeu cau moi.

## 7. Files lien quan chinh

- `pages/process_page.py`
- `main_app.py`
- `stores/task_store.py`
- `stores/notification_store.py`
- `services/task_service.py`
- `services/task_follow_api_service.py`
- `backend_server/routers/task_follow.py`
- `backend_server/models.py`
- `backend_server/api_server.py`
- `backend_server/sql/create_task_follow_tables.sql`

## 8. Next steps de uu tien

1. Nang cap len notification realtime neu can, sau khi read/unread persistent da on.
2. Can nhac them co che retry/persist queue neu app bi tat dot ngot truoc khi flush notice read.
3. Can nhac test automation / audit rieng neu user muon mo tiep Task Follow sau nay.
