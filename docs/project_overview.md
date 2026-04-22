# 📘 DeltaSupport — Tài Liệu Kỹ Thuật Toàn Diện

> Tài liệu này được tạo ra để giúp bạn và các AI hiểu toàn bộ cấu trúc app, dễ dàng hỏi và nhận trợ giúp mà không bị lạc.

---

## 1. 📋 Project Overview

### App này dùng để làm gì?
**DeltaSupport** là một **ứng dụng desktop nội bộ** dành cho đội Tech Support của một công ty cung cấp phần mềm POS cho tiệm nail.

Chức năng chính:
- **Quản lý Task**: Theo dõi tiến trình Follow merchant, Setup thiết bị, 1st & 2nd Training
- **Quản lý Lịch làm việc**: Đăng ký ca, xem lịch theo tuần, duyệt đơn nghỉ
- **Truy vấn SQL**: Chạy query trực tiếp lên database nội bộ
- **POS Lookup**: Tra cứu thông tin POS của merchant
- **Link / Data**: Chức năng liên kết dữ liệu (đang phát triển)
- **Thông báo realtime**: Nhận thông báo khi có task mới được assign
- **Admin**: Quản lý phê duyệt nội bộ (chưa chắc đầy đủ)

### Entry Point
```
main.py  ←  Chạy lệnh: python main.py
```

### API endpoint / network config
- Desktop app doc `API_BASE_URL` tu `services/app_config.py`.
- Thu tu uu tien cau hinh:
  1. Bien moi truong `DELTA_API_BASE_URL`
  2. File config `data/app_config.json`
  3. Gia tri mac dinh `http://127.0.0.1:8000`
- Cau hinh hien tai da ho tro che do `auto`:
  - Neu `api_base_url = "auto"` thi app se thu lan luot candidate URL va chon server tra ve JSON root `{"status": "API OK"}`
  - Thu tu candidate dang dung: LAN `http://192.168.80.110:8000` -> Tailscale `http://100.111.27.65:8000` -> localhost `http://127.0.0.1:8000`
- Neu can fix cung 1 endpoint, van co the set truc tiep `DELTA_API_BASE_URL` hoac `api_base_url` trong file config.
- Luu y van hanh:
  - Backend phai bind `0.0.0.0:8000`, khong chi `127.0.0.1`
  - Firewall tren may chu phai mo port `8000`
  - May dung ben ngoai phai dang nhap cung tailnet Tailscale
- Neu can doi endpoint theo moi truong, uu tien sua config/env, khong hardcode lai trong tung service.

### Các module lớn
| Module | Vai trò |
|--------|---------|
| `main.py` | Khởi động app, quản lý cửa sổ |
| `main_app.py` | Shell chính sau khi đăng nhập |
| `pages/` | Tất cả các trang UI |
| `services/` | Gọi API backend |
| `stores/` | Cache dữ liệu + quản lý state |
| `realtime/` | WebSocket nhận thông báo |
| `utils/` | Tiện ích dùng chung |
| `widgets/` | Widget UI tái sử dụng |
| `backend_server/` | Server FastAPI riêng (chạy song song hoặc độc lập) |

---

## 2. 🗂️ Folder Map

