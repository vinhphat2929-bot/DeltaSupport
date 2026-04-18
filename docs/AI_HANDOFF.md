# AI Handoff

Tai lieu nay danh cho AI/dev den sau.

## 1. Boi canh phai hieu truoc

- User rat quan tam cam giac UI va chi muon sua dung cho dang yeu cau.
- Neu user noi mot phan "da dung y" thi coi do la rang buoc cung.
- Project dang co boi canh `2 may`:
  - may dev: noi dang mo IDE va chat voi AI
  - may chu: noi backend that dang chay
- Frontend desktop goi `API`.
- Backend tren may chu ghi du lieu va log xuong `SQL Server`.
- Khong duoc de xuat huong de nhieu may client ghi thang vao `SQL Server`.

## 2. Rule deploy va backend

- Backend trong workspace nay chi la ban copy local, khong phai may chu that.
- Neu sua backend local thi thay doi khong tu co hieu luc tren may chu.
- Sau khi sua backend local, user phai:
  1. copy file da sua len may chu
  2. chep de file cu
  3. restart backend tren may chu
- Neu user noi "da sua roi ma app khong doi", phai kiem tra ngay:
  - da copy dung file len may chu chua
  - da restart backend chua

Neu dung cac file backend local copy nhu:
- `backend_server/api_server.py`
- `backend_server/database.py`
- `backend_server/models.py`
- `backend_server/routers/...`
- `backend_server/services/...`
- `backend_server/sql/...`

thi cuoi cau tra loi phai noi ro:
- file nao da sua local
- file nao can copy len may chu
- co can restart backend hay khong

## 3. Cach support user

- giai thich cham, ro, tung buoc
- khong nhay buoc
- khong dung giong day doi
- khong gia dinh user biet Git, deploy, API, schema, SQL migration
- neu co nhieu lua chon, dua lua chon de nhat truoc
- neu khong lam duoc, noi thang la chua lam duoc

## 4. Vung nhay cam

### `main.py`

Loi tung xay ra:
- maximize chet
- van hien icon resize o mep/goc
- keo resize duoc ngoai y user
- nut `X` khong dong app
- dialog `Yes/No` trong `Log out` khong bam duoc
- loi callback `ctypes`

Rule:
- khong sua `main.py` phan window handling neu user khong yeu cau truc tiep

### `main_app.py`

Vung nhay cam:
- `handle_click_outside`
- `work_schedule_dropdown`
- action `Log out`

Loi tung xay ra:
- `bad window path name`
- callback click-outside co dong dropdown da bi destroy
- loi day chuyen lam user tuong app hong toan bo

Rule:
- neu cham vao dropdown hoac click-outside, phai guard `winfo_exists()`
- khong goi `place_forget()` tren widget da bi destroy

## 5. Phan da chot, khong tu y sua

- UI tong the hien tai la ban user da ung.
- Khong duoc tu y redesign topbar, spacing, landing screen, window mode.
- `Lock Screen` hien tai da ok theo y user, khong duoc tu y sua them.
- `Sync Card to Ticket` trong muc `SQL` hien tai da ok theo y user, khong duoc tu y sua them.
- `Task Follow` UI cu trong `pages/process_page.py` dang la ban user muon giu.
- Neu lam `Task Follow`, chi duoc doi data flow/cache theo tung buoc; khong tu tach ra page UI moi neu user chua yeu cau.
- Uu tien patch nho tren UI cu cua `Task Follow`; khong duoc "lam lai cho sach" roi doi layout.

`Sync Card to Ticket` da chot:
- chi luu log khi user bam `GET SQL Code`
- moi lan bam `GET SQL Code` luu `1 dong`
- UI/wording/flow hien tai duoc coi la da chot

`Task Follow` da chot cho giai doan nay:
- buoc 1 chi la local cache/store cho task
- UI giu layout cu
- khong refactor ca app mot luc
- neu chi sua frontend/store/service local thi khong can copy len may chu
- chi khi sua backend local copy moi can copy len may chu va restart backend

## 6. Checklist neu cham vung nhay cam

Neu sua `main.py` hoac cac phan dropdown/logout cua `main_app.py`, phai test lai:

1. mo app bang `python main.py`
2. bam nut `X`
3. bam nut vuong Windows
4. re chuot vao mep/goc cua so
5. `Log out` -> bam `Yes`
6. `Log out` -> bam `No`
7. mo dropdown `Work Schedule`
8. click ra ngoai de dong dropdown
9. quan sat terminal xem co loi `Tkinter`, `TclError`, `ctypes callback` khong
