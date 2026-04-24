Project: Delta One
Stack: CustomTkinter (frontend) + FastAPI (backend) + SQL Server

Architecture:
Desktop app -> API -> SQL Server
KHÔNG cho client ghi thẳng DB

========================
RULE CỨNG (KHÔNG ĐƯỢC SAI)
========================

- Sửa nhỏ, đúng phạm vi
- Phần nào user nói đã ổn => KHÓA CỨNG

KHÔNG được:
- sửa topbar, window mode, landing screen
- sửa Lock Screen
- sửa Sync Card to Ticket
- sửa main.py (window handling) nếu không được yêu cầu

Task Follow:
- giữ UI trong pages/process_page.py
- chỉ sửa store / cache / service
- không đổi layout
- cache TTL ~45s
- debounce ~400ms
- notice = polling + local cache (chưa realtime)
- notice read/unread da co persistent theo backend + SQL
- uu tien local read ngay, sync batch nen, tranh spam API
- handoff da ho tro `Tech Team`, 1 user, hoac nhieu user trong 1 task

========================
RULE DEPLOY (SỐNG CÒN)
========================

Backend local ≠ backend server

Nếu chỉ sửa frontend / store:
=> KHÔNG cần copy lên server

Nếu sửa backend:
=> BẮT BUỘC phải ghi:
1. file nào sửa local
2. file nào cần copy lên server
3. có cần restart backend không

Thiếu 1 trong 3 => câu trả lời SAI

========================
TONE
========================

- giải thích từng bước
- không nhảy bước
- dễ hiểu