```
DeltaSupport/
│
├── main.py                  ← Entry point, khởi động app
├── main_app.py              ← Shell chính, navbar, routing các page
├── splash_screen.py         ← Màn hình chờ khi khởi động
│
├── pages/                   ← TẤT CẢ các màn hình UI
│   ├── login_page.py        ← Màn hình đăng nhập
│   ├── signup_page.py       ← Đăng ký tài khoản
│   ├── process_page.py      ← Trang Task chính (lớn nhất ~80KB)
│   ├── process/             ← Các module con của process_page
│   │   ├── layout.py        ← Dựng UI (form, canvas, button)
│   │   ├── logic.py         ← Business rules (template training, format phone)
│   │   ├── renderers.py     ← Vẽ canvas (bảng task board)
│   │   ├── service.py       ← Kết nối TaskStore, build payload
│   │   ├── handlers_ui.py   ← Xử lý sự kiện UI (search, handoff, calendar)
│   │   └── handlers/        ← Handlers nâng cao (chưa chắc hoàn chỉnh)
│   ├── task_page.py         ← Trang Task (phiên bản khác? cần xác nhận)
│   ├── sql_page.py          ← Trang truy vấn SQL (~45KB)
│   ├── schedule_setup_page.py ← Trang cài đặt lịch làm việc (~30KB)
│   ├── tech_schedule_page.py  ← Trang xem lịch theo tuần (~36KB)
│   ├── admin_approval_page.py ← Trang Admin (~38KB)
│   ├── leave_request_page.py  ← Trang gửi đơn xin nghỉ
│   ├── leave_summary_page.py  ← Trang xem tổng hợp nghỉ phép
│   ├── link_data_page.py      ← Trang Link/Data
│   ├── pos_page.py            ← Trang POS Lookup
│   └── pin_verify_dialog.py   ← Dialog xác thực PIN
│
├── services/                ← Gọi API backend (HTTP requests)
│   ├── auth_service.py      ← Xác thực, login, API_BASE_URL
│   ├── task_service.py      ← CRUD task + notifications
│   ├── task_follow_api_service.py ← API phụ trợ cho task follow
│   ├── schedule_service.py  ← Gọi API lịch làm việc
│   ├── schedule_setup_api_service.py ← API cài đặt lịch
│   ├── schedule_config_service.py    ← Config lịch
│   ├── schedule_people_service.py    ← Danh sách nhân viên trong lịch
│   ├── user_service.py      ← Thông tin user
│   ├── login_service.py     ← Đăng nhập
│   ├── signup_service.py    ← Đăng ký
│   ├── pos_service.py       ← POS lookup
│   └── sql_tool_service.py  ← Chạy query SQL
│
├── stores/                  ← Cache & State Management (lớp trung gian)
│   ├── base_store.py        ← Class cơ sở: TTL cache, lock, load pattern
│   ├── task_store.py        ← State cho task: list, filter, optimistic update
│   ├── notification_store.py← State cho thông báo realtime
│   ├── pos_store.py         ← (Stub, chưa hoàn thiện)
│   └── schedule_store.py    ← (Stub, chưa hoàn thiện)
│
├── realtime/
│   └── ws_client.py         ← WebSocket client nhận thông báo
│
├── utils/
│   ├── auth.py              ← Lưu/đọc token đăng nhập
│   └── theme.py             ← Cấu hình màu sắc/giao diện chung
│
├── widgets/
│   └── work_schedule_menu.py ← Widget dropdown lịch làm việc trên navbar
│
├── backend_server/          ← Server FastAPI (chạy riêng, không phải desktop)
│   ├── api_server.py        ← Entry point FastAPI
│   ├── database.py          ← Kết nối database
│   ├── models.py            ← Khai báo bảng dữ liệu
│   ├── routers/
│   │   ├── task_follow.py   ← API Task (~68KB — lớn nhất)
│   │   ├── work_schedule.py ← API Lịch làm việc (~37KB)
│   │   ├── admin.py         ← API Admin (~40KB)
│   │   ├── auth.py          ← API Đăng nhập/Đăng ký
│   │   ├── pin.py           ← API PIN xác thực
│   │   └── tool_logs.py     ← API ghi log tool
│   └── services/            ← Business logic phía server (chưa xác nhận nội dung)
│
├── data/                    ← Tài nguyên tĩnh (icon, config)
├── docs/                    ← Tài liệu nội bộ
└── tests/                   ← Tests (chưa xác nhận nội dung)
```

---

## 3. 📁 File-by-File Breakdown

### 🔵 `main.py`
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Khởi động app, tạo cửa sổ, show splash screen, điều hướng login → main_app |
| **Gọi từ** | Terminal: `python main.py` |
| **Gọi sang** | `login_page.py`, `main_app.py`, `splash_screen.py` |
| **Class chính** | `App(ctk.CTk)` |
| **Liên quan** | UI (window management), OS (ctypes để chỉnh style cửa sổ Windows) |
| **Rủi ro khi sửa** | 🔴 **Cao** — sửa sai app không khởi động được |
| **Gợi ý** | Không nên thay đổi gì ở đây trừ khi cần sửa cửa sổ |

