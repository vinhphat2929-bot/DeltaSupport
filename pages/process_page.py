import calendar
import re
import tkinter as tk
from datetime import datetime
import time
from tkinter import messagebox

import customtkinter as ctk

from services.task_service import TASK_STATUSES
from stores.task_store import TaskStore


BG_PANEL = "#f3ede4"
BG_PANEL_INNER = "#fffaf3"
BG_CANVAS = "#f7efe2"
BORDER = "#c79a4c"
BORDER_SOFT = "#d7b57d"
TEXT_DARK = "#2a221d"
TEXT_MUTED = "#6f5d4f"
TEXT_LIGHT = "#f5efe6"
BTN_ACTIVE = "#c58b42"
BTN_ACTIVE_HOVER = "#d49a50"
BTN_IDLE = "#5a483d"
BTN_IDLE_HOVER = "#6a5548"
BTN_DARK = "#3a2d25"
BTN_DARK_HOVER = "#4b3b31"
INPUT_BG = "#fffaf3"
INPUT_BORDER = "#d1b180"
CANVAS_HEADER = "#4b382c"
CANVAS_ROW = "#fffaf3"
CANVAS_ROW_ALT = "#fcf5eb"
CANVAS_OVERDUE = "#fde2e2"
CANVAS_OVERDUE_TEXT = "#7f1d1d"
CANVAS_TODAY = "#fde2e2"
CANVAS_TODAY_TEXT = "#7f1d1d"
CANVAS_TOMORROW = "#fff4d6"
CANVAS_TOMORROW_TEXT = "#7c4a03"
CANVAS_DAY_AFTER = "#dbeafe"
CANVAS_DAY_AFTER_TEXT = "#1d4ed8"

STATUS_META = {
    "FOLLOW": {"bg": "#2d6cdf", "text": "#ffffff"},
    "FOLLOW REQUEST": {"bg": "#2563eb", "text": "#ffffff"},
    "CHECK TRACKING NUMBER": {"bg": "#0f766e", "text": "#ffffff"},
    "SET UP & TRAINING": {"bg": "#9333ea", "text": "#ffffff"},
    "2ND TRAINING": {"bg": "#0ea5a3", "text": "#ffffff"},
    "MISS TIP / CHARGE BACK": {"bg": "#f59e0b", "text": "#2a221d"},
    "DONE": {"bg": "#ef4444", "text": "#ffffff"},
    "DEMO": {"bg": "#ec4899", "text": "#ffffff"},
}

TRAINING_RESULT_OPTIONS = ["", "DONE", "X"]
TRAINING_CANVAS_BG = "#fffef9"
TRAINING_BANNER_BG = "#ffef3a"
TRAINING_SUBHEADER_BG = "#21d8e2"
TRAINING_GROUP_BG = "#fff8ec"

FIRST_TRAINING_TEMPLATE = [
    {
        "section_key": "devices",
        "title": "I. SET UP CÁC THIẾT BỊ",
        "subtitle": "(Trước khi set up, vào ASANA check trong mục Tracking Number xem bên mình gửi ra những thiết bị gì)",
        "rows": [
            {"kind": "normal", "step": "1", "label": "PC / Duo"},
            {"kind": "normal", "step": "2", "label": "Máy cà thẻ"},
            {"kind": "normal", "step": "3", "label": "Tablet Check-In (nếu có)"},
            {"kind": "normal", "step": "4", "label": "Printer"},
            {"kind": "normal", "step": "5", "label": "Scanner."},
            {"kind": "normal", "step": "6", "label": "Cashdraw"},
            {"kind": "normal", "step": "7", "label": "Check đã Install Google Drive chưa, và check link backup trong POS đúng thư mục chưa"},
            {"kind": "normal", "step": "8", "label": "Check ATLED Cloud / ATLED Services\nSet Automatic + Restart the services"},
            {"kind": "normal", "step": "9", "label": "Check Windows Update đã dowload và update đủ file chưa\n(Khi vào Windows update thấy đã đủ thì disable Windows Update trong Services)", "default_note": "nếu chưa thì sau khi set up, training, log router (nếu có) thì cho win update xong mới stop"},
            {"kind": "normal", "step": "10", "label": "Vào Windows Security -> Virus & Threat protection\nTắt Real-time protection & Dev Drive protection (nếu có)"},
            {"kind": "normal", "step": "11", "label": "Đo tốc độ mạng của tiệm\n(nếu mạng quá yếu thì nhớ tiệm đi dây LAN ra quầy & request ship router)"},
            {"kind": "normal", "step": "12", "label": "Xem ở quầy có sợi dây LAN nào không\n(nếu không có LAN thì kết nối wifi tiệm)"},
            {"kind": "normal", "step": "13", "label": "Check xem đang dùng nhà mạng nào, log được vào router không\n(nếu login được thì ưu tiên kết nối mạng 5G, thiết bị nào không có thì kết nối 2.4Ghz,\nkhông biết cách check thì hỏi Tech khác)\n(Trường hợp log-in được vào router thì log-in và Setup IP sau khi hoàn tất buổi 1st Training)"},
            {"kind": "group", "label": "CHECK TRÊN MÁY CÀ THẺ"},
            {"kind": "normal", "step": "14", "label": "Schedule Reboot Time -> ON (set auto 5:00 AM)"},
            {"kind": "normal", "step": "", "label": "Screen time out -> Never"},
            {"kind": "normal", "step": "", "label": "Daydream -> OFF"},
            {"kind": "normal", "step": "", "label": "ON Dedicated device mode"},
        ],
    },
    {
        "section_key": "pos",
        "title": "II. SET UP POS",
        "subtitle": "(Phải check list setup xong trước khi vào bước này)",
        "rows": [
            {"kind": "normal", "step": "1", "label": "Check vào Show Waiting List\n(thông nhất 1 cách tính tiền đơn giản nhất cho tất cả các tiệm mới)"},
            {"kind": "normal", "step": "2", "label": "Set up thợ & lương thợ"},
            {"kind": "normal", "step": "3", "label": "Hỏi tiệm có thu tiền Supply/Hold tip/ hoặc bất kỳ tiền gì của thợ không ?\n(Nếu có thu thì hỏi tiệm muốn ăn hay muốn hiện phần thu đó)"},
            {"kind": "normal", "step": "3", "label": "Set up giờ đóng-mở cửa\n(hỏi thêm first & last booking trước bao nhiêu tiếng,\ngửi tin nhắn remind trước bao lâu)"},
            {"kind": "normal", "step": "4", "label": "Hỏi tiệm có thu tiền TAX (thuế bang) không\n(nếu thu thì thu trên cash - credit hay thu cả 2)\n(sẵn check lại rate trên POS - ASANA khớp chưa)"},
            {"kind": "normal", "step": "5", "label": "Hỏi tiệm tiền phần DISCOUNT cho khách sẽ do ai chịu"},
            {"kind": "normal", "step": "6", "label": "Hỏi tiệm cách chia turn"},
            {"kind": "normal", "step": "7", "label": "Hỏi tiệm cách tính điểm / redeem điểm"},
            {"kind": "normal", "step": "8", "label": "Set up promotion\nBirthday, Reminder, New Client (set up & giải thích cách hoạt động)"},
            {"kind": "normal", "step": "9", "label": "Tắt Slide ở trong phần check-in (discount 50%)"},
            {"kind": "normal", "step": "8", "label": "Giải đáp thêm các thắc mắc & các yêu cầu khác của tiệm\n(Nhớ NOTE lại)"},
        ],
    },
    {
        "section_key": "first_training",
        "title": "III. BẮT ĐẦU TRAINING",
        "subtitle": "(Training sau khi đã hoàn thành các bước trên)\n1st Training\n(Ở buổi đầu training, bảo tiệm chuẩn bị sẵn 1 cái thẻ để charge test và để hướng dẫn các thao tác sau Payment)\n(Nhớ lưu ý bảo tiệm chỉ charge $5 để test, và warning tiệm không được dùng thẻ cá nhân charge vào máy dây những số tiền lớn)",
        "rows": [
            {"kind": "normal", "step": "1", "label": "Hướng dẫn tiệm đầu ngày vào mở đúng App ATLED POS trên PC\n(Hướng dẫn từ màn hình Desktop -> Double tap vào ICON POS)"},
            {"kind": "normal", "step": "2", "label": "Hướng dẫn khách Checkin thợ"},
            {"kind": "normal", "step": "3", "label": "Hướng dẫn khách CheckIn Customer"},
            {"kind": "group", "label": "HƯỚNG DẪN CÁC THAO TÁC TRONG MỤC PAYMENT"},
            {"kind": "normal", "step": "4", "label": "Hướng dẫn khách CheckOut Payment\n(Hướng dẫn luôn cách tính tiền khi có nhiều thợ làm 1 ticket)"},
            {"kind": "normal", "step": "", "label": "Hướng dẫn cách Discount tính cho Owner hay Employee\n(đã set mặc định ở bước set up, nhưng hướng dẫn lại nếu cần thay đổi lúc tính tiền)"},
            {"kind": "normal", "step": "", "label": "Hướng dẫn khách AddTip, Sửa TIP, Chia TIP"},
            {"kind": "normal", "step": "", "label": "Hướng dẫn tiệm đổi qua thợ khác khi tính tiền sai thợ"},
            {"kind": "normal", "step": "", "label": "Hướng dẫn Sale / Redeem Gift Card"},
            {"kind": "normal", "step": "", "label": "Hướng dẫn check điểm / redeem điểm"},
            {"kind": "normal", "step": "5", "label": "Hướng dẫn đặt lịch hẹn Appointment"},
            {"kind": "normal", "step": "6", "label": "Check xem đã có Data Cus + Gift chưa"},
            {"kind": "normal", "step": "7", "label": "Hướng dẫn tiệm những cách liên hệ Technical Support:\n1: Trường hợp cần hỗ trợ gấp -> Gọi thẳng vào Hotline (có dán trên máy và ấn phím 2)\n2: Cần hỗ trợ bất kỳ thông tin nào, không gấp -> Bấm nút Support ngoài giao diện chính\nDùng lời nói để tạo sự yên tâm cho tiệm là trong quá trình đi với Công ty mình thì luôn có người hỗ trợ từ lúc tiệm mở cửa đến lúc đóng cửa. Cần hỗ trợ gì cứ liên hệ."},
            {"kind": "normal", "step": "8", "label": "Done 1st Training\nGiải đáp thêm các thắc mắc & các yêu cầu khác của tiệm\nHẹn thời gian liên hệ lại để 2nd Training\n(sau buổi đầu thì hầu như tiệm đã có thể sử dụng, tiệm làm quen thao tác dần và hướng dẫn liên hệ số HOTLINE của Tech)\n(Nhớ NOTE lại)"},
        ],
    },
]

SECOND_TRAINING_TEMPLATE = [
    {
        "section_key": "second_training",
        "title": "2nd Training",
        "subtitle": "",
        "rows": [
            {"kind": "normal", "step": "1", "label": "Hướng dẫn khách tạo Promotion"},
            {"kind": "normal", "step": "2", "label": "Booking Online"},
            {"kind": "normal", "step": "3", "label": "Mua SMS"},
            {"kind": "normal", "step": "4", "label": "Xem Report, tính lương cho thợ"},
            {"kind": "normal", "step": "5", "label": "Hỏi lại những thao tác ở buổi đầu xem có lấn cấn ở đâu không"},
            {"kind": "normal", "step": "6", "label": "Hướng dẫn tải app và sử dụng app ATLED REPORT"},
            {"kind": "normal", "step": "7", "label": "Done 2nd Training\nGiải đáp thêm các thắc mắc & các yêu cầu khác của tiệm\n(Nhớ NOTE lại)"},
        ],
    },
]