---

### 🔵 `main_app.py` (~105KB — file lớn thứ hai)
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Là "shell" sau khi đăng nhập: navbar, routing, notification bell, lock screen, polling |
| **Gọi từ** | `main.py` sau khi login thành công |
| **Gọi sang** | Tất cả các `pages/*.py` |
| **Class chính** | `MainAppPage` |
| **Liên quan** | UI (navbar, layout), Routing, Polling notification, Realtime |
| **Rủi ro khi sửa** | 🔴 **Cao** — thay đổi ảnh hưởng toàn bộ app |
| **Gợi ý** | Nên tách phần polling và notification ra module riêng |

---

### 🔵 `pages/process_page.py` (~80KB — file lớn nhất)
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Trang Task chính: Follow merchant, Setup/Training, form nhập liệu, bảng task board |
| **Gọi từ** | `main_app.py → show_process_page()` |
| **Gọi sang** | `process/layout.py`, `process/logic.py`, `process/renderers.py`, `process/service.py`, `process/handlers_ui.py`, `process/follow_controller.py`, `process/setup_training_controller.py`, `pages/task_report_page.py`, `stores/task_store.py` |
| **Class chính** | `ProcessPage(ctk.CTkFrame)` |
| **Liên quan** | UI + Business Logic + API (qua store) + Polling |
| **Rủi ro khi sửa** | 🔴 **Cao** — file điều phối trung tâm của module Task |
| **Gợi ý** | Sau nhánh refactor hiện tại, file này nên giữ vai trò shell mỏng: init, shared helpers, lifecycle, delegate wrappers |

#### Ghi chú refactor Task module
- `ProcessPage` không còn nên chứa logic Follow hay Setup/Training chi tiết.
- `Task Follow` đã được gom sang `pages/process/follow_controller.py`.
- `Task Setup / Training` đã được gom sang `pages/process/setup_training_controller.py`.
- `Task Report` đang dùng `pages/task_report_page.py` để render phần report riêng.
- `process_page.py` hiện nên được xem như lớp nối: dựng khung chung, giữ shared helpers, rồi delegate sang controller tương ứng.

---

### 🟡 `pages/process/follow_controller.py`
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Chứa toàn bộ flow cho Task Follow: render UI, search/filter, board canvas, load detail, save/update |
| **Gọi từ** | `process_page.py` |
| **Gọi sang** | `stores/task_store.py`, `process/layout.py`, `process/service.py`, `process/handlers_ui.py` |
| **Class chính** | `TaskFollowController` |
| **Liên quan** | UI + Task workflow + Store events |
| **Rủi ro khi sửa** | 🔴 **Cao** — sửa sai ảnh hưởng trực tiếp luồng Follow đang chạy |
| **Gợi ý** | Khi fix lỗi Follow, ưu tiên sửa ở đây thay vì đưa logic quay lại `process_page.py` |

---

### 🟡 `pages/process/setup_training_controller.py`
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Chứa toàn bộ flow Setup / Training: checklist, training popup, complete stage, local draft, view mode |
| **Gọi từ** | `process_page.py` |
| **Gọi sang** | `process/layout.py`, `process/logic.py`, `process/renderers.py`, `process/service.py` |
| **Class chính** | `TaskSetupTrainingController` |
| **Liên quan** | UI + Training workflow + payload build |
| **Rủi ro khi sửa** | 🔴 **Cao** — sửa sai dễ ảnh hưởng Step I / II / III, complete flow và popup handoff/deadline |
| **Gợi ý** | Các thay đổi liên quan checklist training nên tập trung ở đây, không nhồi ngược lại vào `process_page.py` |

---

### 🟡 `pages/task_report_page.py`
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Render phần Task Report riêng thay vì để `process_page.py` ôm luôn phần report placeholder |
| **Gọi từ** | `process_page.py` |
| **Gọi sang** | `customtkinter` |
| **Class chính** | `TaskReportPage` |
| **Liên quan** | UI thuần |
| **Rủi ro khi sửa** | 🟢 **Thấp** |
| **Gợi ý** | Có thể build report thật sau này mà không đụng vào luồng Follow / Setup-Training |

---

### 🟡 `pages/process/layout.py` (~21KB)
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Dựng toàn bộ khung UI của trang Task (canvas, form, nút, deadline picker) |
| **Gọi từ** | `process_page.py` |
| **Gọi sang** | `customtkinter`, `tkinter` |
| **Class chính** | `ProcessLayout` |
| **Liên quan** | UI thuần túy |
| **Rủi ro khi sửa** | 🟡 **Trung bình** — sửa sai làm giao diện vỡ hoặc thiếu widget |
| **Gợi ý** | Ổn định. Chỉ sửa khi cần thay đổi bố cục hoặc thêm widget mới |

---

### 🟡 `pages/process/logic.py` (~12KB)
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Chứa toàn bộ business rules: template checklist training, format phone, sinh time slot |
| **Gọi từ** | `process_page.py`, `renderers.py` |
| **Gọi sang** | Không gọi API, thuần Python |
| **Class chính** | `ProcessLogic` |
| **Liên quan** | Business Logic |
| **Rủi ro khi sửa** | 🟢 **Thấp** — logic độc lập, dễ test |
| **Gợi ý** | Nếu có template training mới, thêm vào đây |

---

### 🟡 `pages/process/renderers.py` (~11KB)
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Vẽ bảng Task Board trên Canvas (header, từng row, màu theo deadline) |
| **Gọi từ** | `process_page.py` |
| **Gọi sang** | `tkinter.Canvas` |
| **Class chính** | `ProcessRenderer` |
| **Liên quan** | UI (Canvas drawing) |
| **Rủi ro khi sửa** | 🟡 **Trung bình** — sửa sai bảng task hiển thị sai |
| **Gợi ý** | Tốt. Có thể thêm màu mới hoặc cột mới tại đây |

---

### 🟡 `pages/process/service.py` (~8KB)
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Trung gian giữa ProcessPage và TaskStore: load data, build payload, validate form |
| **Gọi từ** | `process_page.py` |
| **Gọi sang** | `stores/task_store.py` |
| **Class chính** | `ProcessService` |
| **Liên quan** | Business Logic + Data |
| **Rủi ro khi sửa** | 🟡 **Trung bình** — sửa sai payload gửi API sai |
| **Gợi ý** | Ổn định |

---

### 🟡 `pages/process/handlers_ui.py` (~10KB)
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Xử lý sự kiện UI: search/filter task, render nút handoff, calendar deadline |
| **Gọi từ** | `process_page.py` |
| **Gọi sang** | Truy cập `self.page` (ProcessPage instance) |
| **Class chính** | `ProcessUIHandler` |
| **Liên quan** | UI Event Handling |
| **Rủi ro khi sửa** | 🟡 **Trung bình** |
| **Gợi ý** | Ổn định. Sẽ mở rộng khi thêm handler mới |

---

### 🔵 `stores/task_store.py` (~20KB)
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Cache và quản lý state danh sách task: load background, optimistic update, filter |
| **Gọi từ** | `process_page.py` qua `ProcessService` |
| **Gọi sang** | `services/task_service.py` |
| **Class chính** | `TaskStore(BaseStore)` |
| **Liên quan** | Data + Threading |
| **Rủi ro khi sửa** | 🔴 **Cao** — sửa sai gây mất data hoặc race condition |
| **Gợi ý** | Không sửa nếu không chắc về threading |

---

### 🔵 `stores/base_store.py`
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Class cơ sở cho tất cả stores: TTL cache, threading lock, load pattern |
| **Gọi từ** | `task_store.py`, `notification_store.py` |
| **Liên quan** | Data + Threading |
| **Rủi ro khi sửa** | 🔴 **Cao** — ảnh hưởng toàn bộ store layer |