class ProcessPage(ctk.CTkFrame):
    def __init__(self, parent, initial_section="report", current_user=None, initial_task_id=None):
        super().__init__(parent, fg_color="transparent")

        self.initial_section = initial_section
        self.initial_task_id = initial_task_id
        self.current_user = current_user or {}
        self.current_username = str(self.current_user.get("username", "")).strip()
        self.current_full_name = str(self.current_user.get("full_name", "")).strip()
        self.current_department = str(self.current_user.get("department", "")).strip()
        self.current_team = str(self.current_user.get("team", "General")).strip() or "General"
        self.current_display_name = self.current_full_name or self.current_username

        self.store = TaskStore()

        self.selected_status = "FOLLOW"
        self.selected_handoff_to = "Tech Team"
        self.selected_handoff_targets = ["Tech Team"]
        self.status_buttons = {}
        self.handoff_buttons = {}
        self.handoff_options = [{"username": "", "display_name": "Tech Team", "type": "TEAM"}]
        self.canvas_row_hits = []
        self.deadline_time_slots = self.build_deadline_time_slots()
        self.confirmed_deadline_date = ""
        self.confirmed_deadline_time = ""
        self.pending_deadline_date = ""
        self.pending_deadline_time = self.deadline_time_slots[0] if self.deadline_time_slots else ""
        self.deadline_popup_frame = None
        self.deadline_popup_month = datetime.now().replace(day=1)
        self.deadline_calendar_hits = []
        self.follow_layout_mode = None
        self.active_scroll_target = None
        self.follow_mousewheel_bind_id = None
        self.follow_poll_after_id = None
        self.follow_refresh_button = None
        self.follow_action_cooldown_ms = 3000
        self.follow_action_ready_at = {}
        self.follow_action_inflight = set()
        self.follow_action_after_ids = {}

        self.follow_tasks = []
        self.filtered_follow_tasks = []
        self.active_task = None
        self.training_result_vars = {}
        self.training_note_entries = {}
        self.training_note_values = {}
        self.training_row_cards = []
        self.training_canvas = None
        self.training_canvas_window_map = {}
        self.training_canvas_row_layout = []
        self.training_canvas_flat_rows = []
        self.training_canvas_content_height = 0
        self.training_canvas_after_id = None
        self.follow_search_scope = "board"
        self.follow_show_all = False
        self.follow_include_done = False
        self.follow_board_min_height = 220
        self.follow_board_max_height = 520
        self.follow_board_height = self.follow_board_min_height
        self.current_task_section = (
            initial_section if initial_section in {"follow", "setup_training"} else "follow"
        )
        self.pending_focus_task_id = int(initial_task_id) if initial_task_id not in (None, "") else None

        if self.pending_focus_task_id:
            self.follow_show_all = True

        self.build_ui()
        self.render_section(initial_section)

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.header_card = ctk.CTkFrame(
            self,
            fg_color=BG_PANEL,
            corner_radius=22,
            border_width=1,
            border_color=BORDER,
        )
        self.header_card.grid(row=0, column=0, sticky="ew", pady=(4, 12))

        self.title_label = ctk.CTkLabel(
            self.header_card,
            text="Task",
            font=("Segoe UI", 20, "bold"),
            text_color=TEXT_DARK,
        )
        self.title_label.pack(anchor="w", padx=22, pady=(18, 4))

        self.subtitle_label = ctk.CTkLabel(
            self.header_card,
            text="Task function will be built here.",
            font=("Segoe UI", 13),
            text_color=TEXT_MUTED,
            justify="left",
        )
        self.subtitle_label.pack(anchor="w", padx=22, pady=(0, 18))

        self.body_card = ctk.CTkFrame(
            self,
            fg_color=BG_PANEL,
            corner_radius=22,
            border_width=1,
            border_color=BORDER,
        )
        self.body_card.grid(row=1, column=0, sticky="nsew", pady=(0, 4))
        self.body_card.grid_columnconfigure(0, weight=1)
        self.body_card.grid_rowconfigure(0, weight=1)

    def destroy(self):
        self.close_deadline_popup()
        self.unbind_follow_mousewheel()
        if self.follow_poll_after_id:
            self.after_cancel(self.follow_poll_after_id)
            self.follow_poll_after_id = None
        for after_id in list(self.follow_action_after_ids.values()):
            if after_id:
                try:
                    self.after_cancel(after_id)
                except Exception:
                    pass
        self.follow_action_after_ids = {}
        super().destroy()

    def render_section(self, section_key):
        section_map = {
            "report": (
                "Report",
                "Khu vuc nay se build function report task.",
            ),
            "follow": (
                "Follow",
                "Task Follow UI giu nguyen layout cu, chi doi data flow sang store.",
            ),
            "setup_training": (
                "Setup / Training",
                "Khu vuc nay se build function setup va training task.",
            ),
        }

        title, subtitle = section_map.get(
            section_key,
            ("Task", "Task function will be built here."),
        )

        if section_key in {"follow", "setup_training"}:
            self.current_task_section = section_key
            self.selected_status = self.get_default_task_status()

        if section_key == "follow":
            self.header_card.grid_remove()
        else:
            self.header_card.grid()
            self.title_label.configure(text=title)
            self.subtitle_label.configure(text=subtitle)

        for widget in self.body_card.winfo_children():
            widget.destroy()

        if section_key in {"follow", "setup_training"}:
            self.render_follow_ui()
        else:
            self.render_placeholder(title)

    def render_placeholder(self, title):
        content = ctk.CTkFrame(
            self.body_card,
            fg_color=BG_PANEL_INNER,
            corner_radius=18,
            border_width=1,
            border_color=BORDER_SOFT,
        )
        content.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        content.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            content,
            text=title,
            font=("Segoe UI", 22, "bold"),
            text_color=TEXT_DARK,
        ).pack(anchor="w", padx=22, pady=(22, 8))

        ctk.CTkLabel(
            content,
            text=(
                "Function nay se duoc build tiep theo.\n"
                "Tam thoi minh giu san khung de sau nay gan API, bang SQL va giao dien chi tiet."
            ),
            font=("Segoe UI", 14),
            text_color=TEXT_MUTED,
            justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 18))

    def render_follow_ui(self):
        wrap = ctk.CTkFrame(
            self.body_card,
            fg_color=BG_PANEL_INNER,
            corner_radius=18,
            border_width=1,
            border_color=BORDER_SOFT,
        )
        wrap.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self.follow_wrap = wrap
        wrap.grid_columnconfigure(0, weight=85)
        wrap.grid_columnconfigure(1, weight=15)
        wrap.grid_rowconfigure(1, weight=1)
        wrap.grid_rowconfigure(2, weight=1)
        wrap.bind("<Configure>", self.on_follow_wrap_configure)

        self.follow_top_card = ctk.CTkFrame(
            wrap,
            fg_color="#fbf5ec",
            corner_radius=16,
            border_width=1,
            border_color="#e0c79d",
        )
        self.follow_top_card.grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 12)
        )
        self.follow_top_card.grid_columnconfigure(1, weight=1)
        self.follow_top_card.grid_columnconfigure(7, weight=1)
        self.follow_top_card.grid_columnconfigure(8, weight=1)

        ctk.CTkLabel(
            self.follow_top_card,
            text="Search merchant",
            font=("Segoe UI", 12),
            text_color=TEXT_MUTED,
        ).grid(row=0, column=0, sticky="w", padx=(18, 8), pady=16)

        self.search_entry = ctk.CTkEntry(
            self.follow_top_card,
            width=240,
            height=34,
            placeholder_text="Merchant name...",
            fg_color=INPUT_BG,
            border_color=INPUT_BORDER,
            text_color=TEXT_DARK,
        )
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=16)
        self.search_entry.bind("<KeyRelease>", lambda _e: self.apply_follow_search())

        ctk.CTkButton(
            self.follow_top_card,
            text="Search",
            width=82,
            height=34,
            corner_radius=12,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 12, "bold"),
            command=self.apply_follow_search,
        ).grid(row=0, column=2, sticky="w", padx=(0, 8), pady=16)

        ctk.CTkButton(
            self.follow_top_card,
            text="Clear",
            width=82,
            height=34,
            corner_radius=12,
            fg_color=BTN_DARK,
            hover_color=BTN_DARK_HOVER,
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 12, "bold"),
            command=self.clear_follow_search,
        ).grid(row=0, column=3, sticky="w", padx=(0, 16), pady=16)

        ctk.CTkButton(
            self.follow_top_card,
            text="Create Task",
            width=104,
            height=34,
            corner_radius=12,
            fg_color=BTN_DARK,
            hover_color=BTN_DARK_HOVER,
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 12, "bold"),
            command=self.start_new_task,
        ).grid(row=0, column=4, sticky="w", padx=(0, 16), pady=16)

        self.show_all_button = ctk.CTkButton(
            self.follow_top_card,
            text="Show All: OFF",
            width=110,
            height=34,
            corner_radius=12,
            fg_color=BTN_DARK,
            hover_color=BTN_DARK_HOVER,
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 12, "bold"),
            command=self.toggle_follow_show_all,
        )
        self.show_all_button.grid(row=0, column=5, sticky="w", padx=(0, 10), pady=16)

        self.include_done_switch = ctk.CTkSwitch(
            self.follow_top_card,
            text="Include Done",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_DARK,
            progress_color=BTN_ACTIVE,
            button_color=BTN_DARK,
            button_hover_color=BTN_DARK_HOVER,
            fg_color="#dbc29c",
            command=self.on_follow_include_done_toggle,
        )
        self.include_done_switch.grid(row=0, column=6, sticky="w", padx=(0, 12), pady=16)

        self.follow_scope_label = ctk.CTkLabel(
            self.follow_top_card,
            text="Only active task | Done hidden | Deadline in 3 days",
            font=("Segoe UI", 10, "italic"),
            text_color=TEXT_MUTED,
        )
        self.follow_scope_label.grid(row=0, column=7, columnspan=2, sticky="w", padx=(0, 10), pady=16)

        self.follow_refresh_button = ctk.CTkButton(
            self.follow_top_card,
            text="Refresh",
            width=104,
            height=34,
            corner_radius=12,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 12, "bold"),
            command=self.on_follow_refresh_manual,
        )
        self.follow_refresh_button.grid(row=0, column=9, sticky="e", padx=(0, 18), pady=16)

        self.table_card = ctk.CTkFrame(
            wrap,
            fg_color="#fbf5ec",
            corner_radius=16,
            border_width=1,
            border_color="#e0c79d",
        )
        self.table_card.grid(row=1, column=0, sticky="new", padx=(16, 8), pady=(0, 16))
        self.table_card.grid_columnconfigure(0, weight=1)
        self.table_card.grid_rowconfigure(1, weight=0)

        ctk.CTkLabel(
            self.table_card,
            text="Task Board",
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_DARK,
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 10))

        canvas_wrap = ctk.CTkFrame(
            self.table_card,
            fg_color=BG_CANVAS,
            corner_radius=14,
            border_width=1,
            border_color=BORDER_SOFT,
            height=self.follow_board_height,
        )
        canvas_wrap.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        canvas_wrap.grid_propagate(False)
        canvas_wrap.grid_columnconfigure(0, weight=1)
        canvas_wrap.grid_rowconfigure(0, weight=0)
        canvas_wrap.grid_rowconfigure(1, weight=1)
        canvas_wrap.grid_rowconfigure(2, weight=0)
        self.follow_canvas_wrap = canvas_wrap

        self.follow_header_canvas = tk.Canvas(
            canvas_wrap,
            bg=BG_CANVAS,
            highlightthickness=0,
            bd=0,
            height=58,
        )
        self.follow_header_canvas.grid(row=0, column=0, sticky="ew", padx=(0, 0), pady=(0, 4))

        self.follow_canvas = tk.Canvas(
            canvas_wrap,
            bg=BG_CANVAS,
            highlightthickness=0,
            bd=0,
        )
        self.follow_canvas.grid(row=1, column=0, sticky="nsew")
        self.follow_canvas.bind("<Button-1>", self.on_follow_canvas_click)
        self.follow_canvas.bind("<Configure>", lambda _e: self.redraw_follow_canvas())
        self.follow_canvas.bind("<Enter>", lambda _e: self.set_active_scroll_target("board"))
        self.follow_canvas.bind("<Leave>", lambda _e: self.clear_active_scroll_target("board"))

        self.canvas_scrollbar = ctk.CTkScrollbar(
            canvas_wrap,
            orientation="vertical",
            command=self.follow_canvas.yview,
        )
        self.canvas_scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 6), pady=6)
        self.follow_canvas.configure(yscrollcommand=self.canvas_scrollbar.set)

        self.canvas_scrollbar_x = ctk.CTkScrollbar(
            canvas_wrap,
            orientation="horizontal",
            command=self.on_follow_canvas_xscroll,
        )
        self.canvas_scrollbar_x.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 6))
        self.follow_canvas.configure(xscrollcommand=self.canvas_scrollbar_x.set)

        self.detail_card = ctk.CTkFrame(
            wrap,
            fg_color="#fbf5ec",
            corner_radius=16,
            border_width=1,
            border_color="#e0c79d",
            width=280,
        )
        self.detail_card.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))
        self.detail_card.grid_columnconfigure(0, weight=1)
        self.detail_card.grid_rowconfigure(0, weight=1)

        self.detail_canvas = tk.Canvas(
            self.detail_card,
            bg="#fbf5ec",
            highlightthickness=0,
            bd=0,
        )
        self.detail_canvas.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        self.detail_canvas.bind("<Enter>", lambda _e: self.set_active_scroll_target("detail"))
        self.detail_canvas.bind("<Leave>", lambda _e: self.clear_active_scroll_target("detail"))
        self.detail_canvas.bind("<Configure>", self.on_detail_canvas_configure)

        self.detail_scrollbar = ctk.CTkScrollbar(
            self.detail_card,
            orientation="vertical",
            command=self.detail_canvas.yview,
        )
        self.detail_scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
        self.detail_canvas.configure(yscrollcommand=self.detail_scrollbar.set)

        self.detail_form = ctk.CTkFrame(self.detail_canvas, fg_color="#fbf5ec")
        self.detail_form.grid_columnconfigure(0, weight=1)
        self.detail_canvas_window = self.detail_canvas.create_window(
            0,
            0,
            window=self.detail_form,
            anchor="nw",
        )
        self.detail_form.bind("<Configure>", self.on_detail_form_configure)

        self.bind_follow_mousewheel()
        if self.is_setup_training_section():
            self.build_setup_training_detail_form()
        else:
            self.build_follow_detail_form()
        self.update_follow_filter_controls()
        self.load_follow_bootstrap()
        self.after(60, self.refresh_follow_layout)

    def build_follow_detail_form(self):
        ctk.CTkLabel(
            self.detail_form,
            text=self.get_task_detail_title(),
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_DARK,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 10))

        self.detail_hint = ctk.CTkLabel(
            self.detail_form,
            text=self.get_default_detail_hint(),
            font=("Segoe UI", 12),
            text_color=TEXT_MUTED,
            justify="left",
        )
        self.detail_hint.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

        self.merchant_name_entry = self.create_labeled_entry(2, "Merchant Name:", "SAPPHIRE NAILS 45805")
        self.phone_entry = self.create_labeled_entry(3, "Phone:", "(012) 345-6789")
        self.phone_entry.bind("<KeyRelease>", self.on_phone_input)
        self.problem_entry = self.create_labeled_entry(4, "Problem:", "Setup + 1st training")
        self.handoff_from_entry = self.create_labeled_entry(
            5, "Task created by:", "Current Display Name", state="disabled"
        )

        # Order requested:
        # Problem -> Nguoi ban giao -> Ngay/Gio hen -> Nguoi nhan ban giao -> Status -> Note -> actions
        deadline_wrap = ctk.CTkFrame(self.detail_form, fg_color="transparent")
        deadline_wrap.grid(row=6, column=0, sticky="ew", padx=18, pady=(2, 10))

        ctk.CTkLabel(
            deadline_wrap,
            text="Ngay gio hen",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_DARK,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.deadline_picker_button = ctk.CTkButton(
            deadline_wrap,
            text="Choose Date & Time",
            width=220,
            height=38,
            corner_radius=12,
            fg_color=INPUT_BG,
            hover_color="#f6ead7",
            border_width=1,
            border_color=INPUT_BORDER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
            command=self.toggle_deadline_popup,
        )
        self.deadline_picker_button.grid(row=1, column=0, sticky="w")

        self.deadline_value_hint = ctk.CTkLabel(
            deadline_wrap,
            text="Chua chon ngay gio hen.",
            font=("Segoe UI", 10),
            text_color=TEXT_MUTED,
        )
        self.deadline_value_hint.grid(row=1, column=1, sticky="w", padx=(12, 0))

        self.create_section_label(8, "Assign to")
        self.handoff_button_wrap = ctk.CTkFrame(self.detail_form, fg_color="transparent")
        self.handoff_button_wrap.grid(row=9, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.render_handoff_buttons()

        self.create_section_label(10, "Status")
        status_wrap = ctk.CTkFrame(self.detail_form, fg_color="transparent")
        status_wrap.grid(row=11, column=0, sticky="ew", padx=18, pady=(0, 12))

        for idx, name in enumerate(TASK_STATUSES):
            btn = ctk.CTkButton(
                status_wrap,
                text=name,
                width=142,
                height=34,
                corner_radius=12,
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_LIGHT,
                font=("Segoe UI", 10, "bold"),
                command=lambda value=name: self.select_status(value),
            )
            btn.grid(row=idx // 2, column=idx % 2, sticky="w", padx=(0, 8), pady=4)
            self.status_buttons[name] = btn

        self.create_section_label(12, "Note")
        self.note_box = ctk.CTkTextbox(
            self.detail_form,
            height=110,
            fg_color=INPUT_BG,
            border_color=INPUT_BORDER,
            border_width=1,
            text_color=TEXT_DARK,
            corner_radius=12,
        )
        self.note_box.grid(row=13, column=0, sticky="ew", padx=18, pady=(0, 12))

        action_row = ctk.CTkFrame(self.detail_form, fg_color="transparent")
        action_row.grid(row=14, column=0, sticky="ew", padx=18, pady=(0, 14))

        self.follow_save_button = ctk.CTkButton(
            action_row,
            text="Save",
            width=110,
            height=40,
            corner_radius=12,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 13, "bold"),
            command=self.on_follow_save,
        )
        self.follow_save_button.pack(side="left", padx=(0, 8))

        self.follow_update_button = ctk.CTkButton(
            action_row,
            text="Update",
            width=110,
            height=40,
            corner_radius=12,
            fg_color=BTN_DARK,
            hover_color=BTN_DARK_HOVER,
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 13, "bold"),
            command=self.on_follow_update,
        )
        self.follow_update_button.pack(side="left")

        self.follow_start_training_button = ctk.CTkButton(
            action_row,
            text="Start 1st Setup & Training",
            width=196,
            height=40,
            corner_radius=12,
            fg_color="#0f766e",
            hover_color="#115e59",
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 12, "bold"),
            command=self.open_setup_training_from_follow,
        )
        self.follow_start_training_button.pack(side="left", padx=(8, 0))
        self.refresh_follow_action_button_states()

        self.create_section_label(15, "History / Log")
        self.history_box = ctk.CTkScrollableFrame(
            self.detail_form,
            height=180,
            fg_color="#fff7ed",
            border_width=1,
            border_color=INPUT_BORDER,
            corner_radius=12,
        )
        self.history_box.grid(row=16, column=0, sticky="ew", padx=18, pady=(0, 18))

        self.selected_status = self.get_default_task_status()
        self.select_status(self.selected_status)
        self.select_handoff(self.selected_handoff_to)
        self.handoff_from_entry.configure(state="normal")
        self.set_entry_value(self.handoff_from_entry, self.current_display_name)
        self.handoff_from_entry.configure(state="disabled")
        self.update_deadline_button_text()
        self.update_follow_form_mode()

    def build_setup_training_detail_form(self):
        ctk.CTkLabel(
            self.detail_form,
            text=self.get_task_detail_title(),
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_DARK,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 10))

        self.detail_hint = ctk.CTkLabel(
            self.detail_form,
            text=self.get_default_detail_hint(),
            font=("Segoe UI", 12),
            text_color=TEXT_MUTED,
            justify="left",
        )
        self.detail_hint.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

        info_card = ctk.CTkFrame(
            self.detail_form,
            fg_color="#fff8ef",
            corner_radius=12,
            border_width=1,
            border_color="#e2c89f",
        )
        info_card.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        info_card.grid_columnconfigure(0, weight=1)

        # Row 1: Tên tiệm + Zip code cùng hàng
        row1 = ctk.CTkFrame(info_card, fg_color="transparent")
        row1.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
        row1.grid_columnconfigure(0, weight=1)
        self.training_merchant_label = ctk.CTkLabel(
            row1,
            text="-",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT_DARK,
            anchor="w",
            justify="left",
        )
        self.training_merchant_label.grid(row=0, column=0, sticky="w")

        # Row 2: Ngày hẹn
        row2 = ctk.CTkFrame(info_card, fg_color="transparent")
        row2.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 2))
        row2.grid_columnconfigure(0, weight=1)
        self.training_date_label = ctk.CTkLabel(
            row2,
            text="-",
            font=("Segoe UI", 12),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        self.training_date_label.grid(row=0, column=0, sticky="w")

        # Row 3: Status badge
        row3 = ctk.CTkFrame(info_card, fg_color="transparent")
        row3.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
        self.training_stage_badge = ctk.CTkLabel(
            row3,
            text="1st Setup & Training",
            font=("Segoe UI", 11, "bold"),
            text_color="#ffffff",
            fg_color="#9333ea",
            corner_radius=8,
            width=160,
            height=26,
        )
        self.training_stage_badge.pack(side="left", ipadx=4)

        self.create_section_label(3, "Assign to")
        self.handoff_button_wrap = ctk.CTkFrame(self.detail_form, fg_color="transparent")
        self.handoff_button_wrap.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.render_handoff_buttons()

        self.create_section_label(5, "Training Summary Note")
        self.note_box = ctk.CTkTextbox(
            self.detail_form,
            height=230,
            fg_color=INPUT_BG,
            border_color=INPUT_BORDER,
            border_width=1,
            text_color=TEXT_DARK,
            corner_radius=12,
        )
        self.note_box.grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 12))

        self.create_section_label(7, "Checklist")
        self.training_sections_wrap = ctk.CTkFrame(
            self.detail_form,
            fg_color=TRAINING_CANVAS_BG,
            corner_radius=12,
            border_width=1,
            border_color="#e1c393",
            height=430,
        )
        self.training_sections_wrap.grid(row=8, column=0, sticky="nsew", padx=18, pady=(0, 12))
        self.training_sections_wrap.grid_propagate(False)
        self.training_sections_wrap.grid_columnconfigure(0, weight=1)
        self.training_sections_wrap.grid_rowconfigure(0, weight=1)

        self.training_canvas = tk.Canvas(
            self.training_sections_wrap,
            bg=TRAINING_CANVAS_BG,
            highlightthickness=0,
            bd=0,
        )
        self.training_canvas.grid(row=0, column=0, sticky="nsew")
        self.training_canvas.bind("<Configure>", self.on_training_canvas_configure)
        self.training_canvas.bind("<Enter>", lambda _e: self.set_active_scroll_target("training_canvas"))
        self.training_canvas.bind("<Leave>", lambda _e: self.clear_active_scroll_target("training_canvas"))

        self.training_canvas_scrollbar = ctk.CTkScrollbar(
            self.training_sections_wrap,
            orientation="vertical",
            command=self.on_training_canvas_yview,
        )
        self.training_canvas_scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=6)
        self.training_canvas.configure(yscrollcommand=self.training_canvas_scrollbar.set)

        action_row = ctk.CTkFrame(self.detail_form, fg_color="transparent")
        action_row.grid(row=9, column=0, sticky="ew", padx=18, pady=(0, 14))

        self.follow_update_button = ctk.CTkButton(
            action_row,
            text="Save Training",
            width=132,
            height=40,
            corner_radius=12,
            fg_color=BTN_DARK,
            hover_color=BTN_DARK_HOVER,
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 13, "bold"),
            command=self.on_follow_update,
        )
        self.follow_update_button.pack(side="left", padx=(0, 8))

        self.follow_complete_training_button = ctk.CTkButton(
            action_row,
            text="Complete 1st Training",
            width=182,
            height=40,
            corner_radius=12,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 13, "bold"),
            command=self.on_complete_first_training,
        )
        self.follow_complete_training_button.pack(side="left")

        self.create_section_label(10, "History / Log")
        self.history_box = ctk.CTkScrollableFrame(
            self.detail_form,
            height=180,
            fg_color="#fff7ed",
            border_width=1,
            border_color=INPUT_BORDER,
            corner_radius=12,
        )
        self.history_box.grid(row=11, column=0, sticky="ew", padx=18, pady=(0, 18))

        self.update_training_info_card({})
        self.render_setup_training_sections([])
        self.set_selected_handoffs(["Tech Team"])
        self.update_follow_form_mode()

    def create_info_value(self, parent, row, column, label_text):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=column, sticky="ew", padx=12, pady=10)
        wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            wrap,
            text=label_text,
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT_DARK,
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        value_label = ctk.CTkLabel(
            wrap,
            text="-",
            font=("Segoe UI", 11),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        value_label.grid(row=1, column=0, sticky="ew")
        return value_label

    def build_deadline_time_slots(self):
        slots = []
        for hour in range(20, 24):
            for minute in (0, 30):
                slots.append(datetime(2000, 1, 1, hour, minute).strftime("%I:%M %p"))
        for hour in range(0, 11):
            for minute in (0, 30):
                slots.append(datetime(2000, 1, 1, hour, minute).strftime("%I:%M %p"))
        slots.append(datetime(2000, 1, 1, 11, 0).strftime("%I:%M %p"))
        return slots

    def create_labeled_entry(self, row, label_text, placeholder, width=None, state="normal"):
        wrap = ctk.CTkFrame(self.detail_form, fg_color="transparent")
        wrap.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        wrap.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            wrap,
            text=label_text,
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_DARK,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        entry = ctk.CTkEntry(
            wrap,
            height=38,
            width=width if width is not None else 360,
            placeholder_text=placeholder,
            fg_color=INPUT_BG,
            border_color=INPUT_BORDER,
            text_color=TEXT_DARK,
            state=state,
        )
        entry.grid(row=1, column=0, sticky="ew")
        return entry

    def create_section_label(self, row, text):
        ctk.CTkLabel(
            self.detail_form,
            text=text,
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_DARK,
        ).grid(row=row, column=0, sticky="w", padx=18, pady=(2, 6))

    def get_training_stage_key(self, task=None):
        current_task = task or self.active_task or {}
        status_value = str(current_task.get("status", "")).strip().upper()
        if status_value == "2ND TRAINING":
            return "second"
        return "first"

    def get_training_template_sections(self, stage_key=None):
        normalized_stage = (stage_key or self.get_training_stage_key()).strip().lower()
        if normalized_stage == "second":
            return FIRST_TRAINING_TEMPLATE + SECOND_TRAINING_TEMPLATE
        return FIRST_TRAINING_TEMPLATE

    def merge_training_form_with_template(self, saved_sections, stage_key=None):
        templates = self.get_training_template_sections(stage_key)
        saved_map = {}
        for section in saved_sections or []:
            section_key = str((section or {}).get("section_key", "")).strip()
            if section_key:
                saved_map[section_key] = section or {}

        merged_sections = []
        for template in templates:
            saved_section = saved_map.get(template["section_key"], {})
            saved_rows = saved_section.get("rows") or []
            saved_row_map = {
                (
                    str((row or {}).get("step", "")).strip(),
                    str((row or {}).get("label", "")).strip(),
                ): row or {}
                for row in saved_rows
            }
            merged_rows = []
            for template_row in template.get("rows", []):
                step_key = str(template_row.get("step", "")).strip()
                label_key = str(template_row.get("label", "")).strip()
                saved_row = saved_row_map.get((step_key, label_key), {})
                merged_rows.append(
                    {
                        "kind": str(template_row.get("kind", "normal")).strip() or "normal",
                        "step": step_key,
                        "label": label_key,
                        "result": str(saved_row.get("result", "")).strip(),
                        "note": str(saved_row.get("note", "")).strip() or str(template_row.get("default_note", "")).strip(),
                    }
                )
            merged_sections.append(
                {
                    "section_key": template["section_key"],
                    "title": template["title"],
                    "subtitle": template.get("subtitle", ""),
                    "rows": merged_rows,
                }
            )
        return merged_sections

    def update_training_info_card(self, task):
        if not self.is_setup_training_section():
            return

        current_task = task or {}

        # Row 1: Tên tiệm + Zip code (đứng chung)
        merchant_label = str(current_task.get("merchant_name", "")).strip() or str(current_task.get("merchant_raw", "")).strip()
        zip_code = str(current_task.get("zip_code", "")).strip()
        if zip_code:
            merchant_label = f"{merchant_label}  {zip_code}".strip()
        if hasattr(self, "training_merchant_label"):
            self.training_merchant_label.configure(text=merchant_label or "-")

        # Row 2: Ngày hẹn (deadline_date từ task)
        deadline_date = str(current_task.get("deadline_date", "")).strip()
        deadline_time = str(current_task.get("deadline_time", "")).strip()
        deadline_period = str(current_task.get("deadline_period", "")).strip()
        if deadline_date and deadline_time and deadline_period:
            date_label = f"Ngay hen: {deadline_date}  {deadline_time} {deadline_period}"
        elif deadline_date:
            date_label = f"Ngay hen: {deadline_date}"
        else:
            date_label = "Ngay hen: -"
        if hasattr(self, "training_date_label"):
            self.training_date_label.configure(text=date_label)

        # Row 3: Status badge (màu theo status)
        is_second = self.get_training_stage_key(current_task) == "second"
        stage_text = "2nd Training" if is_second else "1st Setup & Training"
        stage_color = "#0ea5a3" if is_second else "#9333ea"
        if hasattr(self, "training_stage_badge"):
            self.training_stage_badge.configure(text=stage_text, fg_color=stage_color)

    def render_setup_training_sections(self, saved_sections):
        if not hasattr(self, "training_canvas") or self.training_canvas is None:
            return

        self.training_result_vars = {}
        self.training_note_entries = {}
        self.training_note_values = {}
        self.training_canvas_window_map = {}
        sections = self.merge_training_form_with_template(saved_sections, self.get_training_stage_key())
        self.training_canvas_flat_rows = []
        for section in sections:
            self.training_canvas_flat_rows.append(
                {
                    "kind": "banner",
                    "section_key": section["section_key"],
                    "title": section["title"],
                    "subtitle": str(section.get("subtitle", "")).strip(),
                }
            )
            self.training_canvas_flat_rows.append(
                {
                    "kind": "columns",
                    "section_key": section["section_key"],
                }
            )
            for row in section.get("rows", []):
                self.training_canvas_flat_rows.append(
                    {
                        "kind": row.get("kind", "normal"),
                        "section_key": section["section_key"],
                        "step": row["step"],
                        "label": row["label"],
                        "result": row.get("result", ""),
                        "note": row.get("note", ""),
                    }
                )
        self.redraw_training_canvas()
        self.schedule_training_canvas_refresh()

    def estimate_training_row_height(self, row):
        kind = row.get("kind")
        if kind == "banner":
            subtitle = str(row.get("subtitle", "")).strip()
            return 42 + (22 * max(0, subtitle.count("\n") + (1 if subtitle else 0)))
        if kind == "columns":
            return 30
        if kind == "group":
            return 34
        label = str(row.get("label", "")).strip()
        line_count = max(1, label.count("\n") + 1)
        return max(34, 12 + (line_count * 18))

    def redraw_training_canvas(self):
        canvas = getattr(self, "training_canvas", None)
        if canvas is None:
            return
        for row_key, note_entry in list(self.training_note_entries.items()):
            try:
                self.training_note_values[row_key] = note_entry.get().strip()
            except Exception:
                pass
        canvas.delete("all")
        self.training_canvas_row_layout = []

        canvas_width = max(720, canvas.winfo_width())
        x = 0
        y = 0
        step_w = 44
        result_w = 92
        note_w = max(210, int(canvas_width * 0.33))
        list_w = max(280, canvas_width - step_w - result_w - note_w - 4)
        col_positions = {
            "step": x,
            "list": x + step_w,
            "result": x + step_w + list_w,
            "note": x + step_w + list_w + result_w,
            "right": x + step_w + list_w + result_w + note_w,
        }

        for row in self.training_canvas_flat_rows:
            height = self.estimate_training_row_height(row)
            row["height"] = height
            row["y"] = y
            self.training_canvas_row_layout.append(row)

            kind = row.get("kind")
            if kind == "banner":
                canvas.create_rectangle(
                    col_positions["step"],
                    y,
                    col_positions["right"],
                    y + height,
                    fill=TRAINING_BANNER_BG,
                    outline="#000000",
                )
                canvas.create_text(
                    (col_positions["step"] + col_positions["right"]) / 2,
                    y + 14,
                    text=row.get("title", ""),
                    fill="#1d1d1d",
                    font=("Segoe UI", 13, "bold"),
                    anchor="n",
                )
                subtitle = str(row.get("subtitle", "")).strip()
                if subtitle:
                    canvas.create_text(
                        (col_positions["step"] + col_positions["right"]) / 2,
                        y + 34,
                        text=subtitle,
                        fill="#b91c1c" if row.get("section_key") != "second_training" else "#1d1d1d",
                        font=("Segoe UI", 10, "bold"),
                        anchor="n",
                        justify="center",
                        width=col_positions["right"] - 24,
                    )
            elif kind == "columns":
                for start_x, end_x, text in [
                    (col_positions["step"], col_positions["list"], "STEP"),
                    (col_positions["list"], col_positions["result"], "LIST"),
                    (col_positions["result"], col_positions["note"], "Result"),
                    (col_positions["note"], col_positions["right"], "NOTE"),
                ]:
                    canvas.create_rectangle(start_x, y, end_x, y + height, fill=TRAINING_SUBHEADER_BG, outline="#000000")
                    canvas.create_text(
                        (start_x + end_x) / 2,
                        y + (height / 2),
                        text=text,
                        fill="#1d1d1d",
                        font=("Segoe UI", 10, "bold"),
                    )
            elif kind == "group":
                canvas.create_rectangle(
                    col_positions["step"],
                    y,
                    col_positions["right"],
                    y + height,
                    fill=TRAINING_GROUP_BG,
                    outline="#000000",
                )
                canvas.create_text(
                    (col_positions["step"] + col_positions["right"]) / 2,
                    y + (height / 2),
                    text=row.get("label", ""),
                    fill="#1d1d1d",
                    font=("Segoe UI", 11, "bold"),
                )
            else:
                for start_x, end_x in [
                    (col_positions["step"], col_positions["list"]),
                    (col_positions["list"], col_positions["result"]),
                    (col_positions["result"], col_positions["note"]),
                    (col_positions["note"], col_positions["right"]),
                ]:
                    canvas.create_rectangle(start_x, y, end_x, y + height, fill="#ffffff", outline="#000000")
                canvas.create_text(
                    (col_positions["step"] + col_positions["list"]) / 2,
                    y + 8,
                    text=row.get("step", ""),
                    fill="#1d1d1d",
                    font=("Segoe UI", 10, "bold"),
                    anchor="n",
                )
                canvas.create_text(
                    col_positions["list"] + 8,
                    y + 6,
                    text=row.get("label", ""),
                    fill="#1d1d1d",
                    font=("Segoe UI", 10),
                    anchor="nw",
                    justify="left",
                    width=list_w - 16,
                )
            y += height

        self.training_canvas_content_height = y + 4
        canvas.configure(scrollregion=(0, 0, col_positions["right"], self.training_canvas_content_height))

    def schedule_training_canvas_refresh(self):
        if self.training_canvas_after_id:
            try:
                self.after_cancel(self.training_canvas_after_id)
            except Exception:
                pass
        self.training_canvas_after_id = self.after(16, self.refresh_visible_training_widgets)

    def on_training_canvas_configure(self, _event=None):
        self.redraw_training_canvas()
        self.schedule_training_canvas_refresh()

    def on_training_canvas_yview(self, *args):
        if self.training_canvas is not None:
            self.training_canvas.yview(*args)
            self.schedule_training_canvas_refresh()

    def refresh_visible_training_widgets(self):
        self.training_canvas_after_id = None
        canvas = getattr(self, "training_canvas", None)
        if canvas is None:
            return

        top_y = canvas.canvasy(0)
        bottom_y = top_y + max(1, canvas.winfo_height())
        visible_keys = set()

        canvas_width = max(720, canvas.winfo_width())
        step_w = 44
        result_w = 92
        note_w = max(210, int(canvas_width * 0.33))
        list_w = max(280, canvas_width - step_w - result_w - note_w - 4)
        result_x = step_w + list_w + (result_w / 2)
        note_x = step_w + list_w + result_w + 8

        for row in self.training_canvas_row_layout:
            if row.get("kind") != "normal":
                continue
            row_top = row.get("y", 0)
            row_bottom = row_top + row.get("height", 0)
            row_key = (row.get("section_key", ""), row.get("step", ""), row.get("label", ""))
            if row_bottom < top_y - 80 or row_top > bottom_y + 80:
                continue

            visible_keys.add(row_key)
            result_var = self.training_result_vars.get(row_key)
            if result_var is None:
                result_var = tk.StringVar(value=str(row.get("result", "")).strip())
                self.training_result_vars[row_key] = result_var

            result_item = self.training_canvas_window_map.get((row_key, "result"))
            if result_item is None:
                current_val = str(result_var.get()).strip().upper()

                def make_toggle(rv):
                    def _toggle():
                        cur = str(rv.get()).strip().upper()
                        if cur == "":
                            rv.set("DONE")
                        elif cur == "DONE":
                            rv.set("X")
                        else:
                            rv.set("")
                        # update button appearance
                        btn_widget = _toggle._btn
                        new_val = str(rv.get()).strip().upper()
                        if new_val == "DONE":
                            btn_widget.configure(fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff", text="DONE")
                        elif new_val == "X":
                            btn_widget.configure(fg_color="#f59e0b", hover_color="#d97706", text_color="#ffffff", text="X")
                        else:
                            btn_widget.configure(fg_color=INPUT_BG, hover_color="#f0e8d8", text_color=TEXT_MUTED, text="—")
                    return _toggle

                toggle_fn = make_toggle(result_var)
                if current_val == "DONE":
                    btn_fg, btn_hover, btn_tc, btn_txt = "#ef4444", "#dc2626", "#ffffff", "DONE"
                elif current_val == "X":
                    btn_fg, btn_hover, btn_tc, btn_txt = "#f59e0b", "#d97706", "#ffffff", "X"
                else:
                    btn_fg, btn_hover, btn_tc, btn_txt = INPUT_BG, "#f0e8d8", TEXT_MUTED, "—"

                btn = ctk.CTkButton(
                    canvas,
                    text=btn_txt,
                    width=78,
                    height=26,
                    corner_radius=8,
                    fg_color=btn_fg,
                    hover_color=btn_hover,
                    text_color=btn_tc,
                    font=("Segoe UI", 10, "bold"),
                    command=toggle_fn,
                )
                toggle_fn._btn = btn
                window_id = canvas.create_window(result_x, row_top + (row.get("height", 0) / 2), window=btn, width=78, height=26)
                self.training_canvas_window_map[(row_key, "result")] = {"widget": btn, "window_id": window_id}
            else:
                canvas.coords(result_item["window_id"], result_x, row_top + (row.get("height", 0) / 2))

            note_item = self.training_canvas_window_map.get((row_key, "note"))
            if note_item is None:
                entry = ctk.CTkEntry(
                    canvas,
                    height=26,
                    fg_color=INPUT_BG,
                    border_color=INPUT_BORDER,
                    text_color=TEXT_DARK,
                    placeholder_text="",
                )
                existing_note = str(self.training_note_values.get(row_key, row.get("note", ""))).strip()
                if existing_note:
                    entry.insert(0, existing_note)
                window_id = canvas.create_window(
                    note_x,
                    row_top + (row.get("height", 0) / 2),
                    window=entry,
                    anchor="w",
                    width=note_w - 16,
                    height=26,
                )
                self.training_note_entries[row_key] = entry
                self.training_canvas_window_map[(row_key, "note")] = {"widget": entry, "window_id": window_id}
            else:
                canvas.coords(note_item["window_id"], note_x, row_top + (row.get("height", 0) / 2))
                canvas.itemconfigure(note_item["window_id"], width=note_w - 16)

        for item_key in list(self.training_canvas_window_map.keys()):
            row_key = item_key[0]
            if row_key not in visible_keys:
                item = self.training_canvas_window_map.pop(item_key, None)
                if item:
                    if item_key[1] == "note":
                        try:
                            self.training_note_values[row_key] = item["widget"].get().strip()
                        except Exception:
                            pass
                    try:
                        canvas.delete(item["window_id"])
                    except Exception:
                        pass
                    try:
                        item["widget"].destroy()
                    except Exception:
                        pass
                    if item_key[1] == "note":
                        self.training_note_entries.pop(row_key, None)

    def collect_training_form_sections(self):
        saved_sections = (self.active_task or {}).get("training_form") or []
        sections = self.merge_training_form_with_template(saved_sections, self.get_training_stage_key())
        collected_sections = []
        for section in sections:
            collected_rows = []
            for row in section.get("rows", []):
                row_key = (section["section_key"], row["step"], row["label"])
                result_value = self.training_result_vars.get(row_key).get().strip() if row_key in self.training_result_vars else str(row.get("result", "")).strip()
                note_entry = self.training_note_entries.get(row_key)
                if note_entry is not None:
                    note_value = note_entry.get().strip()
                else:
                    note_value = str(self.training_note_values.get(row_key, "")).strip()
                collected_rows.append(
                    {
                        "kind": row.get("kind", "normal"),
                        "step": row["step"],
                        "label": row["label"],
                        "result": result_value,
                        "note": note_value or str(row.get("note", "")).strip(),
                    }
                )
            collected_sections.append(
                {
                    "section_key": section["section_key"],
                    "title": section["title"],
                    "subtitle": section.get("subtitle", ""),
                    "rows": collected_rows,
                }
            )
        return collected_sections

    def render_handoff_buttons(self):
        if not hasattr(self, "handoff_button_wrap"):
            return

        for widget in self.handoff_button_wrap.winfo_children():
            widget.destroy()

        self.handoff_buttons = {}
        options = self.handoff_options or [{"username": "", "display_name": "Tech Team", "type": "TEAM"}]
        for idx, option in enumerate(options):
            display_name = str(option.get("display_name", "")).strip()
            if not display_name:
                continue

            btn = ctk.CTkButton(
                self.handoff_button_wrap,
                text=display_name,
                width=96,
                height=34,
                corner_radius=12,
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_LIGHT,
                font=("Segoe UI", 11, "bold"),
                command=lambda value=display_name: self.toggle_handoff(value),
            )
            btn.grid(row=idx // 2, column=idx % 2, sticky="w", padx=(0, 8), pady=4)
            self.handoff_buttons[display_name] = btn

        current_targets = list(self.selected_handoff_targets or [])
        if not current_targets and self.handoff_buttons:
            current_targets = [next(iter(self.handoff_buttons))]

        if self.handoff_buttons:
            self.set_selected_handoffs(current_targets)

    def select_status(self, status_name):
        self.selected_status = status_name

        for name, button in self.status_buttons.items():
            if name == status_name:
                meta = STATUS_META.get(name, {"bg": BTN_ACTIVE, "text": TEXT_DARK})
                button.configure(
                    fg_color=meta["bg"],
                    hover_color=meta["bg"],
                    text_color=meta["text"],
                )
            else:
                button.configure(
                    fg_color=BTN_IDLE,
                    hover_color=BTN_IDLE_HOVER,
                    text_color=TEXT_LIGHT,
                )

    def update_follow_form_mode(self):
        is_edit_mode = bool(self.active_task and self.active_task.get("task_id"))

        if self.is_setup_training_section():
            if hasattr(self, "follow_update_button"):
                is_locked = self._follow_action_is_locked("update") or not is_edit_mode
                self.follow_update_button.configure(
                    state="disabled" if is_locked else "normal",
                    fg_color="#b8aba0" if is_locked else BTN_DARK,
                    hover_color="#b8aba0" if is_locked else BTN_DARK_HOVER,
                    text_color="#f4eee7" if is_locked else TEXT_LIGHT,
                )
            if hasattr(self, "follow_complete_training_button"):
                can_complete = (
                    is_edit_mode
                    and str((self.active_task or {}).get("status", "")).strip().upper() == "SET UP & TRAINING"
                    and not self._follow_action_is_locked("update")
                )
                self.follow_complete_training_button.configure(
                    state="normal" if can_complete else "disabled",
                    fg_color=BTN_ACTIVE if can_complete else "#d9c7aa",
                    hover_color=BTN_ACTIVE_HOVER if can_complete else "#d9c7aa",
                    text_color=TEXT_DARK if can_complete else "#8f7a62",
                )
            self.refresh_follow_action_button_states()
            return

        if hasattr(self, "follow_save_button"):
            if is_edit_mode or self._follow_action_is_locked("save"):
                self.follow_save_button.configure(
                    state="disabled",
                    fg_color="#d9c7aa",
                    hover_color="#d9c7aa",
                    text_color="#8f7a62",
                )
            else:
                self.follow_save_button.configure(
                    state="normal",
                    fg_color=BTN_ACTIVE,
                    hover_color=BTN_ACTIVE_HOVER,
                    text_color=TEXT_DARK,
                )

        if hasattr(self, "follow_update_button"):
            if is_edit_mode and not self._follow_action_is_locked("update"):
                self.follow_update_button.configure(
                    state="normal",
                    fg_color=BTN_DARK,
                    hover_color=BTN_DARK_HOVER,
                    text_color=TEXT_LIGHT,
                )
            else:
                self.follow_update_button.configure(
                    state="disabled",
                    fg_color="#b8aba0",
                    hover_color="#b8aba0",
                    text_color="#f4eee7",
                )

        if hasattr(self, "follow_start_training_button"):
            active_status = str((self.active_task or {}).get("status", "")).strip().upper()
            can_start_training = is_edit_mode and active_status == "SET UP & TRAINING"
            self.follow_start_training_button.configure(
                state="normal" if can_start_training else "disabled",
                fg_color="#0f766e" if can_start_training else "#9fb8b3",
                hover_color="#115e59" if can_start_training else "#9fb8b3",
                text_color=TEXT_LIGHT if can_start_training else "#edf3f1",
            )

        self.refresh_follow_action_button_states()

    def _follow_action_is_locked(self, action_key):
        if action_key in self.follow_action_inflight:
            return True
        return time.monotonic() < self.follow_action_ready_at.get(action_key, 0.0)

    def refresh_follow_action_button_states(self):
        if hasattr(self, "follow_refresh_button") and self.follow_refresh_button is not None:
            is_locked = self._follow_action_is_locked("refresh")
            self.follow_refresh_button.configure(
                state="disabled" if is_locked else "normal",
                fg_color="#dac6a5" if is_locked else BTN_ACTIVE,
                hover_color="#dac6a5" if is_locked else BTN_ACTIVE_HOVER,
                text_color="#8f7a62" if is_locked else TEXT_DARK,
            )

        if hasattr(self, "follow_save_button"):
            # Save / Update colors are handled together in update_follow_form_mode.
            pass

    def _schedule_follow_action_state_refresh(self, action_key):
        existing_after_id = self.follow_action_after_ids.get(action_key)
        if existing_after_id:
            try:
                self.after_cancel(existing_after_id)
            except Exception:
                pass

        if action_key in self.follow_action_inflight:
            self.follow_action_after_ids[action_key] = None
            return

        remaining_ms = int(max(0.0, self.follow_action_ready_at.get(action_key, 0.0) - time.monotonic()) * 1000)
        if remaining_ms <= 0:
            self.follow_action_after_ids[action_key] = None
            self.update_follow_form_mode()
            return

        self.follow_action_after_ids[action_key] = self.after(
            remaining_ms,
            self.update_follow_form_mode,
        )

    def _start_follow_action(self, action_key):
        if self._follow_action_is_locked(action_key):
            return False

        self.follow_action_inflight.add(action_key)
        self.follow_action_ready_at[action_key] = time.monotonic() + (self.follow_action_cooldown_ms / 1000.0)
        self._schedule_follow_action_state_refresh(action_key)
        self.update_follow_form_mode()
        return True

    def _finish_follow_action(self, action_key):
        self.follow_action_inflight.discard(action_key)
        self._schedule_follow_action_state_refresh(action_key)
        self.update_follow_form_mode()

    def set_selected_handoffs(self, handoff_names):
        normalized_names = []
        for name in handoff_names or []:
            target_name = str(name or "").strip()
            if target_name and target_name not in normalized_names:
                normalized_names.append(target_name)

        if "Tech Team" in normalized_names and len(normalized_names) > 1:
            normalized_names = [name for name in normalized_names if name != "Tech Team"]

        if not normalized_names and "Tech Team" in self.handoff_buttons:
            normalized_names = ["Tech Team"]
        elif not normalized_names and self.handoff_buttons:
            normalized_names = [next(iter(self.handoff_buttons))]

        self.selected_handoff_targets = normalized_names
        self.selected_handoff_to = ", ".join(normalized_names) if normalized_names else "Tech Team"

        for name, button in self.handoff_buttons.items():
            if name in self.selected_handoff_targets:
                button.configure(
                    fg_color=BTN_ACTIVE,
                    hover_color=BTN_ACTIVE_HOVER,
                    text_color=TEXT_DARK,
                )
            else:
                button.configure(
                    fg_color=BTN_IDLE,
                    hover_color=BTN_IDLE_HOVER,
                    text_color=TEXT_LIGHT,
                )

    def toggle_handoff(self, handoff_name):
        target_name = str(handoff_name or "").strip()
        if not target_name or target_name not in self.handoff_buttons:
            return

        current_targets = list(self.selected_handoff_targets or [])
        if target_name == "Tech Team":
            self.set_selected_handoffs(["Tech Team"])
            return

        current_targets = [name for name in current_targets if name != "Tech Team"]
        if target_name in current_targets:
            current_targets = [name for name in current_targets if name != target_name]
        else:
            current_targets.append(target_name)

        if not current_targets:
            current_targets = ["Tech Team"]

        self.set_selected_handoffs(current_targets)

    def select_handoff(self, handoff_name):
        self.set_selected_handoffs([handoff_name])

    def on_phone_input(self, _event=None):
        digits = re.sub(r"\D", "", self.phone_entry.get())[:10]
        formatted = self.format_phone(digits)
        self.phone_entry.delete(0, "end")
        self.phone_entry.insert(0, formatted)

    def toggle_deadline_popup(self):
        if self.deadline_popup_frame is not None and self.deadline_popup_frame.winfo_exists():
            self.close_deadline_popup()
            return
        self.open_deadline_popup()

    def open_deadline_popup(self):
        if not hasattr(self, "deadline_picker_button"):
            return

        if self.deadline_popup_frame is not None and self.deadline_popup_frame.winfo_exists():
            self.close_deadline_popup()

        selected_date = self.confirmed_deadline_date
        if selected_date and self.is_valid_deadline_date(selected_date):
            self.pending_deadline_date = selected_date
            self.deadline_popup_month = datetime.strptime(selected_date, "%d-%m-%Y").replace(day=1)
        else:
            self.pending_deadline_date = ""
            self.deadline_popup_month = datetime.now().replace(day=1)

        self.pending_deadline_time = self.confirmed_deadline_time or (self.deadline_time_slots[0] if self.deadline_time_slots else "")

        popup = ctk.CTkFrame(
            self.detail_form,
            fg_color="#fff7ed",
            corner_radius=14,
            border_width=1,
            border_color=INPUT_BORDER,
            width=292,
            height=344,
        )
        popup.place(in_=self.deadline_picker_button, relx=0, rely=1.0, x=0, y=8, anchor="nw")
        popup.lift()
        popup.grid_columnconfigure(1, weight=1)
        self.deadline_popup_frame = popup

        prev_button = ctk.CTkButton(
            popup,
            text="<",
            width=34,
            height=30,
            corner_radius=10,
            fg_color=BTN_DARK,
            hover_color=BTN_DARK_HOVER,
            text_color=TEXT_LIGHT,
            command=lambda: self.shift_deadline_popup_month(-1),
        )
        prev_button.grid(row=0, column=0, sticky="w", padx=(12, 6), pady=(12, 8))

        self.deadline_month_label = ctk.CTkLabel(
            popup,
            text="",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_DARK,
        )
        self.deadline_month_label.grid(row=0, column=1, sticky="ew", pady=(12, 8))

        next_button = ctk.CTkButton(
            popup,
            text=">",
            width=34,
            height=30,
            corner_radius=10,
            fg_color=BTN_DARK,
            hover_color=BTN_DARK_HOVER,
            text_color=TEXT_LIGHT,
            command=lambda: self.shift_deadline_popup_month(1),
        )
        next_button.grid(row=0, column=2, sticky="e", padx=(6, 12), pady=(12, 8))

        self.deadline_calendar_canvas = tk.Canvas(
            popup,
            width=266,
            height=198,
            bg="#fff7ed",
            highlightthickness=0,
            bd=0,
        )
        self.deadline_calendar_canvas.grid(row=1, column=0, columnspan=3, padx=12)
        self.deadline_calendar_canvas.bind("<Button-1>", self.on_deadline_calendar_click)

        ctk.CTkLabel(
            popup,
            text="Time",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT_DARK,
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=12, pady=(4, 6))

        self.deadline_popup_time_combo = ctk.CTkComboBox(
            popup,
            values=self.deadline_time_slots,
            height=36,
            fg_color=INPUT_BG,
            border_color=INPUT_BORDER,
            button_color=BTN_ACTIVE,
            button_hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            dropdown_fg_color=INPUT_BG,
            dropdown_text_color=TEXT_DARK,
        )
        self.deadline_popup_time_combo.grid(row=3, column=0, columnspan=3, sticky="ew", padx=12)
        if self.pending_deadline_time:
            self.deadline_popup_time_combo.set(self.pending_deadline_time)

        action_row = ctk.CTkFrame(popup, fg_color="transparent")
        action_row.grid(row=4, column=0, columnspan=3, sticky="ew", padx=12, pady=(12, 12))

        ctk.CTkButton(
            action_row,
            text="Cancel",
            width=108,
            height=34,
            corner_radius=10,
            fg_color=BTN_DARK,
            hover_color=BTN_DARK_HOVER,
            text_color=TEXT_LIGHT,
            command=self.close_deadline_popup,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            action_row,
            text="Confirm",
            width=108,
            height=34,
            corner_radius=10,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            command=self.confirm_deadline_popup,
        ).pack(side="left")

        self.redraw_deadline_calendar()

    def close_deadline_popup(self):
        popup = getattr(self, "deadline_popup_frame", None)
        if popup is not None and popup.winfo_exists():
            popup.destroy()
        self.deadline_popup_frame = None
        self.deadline_calendar_canvas = None
        self.deadline_calendar_hits = []

    def shift_deadline_popup_month(self, month_delta):
        current = self.deadline_popup_month
        total_month = (current.year * 12 + current.month - 1) + month_delta
        year = total_month // 12
        month = total_month % 12 + 1
        self.deadline_popup_month = current.replace(year=year, month=month, day=1)
        self.redraw_deadline_calendar()

    def redraw_deadline_calendar(self):
        canvas = getattr(self, "deadline_calendar_canvas", None)
        if canvas is None:
            return

        canvas.delete("all")
        self.deadline_calendar_hits = []

        month_start = self.deadline_popup_month
        self.deadline_month_label.configure(text=month_start.strftime("%B %Y"))
        day_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        cell_w = 36
        cell_h = 28
        start_x = 8
        start_y = 22
        radius = 10

        for idx, label in enumerate(day_headers):
            x = start_x + idx * cell_w + cell_w / 2
            canvas.create_text(x, 10, text=label, fill=TEXT_MUTED, font=("Segoe UI", 9, "bold"))

        month_rows = calendar.monthcalendar(month_start.year, month_start.month)
        today = datetime.now().date()
        selected_date = None
        if self.pending_deadline_date and self.is_valid_deadline_date(self.pending_deadline_date):
            selected_date = datetime.strptime(self.pending_deadline_date, "%d-%m-%Y").date()

        for row_idx, week in enumerate(month_rows):
            for col_idx, day_num in enumerate(week):
                x1 = start_x + col_idx * cell_w
                y1 = start_y + row_idx * cell_h
                x2 = x1 + cell_w - 4
                y2 = y1 + cell_h - 4

                if not day_num:
                    continue

                current_date = month_start.replace(day=day_num).date()
                fill = "#fff7ed"
                outline = "#efd8b4"
                text_color = TEXT_DARK

                if current_date == today:
                    fill = "#fef3c7"
                    outline = "#e6b450"
                if selected_date and current_date == selected_date:
                    fill = BTN_ACTIVE
                    outline = BTN_ACTIVE
                    text_color = TEXT_DARK

                self.draw_round_rect(canvas, x1, y1, x2, y2, radius, fill, outline)
                canvas.create_text(
                    (x1 + x2) / 2,
                    (y1 + y2) / 2,
                    text=str(day_num),
                    fill=text_color,
                    font=("Segoe UI", 10, "bold"),
                )
                self.deadline_calendar_hits.append((x1, y1, x2, y2, current_date.strftime("%d-%m-%Y")))

    def on_deadline_calendar_click(self, event):
        for x1, y1, x2, y2, date_text in self.deadline_calendar_hits:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.pending_deadline_date = date_text
                self.redraw_deadline_calendar()
                return

    def confirm_deadline_popup(self):
        if not self.pending_deadline_date or not self.is_valid_deadline_date(self.pending_deadline_date):
            messagebox.showwarning(self.get_task_module_label(), "Hay chon ngay hen hop le.")
            return

        selected_time = ""
        if hasattr(self, "deadline_popup_time_combo"):
            selected_time = self.deadline_popup_time_combo.get().strip()

        if selected_time not in self.deadline_time_slots:
            messagebox.showwarning(self.get_task_module_label(), "Hay chon gio hen hop le.")
            return

        previous_signature = self.get_confirmed_deadline_signature()
        self.confirmed_deadline_date = self.pending_deadline_date
        self.confirmed_deadline_time = selected_time
        self.update_deadline_button_text()
        self.close_deadline_popup()

        if self.get_confirmed_deadline_signature() != previous_signature:
            self.refresh_handoff_options_from_deadline()

    def get_confirmed_deadline_signature(self):
        return (
            self.confirmed_deadline_date.strip(),
            self.confirmed_deadline_time.strip().upper(),
        )

    def get_confirmed_deadline_parts(self):
        if not self.confirmed_deadline_time:
            return self.confirmed_deadline_date, "", ""
        try:
            parsed_time = datetime.strptime(self.confirmed_deadline_time, "%I:%M %p")
            return (
                self.confirmed_deadline_date,
                parsed_time.strftime("%I:%M"),
                parsed_time.strftime("%p"),
            )
        except ValueError:
            return self.confirmed_deadline_date, "", ""

    def update_deadline_button_text(self):
        if not hasattr(self, "deadline_picker_button"):
            return

        if self.confirmed_deadline_date and self.confirmed_deadline_time:
            label = f"{self.confirmed_deadline_date} | {self.confirmed_deadline_time}"
            self.deadline_picker_button.configure(text=label)
            if hasattr(self, "deadline_value_hint"):
                self.deadline_value_hint.configure(text="Bam de doi ngay gio hen.")
        else:
            self.deadline_picker_button.configure(text="Choose Date & Time")
            if hasattr(self, "deadline_value_hint"):
                self.deadline_value_hint.configure(text="Chua chon ngay gio hen.")

    def refresh_handoff_options_from_deadline(self):
        if not self.current_username:
            return
        deadline_date, deadline_time, deadline_period = self.get_confirmed_deadline_parts()
        if not deadline_date:
            return
        if not self.is_valid_deadline_date(deadline_date):
            return
        if not deadline_time or deadline_period not in {"AM", "PM"}:
            return
        self.store.load_handoff_options(
            self.current_username,
            task_date=deadline_date,
            task_time=deadline_time,
            task_period=deadline_period,
        )

    def format_phone(self, digits):
        if not digits:
            return ""
        if len(digits) <= 3:
            return f"({digits}"
        if len(digits) <= 6:
            return f"({digits[:3]}) {digits[3:]}"
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:10]}"

    def is_valid_deadline_date(self, date_text):
        try:
            datetime.strptime(date_text, "%d-%m-%Y")
            return True
        except ValueError:
            return False

    def load_follow_bootstrap(self):
        self.store.set_view(show_all=self.follow_show_all, include_done=self.follow_include_done)
        self.store.load_handoff_options(self.current_username, task_date="")
        self.refresh_follow_tasks()
        self.poll_follow_store_events()

    def poll_follow_store_events(self):
        for event in self.store.drain_events():
            self.handle_follow_store_event(event)
        self.follow_poll_after_id = self.after(120, self.poll_follow_store_events)

    def handle_follow_store_event(self, event):
        event_type = event.get("type")

        if event_type == "tasks_loaded":
            self._finish_follow_action("refresh")
            self.follow_search_scope = str(event.get("search_scope", "board")).strip() or "board"
            self.apply_follow_search()
            if self.pending_focus_task_id:
                target_task_id = self.pending_focus_task_id
                self.pending_focus_task_id = None
                self.load_task_detail(target_task_id)
            return

        if event_type == "tasks_loading":
            return

        if event_type == "tasks_load_failed":
            self._finish_follow_action("refresh")
            self.follow_tasks = []
            self.filtered_follow_tasks = []
            self.follow_search_scope = "board"
            self.update_follow_scope_hint()
            self.redraw_follow_canvas()
            self.clear_follow_form()
            messagebox.showerror(self.get_task_module_label(), event.get("message", "Khong load duoc task."))
            return

        if event_type == "handoff_options_loaded":
            self.current_display_name = (
                str(event.get("current_display_name", "")).strip()
                or self.current_full_name
                or self.current_username
            )
            self.handoff_options = event.get("options", []) or self.handoff_options
            self.render_handoff_buttons()

            if hasattr(self, "handoff_from_entry") and self.handoff_from_entry is not None:
                self.handoff_from_entry.configure(state="normal")
                self.set_entry_value(self.handoff_from_entry, self.current_display_name)
                self.handoff_from_entry.configure(state="disabled")
            return

        if event_type == "task_detail_loaded":
            item = event.get("item") or {}
            if item:
                self.load_task_into_form(item)
            return

        if event_type == "task_detail_failed":
            messagebox.showerror(self.get_task_module_label(), event.get("message", "Khong load duoc task detail."))
            return

        if event_type in {"task_upserted", "task_removed"}:
            current_task_id = self.active_task.get("task_id") if self.active_task else None
            self.follow_tasks = self.store.get_all()
            self.filtered_follow_tasks = self.store.filter_local(self.search_entry.get().strip())
            self.redraw_follow_canvas()
            if current_task_id:
                current_item = self.store.get_by_id(current_task_id)
                if current_item:
                    self.load_task_into_form(current_item)
            return

        if event_type == "task_save_failed":
            self._finish_follow_action("save")
            self._finish_follow_action("update")
            messagebox.showerror(self.get_task_module_label(), event.get("message", "Khong luu duoc task."))
            self.follow_tasks = self.store.get_all()
            self.filtered_follow_tasks = self.store.filter_local(self.search_entry.get().strip())
            self.redraw_follow_canvas()
            rollback_item = event.get("rollback_item")
            if rollback_item and event.get("action") == "update":
                self.load_task_into_form(rollback_item)
            return

        if event_type == "task_save_succeeded":
            self._finish_follow_action("save")
            self._finish_follow_action("update")
            messagebox.showinfo(self.get_task_module_label(), event.get("message", "Da luu task thanh cong."))

    def get_handoff_option_by_display_name(self, display_name):
        target = str(display_name or "").strip()
        for option in self.handoff_options:
            if str(option.get("display_name", "")).strip() == target:
                return option
        return None

    def refresh_follow_tasks(self, search_text="", keep_selection=False, force=False):
        if not self.current_username:
            self.follow_tasks = []
            self.filtered_follow_tasks = []
            self.follow_search_scope = "board"
            self.update_follow_scope_hint()
            self.redraw_follow_canvas()
            self.clear_follow_form()
            return

        if search_text:
            self.set_entry_value(self.search_entry, search_text)

        self.store.set_view(show_all=self.follow_show_all, include_done=self.follow_include_done)
        self.store.load(self.current_username, force=force, background_if_stale=True)

    def on_follow_refresh_manual(self):
        if not self._start_follow_action("refresh"):
            return
        self.refresh_follow_tasks(force=True)

        self.follow_tasks = self.get_section_filtered_tasks()
        self.filtered_follow_tasks = self.get_section_filtered_tasks(self.search_entry.get().strip())
        self.follow_search_scope = self.store.search_scope
        self.update_follow_scope_hint()
        self.redraw_follow_canvas()

        current_task_id = self.active_task.get("task_id") if self.active_task else None
        if current_task_id:
            current_item = self.store.get_by_id(current_task_id)
            if current_item:
                self.load_task_into_form(current_item)
                return

        if self.filtered_follow_tasks and not self.active_task:
            self.load_task_detail(self.filtered_follow_tasks[0].get("task_id"))

    def load_task_detail(self, task_id):
        if not task_id:
            return

        item = self.store.get_by_id(task_id)
        if item:
            self.load_task_into_form(item)
            if int(task_id) < 0:
                return
        self.store.ensure_detail(task_id, action_by=self.current_username)

    def collect_follow_form_payload(self):
        merchant_raw_text = self.merchant_name_entry.get().strip()
        status = self.selected_status
        note = self.note_box.get("1.0", "end").strip()
        deadline_date, deadline_time, deadline_period = self.get_confirmed_deadline_parts()
        selected_handoff_names = [
            str(name or "").strip() for name in (self.selected_handoff_targets or []) if str(name or "").strip()
        ]
        handoff_options = [
            option
            for option in (
                self.get_handoff_option_by_display_name(name)
                for name in selected_handoff_names
            )
            if option
        ]

        if not merchant_raw_text:
            return None, "Merchant Name khong duoc de trong."

        if not deadline_date:
            return None, "Ngay hen khong duoc de trong."

        if not self.is_valid_deadline_date(deadline_date):
            return None, "Ngay hen khong hop le."

        if not deadline_time or deadline_period not in {"AM", "PM"}:
            return None, "Hay chon day du ngay gio hen."

        if status == "DONE" and not note:
            return None, "Status DONE bat buoc phai nhap note."

        if not handoff_options:
            return None, "Hay chon nguoi nhan ban giao."

        if any(str(option.get("type", "")).strip().upper() == "TEAM" for option in handoff_options):
            team_option = next(
                (option for option in handoff_options if str(option.get("type", "")).strip().upper() == "TEAM"),
                {},
            )
            handoff_to_type = "TEAM"
            handoff_to_username = ""
            handoff_to_display_name = str(team_option.get("display_name", "Tech Team")).strip() or "Tech Team"
            handoff_to_usernames = []
            handoff_to_display_names = [handoff_to_display_name]
        else:
            handoff_to_display_names = [
                str(option.get("display_name", "")).strip()
                for option in handoff_options
                if str(option.get("display_name", "")).strip()
            ]
            handoff_to_usernames = [
                str(option.get("username", "")).strip()
                for option in handoff_options
                if str(option.get("username", "")).strip()
            ]
            if not handoff_to_usernames:
                return None, "Hay chon nguoi nhan ban giao hop le."
            handoff_to_type = "USER" if len(handoff_to_usernames) == 1 else "USERS"
            handoff_to_username = handoff_to_usernames[0] if len(handoff_to_usernames) == 1 else ""
            handoff_to_display_name = ", ".join(handoff_to_display_names)

        payload = {
            "action_by_username": self.current_username,
            "merchant_raw_text": merchant_raw_text,
            "phone": self.phone_entry.get().strip(),
            "problem_summary": self.problem_entry.get().strip(),
            "handoff_to_type": handoff_to_type,
            "handoff_to_username": handoff_to_username,
            "handoff_to_display_name": handoff_to_display_name,
            "handoff_to_usernames": handoff_to_usernames,
            "handoff_to_display_names": handoff_to_display_names,
            "status": status,
            "deadline_date": deadline_date,
            "deadline_time": deadline_time,
            "deadline_period": deadline_period,
            "note": note,
        }
        return payload, ""

    def collect_setup_training_payload(self, complete_first=False):
        if not self.active_task or not self.active_task.get("task_id"):
            return None, "Hay chon task Setup / Training can xu ly."

        selected_handoff_names = [
            str(name or "").strip() for name in (self.selected_handoff_targets or []) if str(name or "").strip()
        ]
        handoff_options = [
            option
            for option in (
                self.get_handoff_option_by_display_name(name)
                for name in selected_handoff_names
            )
            if option
        ]
        if not handoff_options:
            return None, "Hay chon nguoi nhan ban giao."

        if any(str(option.get("type", "")).strip().upper() == "TEAM" for option in handoff_options):
            team_option = next(
                (option for option in handoff_options if str(option.get("type", "")).strip().upper() == "TEAM"),
                {},
            )
            handoff_to_type = "TEAM"
            handoff_to_username = ""
            handoff_to_display_name = str(team_option.get("display_name", "Tech Team")).strip() or "Tech Team"
            handoff_to_usernames = []
            handoff_to_display_names = [handoff_to_display_name]
        else:
            handoff_to_display_names = [
                str(option.get("display_name", "")).strip()
                for option in handoff_options
                if str(option.get("display_name", "")).strip()
            ]
            handoff_to_usernames = [
                str(option.get("username", "")).strip()
                for option in handoff_options
                if str(option.get("username", "")).strip()
            ]
            if not handoff_to_usernames:
                return None, "Hay chon nguoi nhan ban giao hop le."
            handoff_to_type = "USER" if len(handoff_to_usernames) == 1 else "USERS"
            handoff_to_username = handoff_to_usernames[0] if len(handoff_to_usernames) == 1 else ""
            handoff_to_display_name = ", ".join(handoff_to_display_names)

        current_task = self.active_task or {}
        started_at_text = str(current_task.get("training_started_at", "")).strip()
        started_by_username = str(current_task.get("training_started_by_username", "")).strip() or self.current_username
        started_by_display_name = (
            str(current_task.get("training_started_by_display_name", "")).strip() or self.current_display_name
        )
        if not started_at_text:
            started_at_text = datetime.now().strftime("%d-%m-%Y %I:%M %p")

        payload = {
            "action_by_username": self.current_username,
            "merchant_raw_text": current_task.get("merchant_raw", ""),
            "phone": current_task.get("phone", ""),
            "problem_summary": current_task.get("problem", ""),
            "handoff_to_type": handoff_to_type,
            "handoff_to_username": handoff_to_username,
            "handoff_to_display_name": handoff_to_display_name,
            "handoff_to_usernames": handoff_to_usernames,
            "handoff_to_display_names": handoff_to_display_names,
            "status": "2ND TRAINING" if complete_first else current_task.get("status", "SET UP & TRAINING"),
            "deadline_date": current_task.get("deadline_date", ""),
            "deadline_time": current_task.get("deadline_time", ""),
            "deadline_period": current_task.get("deadline_period", "AM"),
            "note": self.note_box.get("1.0", "end").strip(),
            "training_form": self.collect_training_form_sections(),
            "training_started_at": started_at_text,
            "training_started_by_username": started_by_username,
            "training_started_by_display_name": started_by_display_name,
        }
        return payload, ""

    def apply_follow_search(self):
        self.follow_tasks = self.get_section_filtered_tasks()
        self.filtered_follow_tasks = self.get_section_filtered_tasks(self.search_entry.get().strip())
        self.redraw_follow_canvas()

        if not self.filtered_follow_tasks:
            self.clear_follow_form()
            return

        if self.active_task:
            active_task_id = self.active_task.get("task_id")
            for task in self.filtered_follow_tasks:
                if task.get("task_id") == active_task_id:
                    return

        self.load_task_detail(self.filtered_follow_tasks[0].get("task_id"))

    def update_follow_scope_hint(self):
        if not hasattr(self, "follow_scope_label"):
            return

        prefix = "Setup / Training" if self.is_setup_training_section() else "Follow"
        if self.follow_search_scope == "show_all_with_done":
            hint_text = f"{prefix}: Show all mode | Co hien Done"
        elif self.follow_search_scope == "show_all_active_not_done":
            hint_text = f"{prefix}: Show all mode | Done hidden"
        else:
            hint_text = f"{prefix}: Board mode | Done hidden | Deadline in 3 days"
        self.follow_scope_label.configure(text=hint_text)

    def update_follow_filter_controls(self):
        if hasattr(self, "show_all_button"):
            if self.follow_show_all:
                self.show_all_button.configure(
                    text="Show All: ON",
                    fg_color=BTN_ACTIVE,
                    hover_color=BTN_ACTIVE_HOVER,
                    text_color=TEXT_DARK,
                )
            else:
                self.show_all_button.configure(
                    text="Show All: OFF",
                    fg_color=BTN_DARK,
                    hover_color=BTN_DARK_HOVER,
                    text_color=TEXT_LIGHT,
                )

        if hasattr(self, "include_done_switch"):
            if self.follow_include_done:
                self.include_done_switch.select()
            else:
                self.include_done_switch.deselect()

    def toggle_follow_show_all(self):
        self.follow_show_all = not self.follow_show_all
        if not self.follow_show_all:
            self.follow_include_done = False
        self.update_follow_filter_controls()
        self.refresh_follow_tasks(keep_selection=False)

    def on_follow_include_done_toggle(self):
        self.follow_include_done = bool(self.include_done_switch.get())
        if self.follow_include_done and not self.follow_show_all:
            self.follow_show_all = True
        self.update_follow_filter_controls()
        self.refresh_follow_tasks(keep_selection=False)

    def clear_follow_search(self):
        self.search_entry.delete(0, "end")
        self.apply_follow_search()

    def is_setup_training_section(self):
        return self.current_task_section == "setup_training"

    def get_task_module_label(self):
        return "Task - Setup / Training" if self.is_setup_training_section() else "Task Follow"

    def get_task_detail_title(self):
        return "Setup / Training Detail" if self.is_setup_training_section() else "Task Detail"

    def get_default_task_status(self):
        return "SET UP & TRAINING" if self.is_setup_training_section() else "FOLLOW"

    def get_default_detail_hint(self):
        if self.is_setup_training_section():
            return "Chon 1 task Setup / Training ben trai de xem giao dien chi tiet."
        return "Chon 1 task ben trai de xem giao dien chi tiet."

    def get_no_match_detail_hint(self):
        if self.is_setup_training_section():
            return "Khong co task Setup / Training nao khop search."
        return "Khong co task nao khop search."

    def get_new_task_hint(self):
        if self.is_setup_training_section():
            return (
                "Dang tao task Setup / Training moi. Neu muon tao moi thi bam Save. "
                "Neu dang sua task cu thi chon task ben trai roi bam Update."
            )
        return "Dang tao task moi. Neu muon tao moi thi bam Save. Neu dang sua task cu thi chon task ben trai roi bam Update."

    def get_empty_board_text(self, show_all=False, include_done=False, has_search=False):
        if has_search:
            if self.is_setup_training_section():
                return "Khong tim thay task Setup / Training nao khop merchant search."
            return "Khong tim thay task nao khop merchant search trong board hien tai."
        if show_all and include_done:
            if self.is_setup_training_section():
                return "Khong co task Setup / Training nao khop bo loc Show all + Include Done."
            return "Khong co task nao khop bo loc Show all + Include Done."
        if show_all:
            if self.is_setup_training_section():
                return "Khong co task Setup / Training nao khop bo loc Show all."
            return "Khong co task nao khop bo loc Show all."
        if self.is_setup_training_section():
            return "Chua co task Setup / Training nao trong board hien tai."
        return "Chua co task nao trong board hien tai."

    def get_section_filtered_tasks(self, query=""):
        items = self.store.filter_local(query)
        if not self.is_setup_training_section():
            return items
        return [
            item
            for item in items
            if str(item.get("status", "")).strip().upper() in {"SET UP & TRAINING", "2ND TRAINING"}
        ]

    def bind_follow_mousewheel(self):
        root = self.winfo_toplevel()
        if self.follow_mousewheel_bind_id is None and root is not None:
            self.follow_mousewheel_bind_id = root.bind(
                "<MouseWheel>",
                self.on_global_mousewheel,
                add="+",
            )
            root.bind("<Button-1>", self.on_global_click, add="+")

    def unbind_follow_mousewheel(self):
        root = self.winfo_toplevel()
        if self.follow_mousewheel_bind_id is not None and root is not None:
            try:
                root.unbind("<MouseWheel>", self.follow_mousewheel_bind_id)
            except Exception:
                pass
            self.follow_mousewheel_bind_id = None

    def on_global_click(self, event=None):
        if self.deadline_popup_frame is None or not self.deadline_popup_frame.winfo_exists():
            return
        widget = event.widget if event is not None else self.winfo_containing(self.winfo_pointerx(), self.winfo_pointery())
        if self.is_widget_inside_deadline_popup(widget):
            return
        self.close_deadline_popup()

    def is_widget_inside_deadline_popup(self, widget):
        popup = getattr(self, "deadline_popup_frame", None)
        button = getattr(self, "deadline_picker_button", None)
        combo = getattr(self, "deadline_popup_time_combo", None)
        if widget is None:
            return False

        try:
            widget_class = str(widget.winfo_class() or "").strip().lower()
        except Exception:
            widget_class = ""

        # CTkComboBox opens its option list outside the popup frame.
        # Treat menu/dropdown widgets as part of the deadline popup so selecting
        # a time does not immediately close the popup before the choice is applied.
        if combo is not None and widget_class in {"menu", "dropdownmenu"}:
            return True

        current = widget
        while current is not None:
            if current == popup or current == button or current == combo:
                return True
            try:
                parent_name = current.winfo_parent()
            except Exception:
                return False
            if not parent_name:
                return False
            try:
                current = current.nametowidget(parent_name)
            except Exception:
                return False
        return False

    def set_active_scroll_target(self, target_name):
        self.active_scroll_target = target_name

    def clear_active_scroll_target(self, target_name):
        if getattr(self, "active_scroll_target", None) == target_name:
            self.active_scroll_target = None

    def on_global_mousewheel(self, event):
        target = getattr(self, "active_scroll_target", None)
        if target == "detail" and hasattr(self, "detail_canvas"):
            self.detail_canvas.yview_scroll(-int(event.delta / 120), "units")
        elif target == "training_canvas" and getattr(self, "training_canvas", None) is not None:
            self.training_canvas.yview_scroll(-int(event.delta / 120), "units")
            self.schedule_training_canvas_refresh()
        elif target == "board" and hasattr(self, "follow_canvas"):
            self.follow_canvas.yview_scroll(-int(event.delta / 120), "units")

    def on_follow_canvas_xscroll(self, *args):
        if hasattr(self, "follow_canvas"):
            self.follow_canvas.xview(*args)
        if hasattr(self, "follow_header_canvas"):
            self.follow_header_canvas.xview(*args)

    def on_detail_canvas_configure(self, event):
        if hasattr(self, "detail_canvas_window"):
            self.detail_canvas.itemconfigure(self.detail_canvas_window, width=event.width)
            self.update_detail_scrollregion()

    def on_detail_form_configure(self, _event=None):
        self.update_detail_scrollregion()

    def update_detail_scrollregion(self):
        if hasattr(self, "detail_canvas"):
            bbox = self.detail_canvas.bbox("all")
            if bbox is not None:
                self.detail_canvas.configure(scrollregion=bbox)

    def redraw_follow_canvas(self):
        if not hasattr(self, "follow_canvas") or not hasattr(self, "follow_header_canvas"):
            return

        canvas = self.follow_canvas
        header_canvas = self.follow_header_canvas
        canvas.delete("all")
        header_canvas.delete("all")
        self.canvas_row_hits = []
        row_height = 44
        row_gap = 6
        content_padding = 46
        header_height = 62
        scrollbar_height = 18

        canvas_width = max(canvas.winfo_width(), 640)
        if self.is_setup_training_section():
            header_ratios = [
                ("Merchant", 0.48),
                ("Next", 0.24),
                ("Training", 0.28),
            ]
            min_widths = {
                "Merchant": 130,
                "Next": 90,
                "Training": 120,
            }
        else:
            header_ratios = [
                ("Merchant", 0.25),
                ("Phone", 0.13),
                ("Problem", 0.22),
                ("Handoff To", 0.12),
                ("Deadline", 0.14),
                ("Status", 0.14),
            ]
            min_widths = {
                "Merchant": 155,
                "Phone": 105,
                "Problem": 145,
                "Handoff To": 100,
                "Deadline": 120,
                "Status": 145,
            }
        x = 14
        y = 4
        right_padding = 18

        target_width = max(sum(min_widths.values()), canvas_width - (x * 2) - right_padding)
        resolved_headers = []
        used_width = 0

        for index, (label, ratio) in enumerate(header_ratios):
            if index == len(header_ratios) - 1:
                col_width = max(min_widths[label], target_width - used_width)
            else:
                col_width = max(min_widths[label], int(target_width * ratio))
            resolved_headers.append((label, col_width))
            used_width += col_width

        total_width = sum(col_width for _label, col_width in resolved_headers)
        board_right = x + total_width

        self.draw_round_rect(
            header_canvas,
            x,
            6,
            board_right,
            6 + row_height,
            14,
            CANVAS_HEADER,
            CANVAS_HEADER,
        )

        current_x = x
        for label, col_width in resolved_headers:
            header_canvas.create_text(
                current_x + (col_width / 2),
                6 + row_height / 2,
                text=label,
                anchor="center",
                fill="#f7eedf",
                font=("Segoe UI", 11, "bold"),
            )
            current_x += col_width

        header_canvas.configure(scrollregion=(0, 0, board_right + 10, row_height + 14))
        header_canvas.xview_moveto(canvas.xview()[0])

        y = 8
        tasks = self.filtered_follow_tasks or []
        content_height = header_height + content_padding
        if tasks:
            content_height += len(tasks) * row_height + max(0, len(tasks) - 1) * row_gap
        self.update_follow_board_height(content_height + scrollbar_height)

        if not tasks:
            empty_text = self.get_empty_board_text()
            if self.follow_show_all and self.follow_include_done:
                empty_text = self.get_empty_board_text(show_all=True, include_done=True)
            elif self.follow_show_all:
                empty_text = self.get_empty_board_text(show_all=True)
            elif self.search_entry.get().strip():
                empty_text = self.get_empty_board_text(has_search=True)
            canvas.create_text(
                x + 16,
                y + 24,
                text=empty_text,
                anchor="w",
                fill=TEXT_MUTED,
                font=("Segoe UI", 12),
            )
            canvas.configure(scrollregion=(0, 0, board_right + 10, y + 70))
            header_canvas.configure(scrollregion=(0, 0, board_right + 10, row_height + 14))
            return

        for index, task in enumerate(tasks):
            row_top = y + (index * (row_height + 6))
            row_bottom = row_top + row_height
            row_fill, row_text = self.get_task_row_theme(task, index)

            self.draw_round_rect(
                canvas,
                x,
                row_top,
                board_right,
                row_bottom,
                12,
                row_fill,
                "#e5d0ad",
            )

            if self.is_setup_training_section():
                stage_text = "Done 2nd" if str(task.get("status", "")).strip().upper() == "DONE" else (
                    "2nd Training" if str(task.get("status", "")).strip().upper() == "2ND TRAINING" else "Done 1st"
                )
                values = [
                    task["merchant_raw"],
                    task["deadline"],
                    stage_text,
                ]
                current_x = x
                for col_index, (value, (_label, col_width)) in enumerate(zip(values, resolved_headers)):
                    anchor = "w" if col_index == 0 else "center"
                    text_x = current_x + 8 if col_index == 0 else current_x + (col_width / 2)
                    canvas.create_text(
                        text_x,
                        row_top + row_height / 2,
                        text=value,
                        anchor=anchor,
                        width=col_width - (16 if col_index == 0 else 10),
                        fill=row_text,
                        font=("Segoe UI", 8, "bold"),
                    )
                    current_x += col_width
            else:
                values = [
                    task["merchant_raw"],
                    task["phone"],
                    task["problem"],
                    task["handoff_to"],
                    task["deadline"],
                ]

                current_x = x
                widths_without_status = [col_width for _label, col_width in resolved_headers[:-1]]
                for col_index, (value, col_width) in enumerate(zip(values, widths_without_status)):
                    anchor = "w" if col_index == 0 else "center"
                    text_x = current_x + 10 if col_index == 0 else current_x + (col_width / 2)
                    canvas.create_text(
                        text_x,
                        row_top + row_height / 2,
                        text=value,
                        anchor=anchor,
                        width=col_width - (20 if col_index == 0 else 12),
                        fill=row_text,
                        font=("Segoe UI", 9, "bold"),
                    )
                    current_x += col_width

                status_meta = STATUS_META.get(task["status"], {"bg": BTN_ACTIVE, "text": TEXT_DARK})
                pill_x1 = current_x + 8
                pill_y1 = row_top + 9
                pill_x2 = board_right - 8
                pill_y2 = row_bottom - 9
                self.draw_round_rect(
                    canvas, pill_x1, pill_y1, pill_x2, pill_y2, 12, status_meta["bg"], status_meta["bg"]
                )
                label_text = task["status"]
                if task.get("is_saving"):
                    label_text = f"{label_text} *"
                canvas.create_text(
                    (pill_x1 + pill_x2) / 2,
                    (pill_y1 + pill_y2) / 2,
                    text=label_text,
                    fill=status_meta["text"],
                    font=("Segoe UI", 7, "bold"),
                    width=max(10, pill_x2 - pill_x1 - 10),
                )

            self.canvas_row_hits.append((row_top, row_bottom, task))

        canvas.configure(
            scrollregion=(0, 0, board_right + 10, y + len(tasks) * (row_height + 6) + 30)
        )
        header_canvas.xview_moveto(canvas.xview()[0])

    def draw_round_rect(self, canvas, x1, y1, x2, y2, radius, fill, outline):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        canvas.create_polygon(points, smooth=True, fill=fill, outline=outline)

    def update_follow_board_height(self, content_height):
        if not hasattr(self, "follow_canvas_wrap"):
            return

        target_height = max(
            self.follow_board_min_height,
            min(self.follow_board_max_height, int(content_height)),
        )
        if target_height != self.follow_board_height:
            self.follow_board_height = target_height
            self.follow_canvas_wrap.configure(height=self.follow_board_height)

    def get_task_row_theme(self, task, index):
        try:
            deadline = datetime.strptime(task["deadline_date"], "%d-%m-%Y").date()
            today = datetime.now().date()
            days_left = (deadline - today).days

            if days_left < 0:
                return CANVAS_OVERDUE, CANVAS_OVERDUE_TEXT
            if days_left == 0:
                return CANVAS_TODAY, CANVAS_TODAY_TEXT
            if days_left == 1:
                return CANVAS_TOMORROW, CANVAS_TOMORROW_TEXT
            if days_left == 2:
                return CANVAS_DAY_AFTER, CANVAS_DAY_AFTER_TEXT
        except Exception:
            pass

        return (CANVAS_ROW if index % 2 == 0 else CANVAS_ROW_ALT), TEXT_DARK

    def on_follow_canvas_click(self, event):
        if not self.canvas_row_hits:
            return

        canvas_y = self.follow_canvas.canvasy(event.y)
        for row_top, row_bottom, task in self.canvas_row_hits:
            if row_top <= canvas_y <= row_bottom:
                self.load_task_detail(task.get("task_id"))
                return

    def load_task_into_form(self, task):
        self.active_task = task
        if self.is_setup_training_section():
            self.detail_hint.configure(
                text=(
                    f"Dang xem {self.get_task_module_label().lower()}: {task['merchant_name']} | "
                    "Luu checklist training va handoff nguoi tiep theo tai day."
                )
            )
            target_names = task.get("handoff_to_display_names") or []
            if not target_names and task.get("handoff_to"):
                target_names = [
                    part.strip()
                    for part in str(task.get("handoff_to", "")).split(",")
                    if part.strip()
                ]
            self.set_selected_handoffs(target_names)
            self.note_box.delete("1.0", "end")
            self.note_box.insert("1.0", task["note"])
            self.update_training_info_card(task)
            self.render_setup_training_sections(task.get("training_form") or [])
            self.render_history(task["history"])
            self.update_follow_form_mode()
            self.after_idle(self.update_detail_scrollregion)
            return

        self.detail_hint.configure(
            text=(
                f"Dang xem {self.get_task_module_label().lower()}: {task['merchant_name']} | "
                "Day la task cu, doi status/note xong bam Update."
            )
        )

        self.set_entry_value(self.merchant_name_entry, task["merchant_raw"])
        self.set_entry_value(self.phone_entry, task["phone"])
        self.set_entry_value(self.problem_entry, task["problem"])

        self.handoff_from_entry.configure(state="normal")
        self.set_entry_value(self.handoff_from_entry, task["handoff_from"])
        self.handoff_from_entry.configure(state="disabled")

        target_names = task.get("handoff_to_display_names") or []
        if not target_names and task.get("handoff_to"):
            target_names = [
                part.strip()
                for part in str(task.get("handoff_to", "")).split(",")
                if part.strip()
            ]
        self.set_selected_handoffs(target_names)
        self.select_status(task["status"])

        self.confirmed_deadline_date = task["deadline_date"]
        self.confirmed_deadline_time = ""
        if task.get("deadline_time") and task.get("deadline_period"):
            self.confirmed_deadline_time = f"{task['deadline_time']} {task['deadline_period']}"
        self.update_deadline_button_text()
        if self.current_username and task.get("deadline_date"):
            self.store.load_handoff_options(
                self.current_username,
                task_date=task["deadline_date"],
                task_time=task.get("deadline_time", ""),
                task_period=task.get("deadline_period", ""),
            )

        self.note_box.delete("1.0", "end")
        self.note_box.insert("1.0", task["note"])

        self.render_history(task["history"])
        self.update_follow_form_mode()
        self.after_idle(self.update_detail_scrollregion)

    def clear_follow_form(self):
        self.active_task = None
        self.detail_hint.configure(text=self.get_no_match_detail_hint())

        if self.is_setup_training_section():
            self.note_box.delete("1.0", "end")
            self.set_selected_handoffs(["Tech Team"])
            self.update_training_info_card({})
            self.render_setup_training_sections([])
            self.render_history([])
            self.update_follow_form_mode()
            self.after_idle(self.update_detail_scrollregion)
            return

        for entry in [
            self.merchant_name_entry,
            self.phone_entry,
            self.problem_entry,
        ]:
            self.set_entry_value(entry, "")
        self.confirmed_deadline_date = ""
        self.confirmed_deadline_time = ""
        self.pending_deadline_date = ""
        self.pending_deadline_time = self.deadline_time_slots[0] if self.deadline_time_slots else ""
        self.update_deadline_button_text()

        self.handoff_from_entry.configure(state="normal")
        self.set_entry_value(self.handoff_from_entry, self.current_display_name)
        self.handoff_from_entry.configure(state="disabled")

        self.note_box.delete("1.0", "end")
        self.set_selected_handoffs(["Tech Team"])
        self.select_status(self.get_default_task_status())
        self.render_history([])
        self.update_follow_form_mode()
        self.after_idle(self.update_detail_scrollregion)

    def start_new_task(self):
        if self.is_setup_training_section():
            messagebox.showinfo(
                self.get_task_module_label(),
                "Task Setup / Training duoc mo tu Task Follow co status Setup / Training.",
            )
            return
        self.active_task = None
        self.clear_follow_form()
        self.detail_hint.configure(text=self.get_new_task_hint())

    def open_setup_training_from_follow(self):
        if not self.active_task or not self.active_task.get("task_id"):
            messagebox.showwarning("Task Follow", "Hay chon task Setup / Training truoc.")
            return

        if str(self.active_task.get("status", "")).strip().upper() != "SET UP & TRAINING":
            messagebox.showwarning("Task Follow", "Chi task status SET UP & TRAINING moi mo duoc 1st training.")
            return

        self.pending_focus_task_id = self.active_task.get("task_id")
        self.follow_show_all = True
        self.render_section("setup_training")

    def on_complete_first_training(self):
        if not self.active_task or not self.active_task.get("task_id"):
            messagebox.showwarning(self.get_task_module_label(), "Hay chon task can hoan tat 1st training.")
            return

        payload, error_message = self.collect_setup_training_payload(complete_first=True)
        if error_message:
            messagebox.showwarning(self.get_task_module_label(), error_message)
            return

        if not self._start_follow_action("update"):
            return

        self.store.update_item(
            self.active_task["task_id"],
            payload,
            actor_display_name=self.current_display_name,
            action_by=self.current_username,
        )

    def on_follow_wrap_configure(self, _event=None):
        self.refresh_follow_layout()

    def refresh_follow_layout(self):
        if not hasattr(self, "follow_wrap"):
            return

        width = self.follow_wrap.winfo_width()
        height = self.follow_wrap.winfo_height()
        if width <= 1 or height <= 1:
            return

        new_mode = "split"
        self.follow_board_max_height = max(self.follow_board_min_height, min(620, height - 170))

        if new_mode != self.follow_layout_mode:
            self.follow_layout_mode = new_mode
            if self.is_setup_training_section():
                self.follow_wrap.grid_columnconfigure(0, weight=78)
                self.follow_wrap.grid_columnconfigure(1, weight=22)
                self.follow_wrap.grid_rowconfigure(1, weight=1, minsize=0)
                self.follow_wrap.grid_rowconfigure(2, weight=0, minsize=0)
                self.detail_card.grid_configure(row=1, column=0, padx=(16, 8), pady=(0, 16), sticky="nsew")
                self.table_card.grid_configure(row=1, column=1, padx=(8, 16), pady=(0, 16), sticky="nsew")
                self.table_card.configure(width=260)
            else:
                self.follow_wrap.grid_columnconfigure(0, weight=85)
                self.follow_wrap.grid_columnconfigure(1, weight=15)
                self.follow_wrap.grid_rowconfigure(1, weight=1, minsize=0)
                self.follow_wrap.grid_rowconfigure(2, weight=0, minsize=0)
                self.table_card.grid_configure(row=1, column=0, padx=(16, 8), pady=(0, 16), sticky="new")
                self.detail_card.grid_configure(row=1, column=1, padx=(8, 16), pady=(0, 16), sticky="nsew")
                self.detail_card.configure(width=180)

    def set_entry_value(self, entry, value):
        entry.delete(0, "end")
        if value:
            entry.insert(0, value)

    def render_history(self, history_items):
        for widget in self.history_box.winfo_children():
            widget.destroy()

        if not history_items:
            ctk.CTkLabel(
                self.history_box,
                text="Chua co history.",
                font=("Segoe UI", 12),
                text_color=TEXT_MUTED,
            ).pack(anchor="w", padx=8, pady=8)
            return

        grouped_history_items = []
        index = 0
        while index < len(history_items):
            item = history_items[index] or {}
            action_type = str(item.get("action_type", "")).strip().upper()
            if action_type == "ASSIGN":
                grouped_entry = {
                    "user": item.get("user", ""),
                    "time": item.get("time", ""),
                    "assign_note": item.get("note", ""),
                    "note": "",
                }
                if index + 1 < len(history_items):
                    next_item = history_items[index + 1] or {}
                    next_action_type = str(next_item.get("action_type", "")).strip().upper()
                    if (
                        next_action_type != "ASSIGN"
                        and str(next_item.get("user", "")).strip() == str(item.get("user", "")).strip()
                        and str(next_item.get("time", "")).strip() == str(item.get("time", "")).strip()
                    ):
                        grouped_entry["note"] = next_item.get("note", "")
                        index += 1
                grouped_history_items.append(grouped_entry)
            else:
                grouped_history_items.append(
                    {
                        "user": item.get("user", ""),
                        "time": item.get("time", ""),
                        "assign_note": "",
                        "note": item.get("note", ""),
                    }
                )
            index += 1

        for item in grouped_history_items:
            card = ctk.CTkFrame(
                self.history_box,
                fg_color="#fffaf3",
                corner_radius=10,
                border_width=1,
                border_color="#e6cfab",
            )
            card.pack(fill="x", padx=6, pady=5)

            ctk.CTkLabel(
                card,
                text=f"{item['user']} | {item['time']}",
                font=("Segoe UI", 12, "bold"),
                text_color=TEXT_DARK,
            ).pack(anchor="w", padx=10, pady=(8, 4))

            assign_note = str(item.get("assign_note", "")).strip()
            if assign_note:
                assign_wrap = ctk.CTkFrame(
                    card,
                    fg_color="#fff1d6",
                    corner_radius=8,
                    border_width=1,
                    border_color="#d6a24a",
                )
                assign_wrap.pack(fill="x", padx=10, pady=(0, 6))

                ctk.CTkLabel(
                    assign_wrap,
                    text=assign_note,
                    font=("Segoe UI", 11, "bold"),
                    text_color="#8a4b00",
                    justify="left",
                    wraplength=308,
                ).pack(anchor="w", padx=10, pady=(8, 8))

            note_text = str(item.get("note", "")).strip()
            if note_text:
                ctk.CTkLabel(
                    card,
                    text=note_text,
                    font=("Segoe UI", 12),
                    text_color=TEXT_MUTED,
                    justify="left",
                    wraplength=330,
                ).pack(anchor="w", padx=10, pady=(0, 8))

        self.after_idle(self.update_detail_scrollregion)

    def on_follow_save(self):
        if self.is_setup_training_section():
            messagebox.showinfo(
                self.get_task_module_label(),
                "Task Setup / Training duoc tao tu Task Follow. Vui long mo tu task goc.",
            )
            return
        if self.active_task and self.active_task.get("task_id"):
            messagebox.showwarning(
                self.get_task_module_label(),
                "Task nay dang o che do update. Neu ban muon sua status/note thi bam Update, khong dung Save.",
            )
            return

        payload, error_message = self.collect_follow_form_payload()
        if error_message:
            messagebox.showwarning(self.get_task_module_label(), error_message)
            return

        if not self._start_follow_action("save"):
            return

        temp_id = self.store.create_item(
            payload,
            actor_display_name=self.current_display_name,
            action_by=self.current_username,
        )
        self.follow_tasks = self.store.get_all()
        self.filtered_follow_tasks = self.store.filter_local(self.search_entry.get().strip())
        self.redraw_follow_canvas()
        self.load_task_detail(temp_id)

    def on_follow_update(self):
        if not self.active_task or not self.active_task.get("task_id"):
            messagebox.showwarning(self.get_task_module_label(), "Hay chon task can update.")
            return

        if self.is_setup_training_section():
            payload, error_message = self.collect_setup_training_payload(complete_first=False)
        else:
            payload, error_message = self.collect_follow_form_payload()
        if error_message:
            messagebox.showwarning(self.get_task_module_label(), error_message)
            return

        if not self._start_follow_action("update"):
            return

        self.store.update_item(
            self.active_task["task_id"],
            payload,
            actor_display_name=self.current_display_name,
            action_by=self.current_username,
        )