---

### 🔵 `services/task_service.py` (~11KB)
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Gọi API task: get list, get detail, create, update, handoff options, notifications |
| **Gọi từ** | `stores/task_store.py` |
| **Gọi sang** | Backend API qua `requests` HTTP |
| **Class chính** | `TaskService` |
| **Liên quan** | API |
| **Rủi ro khi sửa** | 🟡 **Trung bình** |

---

### 🔵 `services/auth_service.py`
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Xác thực, PIN flow, gọi cac auth endpoint |
| **Gọi từ** | Login page, PIN dialog, cac luong auth |
| **Rủi ro khi sửa** | 🔴 **Cao** — sua sai de loi login / PIN flow |

### 🔵 `services/app_config.py`
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Resolve `API_BASE_URL` tu env/config/default, ho tro che do `auto` va probe LAN/Tailscale/local server — diem cau hinh API trung tam cua desktop app |
| **Gọi từ** | Hau het service HTTP |
| **Rủi ro khi sửa** | 🔴 **Cao** — sua sai la moi API deu hong hoac tro sai server |

---

### 🟡 `stores/notification_store.py` (~12KB)
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Quản lý state thông báo, polling định kỳ từ API |
| **Gọi từ** | `main_app.py` |
| **Liên quan** | Realtime (polling), Data |
| **Rủi ro khi sửa** | 🟡 **Trung bình** |

---

### 🟢 `pages/sql_page.py` (~45KB)
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Trang chạy SQL query nội bộ, hiển thị kết quả dạng bảng |
| **Rủi ro khi sửa** | 🟡 **Trung bình** — lớn nhưng tách biệt |

---

### 🟢 `pages/schedule_setup_page.py` & `tech_schedule_page.py`
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Cài đặt và xem lịch làm việc tuần |
| **Rủi ro khi sửa** | 🟡 **Trung bình** |

---

### 🟢 `pages/admin_approval_page.py` (~38KB)
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Trang Admin — duyệt yêu cầu nội bộ |
| **Rủi ro khi sửa** | 🟡 **Trung bình** |

---

### 🟢 `realtime/ws_client.py`
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | WebSocket client nhận push notification |
| **Rủi ro khi sửa** | 🟡 **Trung bình** |
| **Lưu ý** | Chưa chắc đang được dùng chính thức hay còn là stub |

---

### 🟢 `utils/auth.py`
| Thuộc tính | Chi tiết |
|-----------|---------|
| **Làm gì** | Lưu và đọc token đăng nhập (local file/registry) |
| **Rủi ro khi sửa** | 🟡 **Trung bình** |

---

## 4. 🔄 Runtime Flow

```
[ Người dùng chạy: python main.py ]
          ↓
    App(ctk.CTk) khởi động
          ↓
    Hiện Splash Screen (2.2 giây)
          ↓
    LoginPage hiện lên
    → User nhập username + password
    → auth_service gọi API đăng nhập
    → Nhận token + thông tin user
          ↓
    MainAppPage được tạo (shell chính)
    → Dựng navbar (POS, SQL, Task, Work Schedule...)
    → Bắt đầu polling notification (cứ X giây gọi API 1 lần)
    → Nếu có token lưu → giữ phiên
          ↓
    User bấm vào "Task"
    → show_process_page() được gọi
    → ProcessPage được khởi tạo
    → ProcessLayout dựng khung UI (canvas, form, nút)
    → load_follow_bootstrap() gọi TaskStore
    → TaskStore kiểm tra cache (TTL 45s)
      - Nếu cache còn hiệu lực → dùng luôn
      - Nếu hết hạn → gọi background thread → TaskService → API GET /task-follows
    → Kết quả trả về → TaskStore notify → ProcessPage redraw canvas
    → User click vào một task → load_task_detail()
      → TaskStore.ensure_detail() → API GET /task-follows/{id}
      → Form được điền thông tin
          ↓
    User bấm Save / Update
    → collect_follow_form_payload() validate form
    → TaskStore.create_item() / update_item()
      → Optimistic update (hiện ngay trên UI)
      → Background thread gọi API POST/PUT
      → Nếu thành công: xác nhận
      → Nếu thất bại: rollback + thông báo lỗi
```

### Điểm có Polling
| Nơi | Tần suất | Mục đích |
|-----|----------|---------|
| `main_app.py` | ~30-60s | Kiểm tra notification mới |
| `process_page.py` | Theo `follow_poll_after_id` | Refresh danh sách task |
| `notification_store.py` | Định kỳ | Đồng bộ thông báo |

---

## 5. ⚠️ Risk Map

### Files nguy hiểm nhất (sửa sai = vỡ app)
| File | Lý do nguy hiểm |
|------|----------------|
| `main.py` | Entry point — sửa sai app không chạy được |
| `main_app.py` | Shell toàn app — routing, navbar, polling |
| `services/app_config.py` | Chua cau hinh `API_BASE_URL` — sua sai = moi API deu hong |
| `stores/base_store.py` | Threading lock — sửa sai = race condition, crash ngẫu nhiên |
| `stores/task_store.py` | State task — sửa sai = mất data optimistic, crash |

### Files đang quá to, cần tách tiếp
| File | Kích thước | Vấn đề |
|------|-----------|--------|
| `main_app.py` | ~105KB | Ôm quá nhiều: routing, navbar, polling, notification, UI |
| `pages/process_page.py` | Đã giảm sau refactor | Giữ vai trò shell + shared helpers + delegates |
| `pages/process/follow_controller.py` | Mới tách | Gom logic Task Follow để sửa đúng chỗ |
| `pages/process/setup_training_controller.py` | Mới tách | Gom logic Setup / Training để tránh đụng chéo |
| `backend_server/routers/task_follow.py` | ~68KB | Router API quá lớn |
| `backend_server/routers/admin.py` | ~40KB | Tương tự |
| `pages/sql_page.py` | ~45KB | Chứa cả UI lẫn query logic |

### Chỗ có thể gây lag
| Nơi | Vấn đề |
|-----|--------|
| `process_page.py` polling | `after()` gọi liên tục → tích lũy nếu không cancel đúng |
| Canvas redraw trong `renderers.py` | Vẽ lại toàn bộ canvas mỗi lần refresh |
| `notification_store.py` polling | Cộng thêm 1 vòng API call nữa chạy nền |
| `main_app.py` polling | Nếu không throttle → gọi API liên tục |
| Background threads trong `task_store.py` | Nhiều thread chạy song song nếu user click nhanh |

---

## 6. 🗺️ Bản đồ nhanh cho AI hỗ trợ

Khi bạn hỏi AI về vấn đề cụ thể, hãy nói:

| Khi cần | Hướng AI đến |
|---------|-------------|
| Sửa giao diện Task board | `pages/process/layout.py` + `renderers.py` |
| Sửa nút, form, màu sắc Task | `pages/process/layout.py` |
| Sửa logic search/filter/calendar | `pages/process/handlers_ui.py` |
| Sửa template checklist training | `pages/process/logic.py` |
| Sửa cách lưu/gửi task | `pages/process/service.py` + `stores/task_store.py` |
| Sửa API endpoint Task | `services/task_service.py` |
| Sửa navbar / routing | `main_app.py` |
| Sửa đăng nhập | `pages/login_page.py` + `services/auth_service.py` |
| Sửa lịch làm việc | `pages/tech_schedule_page.py` + `schedule_setup_page.py` |
| Thêm trang mới | Tạo file trong `pages/`, đăng ký trong `main_app.py` |
| Sửa thông báo | `stores/notification_store.py` |

---

> 📌 **Lưu ý cho AI**: Trước khi sửa bất kỳ file nào có mức rủi ro 🔴 Cao, hãy đọc kỹ file đó và hỏi lại owner ý định thay đổi cụ thể là gì để tránh gây hỏng luồng chính của app.
