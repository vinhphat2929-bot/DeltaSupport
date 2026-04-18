import re
import tkinter as tk
from datetime import datetime
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
    "MISS TIP / CHARGE BACK": {"bg": "#f59e0b", "text": "#2a221d"},
    "DONE": {"bg": "#ef4444", "text": "#ffffff"},
    "DEMO": {"bg": "#ec4899", "text": "#ffffff"},
}


class ProcessPage(ctk.CTkFrame):
    def __init__(self, parent, initial_section="report", current_user=None):
        super().__init__(parent, fg_color="transparent")

        self.initial_section = initial_section
        self.current_user = current_user or {}
        self.current_username = str(self.current_user.get("username", "")).strip()
        self.current_full_name = str(self.current_user.get("full_name", "")).strip()
        self.current_department = str(self.current_user.get("department", "")).strip()
        self.current_team = str(self.current_user.get("team", "General")).strip() or "General"
        self.current_display_name = self.current_full_name or self.current_username

        self.store = TaskStore()

        self.selected_status = "FOLLOW"
        self.selected_handoff_to = "Tech Team"
        self.status_buttons = {}
        self.handoff_buttons = {}
        self.handoff_options = [{"username": "", "display_name": "Tech Team", "type": "TEAM"}]
        self.canvas_row_hits = []
        self.last_valid_deadline_text = ""
        self.last_deadline_edit_text = "DD-MM-YYYY"
        self.follow_layout_mode = None
        self.active_scroll_target = None
        self.follow_mousewheel_bind_id = None
        self.follow_poll_after_id = None

        self.follow_tasks = []
        self.filtered_follow_tasks = []
        self.active_task = None
        self.follow_search_scope = "board"
        self.follow_show_all = False
        self.follow_include_done = False
        self.follow_board_min_height = 220
        self.follow_board_max_height = 520
        self.follow_board_height = self.follow_board_min_height

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
        self.unbind_follow_mousewheel()
        if self.follow_poll_after_id:
            self.after_cancel(self.follow_poll_after_id)
            self.follow_poll_after_id = None
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

        if section_key == "follow":
            self.header_card.grid_remove()
        else:
            self.header_card.grid()
            self.title_label.configure(text=title)
            self.subtitle_label.configure(text=subtitle)

        for widget in self.body_card.winfo_children():
            widget.destroy()

        if section_key == "follow":
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

        ctk.CTkButton(
            self.follow_top_card,
            text="Refresh UI",
            width=104,
            height=34,
            corner_radius=12,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 12, "bold"),
            command=lambda: self.refresh_follow_tasks(force=True),
        ).grid(row=0, column=9, sticky="e", padx=(0, 18), pady=16)

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
        self.build_follow_detail_form()
        self.update_follow_filter_controls()
        self.load_follow_bootstrap()
        self.after(60, self.refresh_follow_layout)

    def build_follow_detail_form(self):
        ctk.CTkLabel(
            self.detail_form,
            text="Task Detail",
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_DARK,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 10))

        self.detail_hint = ctk.CTkLabel(
            self.detail_form,
            text="Chon 1 task ben trai de xem giao dien chi tiet.",
            font=("Segoe UI", 12),
            text_color=TEXT_MUTED,
            justify="left",
        )
        self.detail_hint.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

        self.merchant_name_entry = self.create_labeled_entry(2, "Merchant Name", "SAPPHIRE NAILS 45805")
        self.phone_entry = self.create_labeled_entry(3, "Phone", "(012) 345-6789")
        self.phone_entry.bind("<KeyRelease>", self.on_phone_input)
        self.problem_entry = self.create_labeled_entry(4, "Problem", "Setup + 1st training")
        self.handoff_from_entry = self.create_labeled_entry(5, "Nguoi ban giao", "Current Display Name", state="disabled")

        self.create_section_label(6, "Nguoi nhan ban giao")
        self.handoff_button_wrap = ctk.CTkFrame(self.detail_form, fg_color="transparent")
        self.handoff_button_wrap.grid(row=7, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.render_handoff_buttons()

        self.create_section_label(8, "Status")
        status_wrap = ctk.CTkFrame(self.detail_form, fg_color="transparent")
        status_wrap.grid(row=9, column=0, sticky="ew", padx=18, pady=(0, 12))

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

        deadline_wrap = ctk.CTkFrame(self.detail_form, fg_color="transparent")
        deadline_wrap.grid(row=10, column=0, sticky="ew", padx=18, pady=(2, 10))

        ctk.CTkLabel(
            deadline_wrap,
            text="Ngay hen",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_DARK,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        ctk.CTkLabel(
            deadline_wrap,
            text="Gio hen",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_DARK,
        ).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 6))

        self.deadline_date_entry = ctk.CTkEntry(
            deadline_wrap,
            width=128,
            height=36,
            placeholder_text="DD-MM-YYYY",
            fg_color=INPUT_BG,
            border_color=INPUT_BORDER,
            text_color=TEXT_DARK,
        )
        self.deadline_date_entry.grid(row=1, column=0, sticky="w")
        self.deadline_date_entry.insert(0, "DD-MM-YYYY")
        self.deadline_date_entry.bind("<FocusIn>", self.on_deadline_focus_in)
        self.deadline_date_entry.bind("<FocusOut>", self.on_deadline_focus_out)
        self.deadline_date_entry.bind("<KeyRelease>", self.on_deadline_date_input)

        self.deadline_time_combo = ctk.CTkComboBox(
            deadline_wrap,
            values=[
                "08:00", "08:30", "09:00", "09:30", "10:00", "10:30",
                "11:00", "11:30", "12:00", "12:30", "01:00", "01:30",
                "02:00", "02:30", "03:00", "03:30", "04:00", "04:30",
                "05:00", "05:30", "06:00", "06:30", "07:00", "07:30",
            ],
            width=108,
            height=36,
            fg_color=INPUT_BG,
            border_color=INPUT_BORDER,
            button_color=BTN_ACTIVE,
            button_hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            dropdown_fg_color=INPUT_BG,
            dropdown_text_color=TEXT_DARK,
        )
        self.deadline_time_combo.grid(row=1, column=1, sticky="w", padx=(10, 8))
        self.deadline_time_combo.set("02:00")

        self.deadline_period_combo = ctk.CTkComboBox(
            deadline_wrap,
            values=["AM", "PM"],
            width=72,
            height=36,
            fg_color=INPUT_BG,
            border_color=INPUT_BORDER,
            button_color=BTN_ACTIVE,
            button_hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            dropdown_fg_color=INPUT_BG,
            dropdown_text_color=TEXT_DARK,
        )
        self.deadline_period_combo.grid(row=1, column=2, sticky="w")
        self.deadline_period_combo.set("AM")

        self.create_section_label(11, "Note")
        self.note_box = ctk.CTkTextbox(
            self.detail_form,
            height=110,
            fg_color=INPUT_BG,
            border_color=INPUT_BORDER,
            border_width=1,
            text_color=TEXT_DARK,
            corner_radius=12,
        )
        self.note_box.grid(row=12, column=0, sticky="ew", padx=18, pady=(0, 12))

        action_row = ctk.CTkFrame(self.detail_form, fg_color="transparent")
        action_row.grid(row=13, column=0, sticky="ew", padx=18, pady=(0, 14))

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

        self.create_section_label(14, "History / Log")
        self.history_box = ctk.CTkScrollableFrame(
            self.detail_form,
            height=180,
            fg_color="#fff7ed",
            border_width=1,
            border_color=INPUT_BORDER,
            corner_radius=12,
        )
        self.history_box.grid(row=15, column=0, sticky="ew", padx=18, pady=(0, 18))

        self.select_status(self.selected_status)
        self.select_handoff(self.selected_handoff_to)
        self.handoff_from_entry.configure(state="normal")
        self.set_entry_value(self.handoff_from_entry, self.current_display_name)
        self.handoff_from_entry.configure(state="disabled")
        self.update_follow_form_mode()

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
                command=lambda value=display_name: self.select_handoff(value),
            )
            btn.grid(row=idx // 2, column=idx % 2, sticky="w", padx=(0, 8), pady=4)
            self.handoff_buttons[display_name] = btn

        if self.selected_handoff_to not in self.handoff_buttons and self.handoff_buttons:
            self.selected_handoff_to = next(iter(self.handoff_buttons))

        if self.handoff_buttons:
            self.select_handoff(self.selected_handoff_to)

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

        if hasattr(self, "follow_save_button"):
            if is_edit_mode:
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
            if is_edit_mode:
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

    def select_handoff(self, handoff_name):
        self.selected_handoff_to = handoff_name

        for name, button in self.handoff_buttons.items():
            if name == handoff_name:
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

    def on_phone_input(self, _event=None):
        digits = re.sub(r"\D", "", self.phone_entry.get())[:10]
        formatted = self.format_phone(digits)
        self.phone_entry.delete(0, "end")
        self.phone_entry.insert(0, formatted)

    def on_deadline_date_input(self, _event=None):
        raw_value = self.deadline_date_entry.get()
        if raw_value == "DD-MM-YYYY":
            return

        digits = re.sub(r"\D", "", raw_value)[:8]
        formatted, is_complete = self.format_deadline_date(digits)

        if formatted and not self.is_valid_deadline_partial(formatted):
            fallback_value = self.last_deadline_edit_text or self.last_valid_deadline_text or ""
            self.deadline_date_entry.delete(0, "end")
            self.deadline_date_entry.insert(0, fallback_value)
            return

        self.deadline_date_entry.delete(0, "end")
        self.deadline_date_entry.insert(0, formatted)
        self.last_deadline_edit_text = formatted

        if is_complete and formatted:
            self.last_valid_deadline_text = formatted

    def on_deadline_focus_in(self, _event=None):
        if self.deadline_date_entry.get() == "DD-MM-YYYY":
            self.deadline_date_entry.delete(0, "end")
            self.last_deadline_edit_text = ""
            return

        self.last_deadline_edit_text = self.deadline_date_entry.get().strip()

    def on_deadline_focus_out(self, _event=None):
        current_value = self.deadline_date_entry.get().strip()
        if not current_value:
            self.deadline_date_entry.delete(0, "end")
            self.deadline_date_entry.insert(0, "DD-MM-YYYY")
            return

        if current_value == "DD-MM-YYYY":
            return

        if not self.is_valid_deadline_date(current_value):
            fallback_value = self.last_valid_deadline_text or "DD-MM-YYYY"
            self.deadline_date_entry.delete(0, "end")
            self.deadline_date_entry.insert(0, fallback_value)
            self.last_deadline_edit_text = fallback_value
        else:
            self.last_deadline_edit_text = current_value

    def format_phone(self, digits):
        if not digits:
            return ""
        if len(digits) <= 3:
            return f"({digits}"
        if len(digits) <= 6:
            return f"({digits[:3]}) {digits[3:]}"
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:10]}"

    def format_deadline_date(self, digits):
        if not digits:
            return "", False
        parts = []
        if len(digits) <= 2:
            parts = [digits]
        elif len(digits) <= 4:
            parts = [digits[:2], digits[2:4]]
        else:
            parts = [digits[:2], digits[2:4], digits[4:8]]

        formatted = "-".join(part for part in parts if part)
        is_complete = len(digits) == 8 and self.is_valid_deadline_date(formatted)
        return formatted, is_complete

    def is_valid_deadline_date(self, date_text):
        try:
            datetime.strptime(date_text, "%d-%m-%Y")
            return True
        except ValueError:
            return False

    def is_valid_deadline_partial(self, date_text):
        parts = date_text.split("-")
        if not parts:
            return True

        day_text = parts[0] if len(parts) > 0 else ""
        month_text = parts[1] if len(parts) > 1 else ""
        year_text = parts[2] if len(parts) > 2 else ""

        if day_text:
            day = int(day_text)
            if len(day_text) == 1:
                if day < 0 or day > 3:
                    return False
            elif day < 1 or day > 31:
                return False

        if month_text:
            month = int(month_text)
            if len(month_text) == 1:
                if month < 0 or month > 1:
                    return False
            elif month < 1 or month > 12:
                return False

        if year_text:
            if len(year_text) > 4:
                return False

        if len(day_text) == 2 and len(month_text) == 2 and year_text:
            try:
                int(year_text)
            except ValueError:
                return False

            if len(year_text) == 4:
                try:
                    datetime.strptime(f"{day_text}-{month_text}-{year_text}", "%d-%m-%Y")
                except ValueError:
                    return False

        return True

    def load_follow_bootstrap(self):
        self.store.set_view(show_all=self.follow_show_all, include_done=self.follow_include_done)
        self.store.load_handoff_options(self.current_username)
        self.refresh_follow_tasks()
        self.poll_follow_store_events()

    def poll_follow_store_events(self):
        for event in self.store.drain_events():
            self.handle_follow_store_event(event)
        self.follow_poll_after_id = self.after(120, self.poll_follow_store_events)

    def handle_follow_store_event(self, event):
        event_type = event.get("type")

        if event_type == "tasks_loaded":
            self.follow_search_scope = str(event.get("search_scope", "board")).strip() or "board"
            self.apply_follow_search()
            return

        if event_type == "tasks_loading":
            return

        if event_type == "tasks_load_failed":
            self.follow_tasks = []
            self.filtered_follow_tasks = []
            self.follow_search_scope = "board"
            self.update_follow_scope_hint()
            self.redraw_follow_canvas()
            self.clear_follow_form()
            messagebox.showerror("Task Follow", event.get("message", "Khong load duoc task."))
            return

        if event_type == "handoff_options_loaded":
            self.current_display_name = (
                str(event.get("current_display_name", "")).strip()
                or self.current_full_name
                or self.current_username
            )
            self.handoff_options = event.get("options", []) or self.handoff_options
            self.render_handoff_buttons()
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
            messagebox.showerror("Task Follow", event.get("message", "Khong load duoc task detail."))
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
            messagebox.showerror("Task Follow", event.get("message", "Khong luu duoc task."))
            self.follow_tasks = self.store.get_all()
            self.filtered_follow_tasks = self.store.filter_local(self.search_entry.get().strip())
            self.redraw_follow_canvas()
            rollback_item = event.get("rollback_item")
            if rollback_item and event.get("action") == "update":
                self.load_task_into_form(rollback_item)
            return

        if event_type == "task_save_succeeded":
            messagebox.showinfo("Task Follow", event.get("message", "Da luu task thanh cong."))

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

        self.follow_tasks = self.store.get_all()
        self.filtered_follow_tasks = self.store.filter_local(self.search_entry.get().strip())
        self.follow_search_scope = self.store.search_scope
        self.update_follow_scope_hint()
        self.redraw_follow_canvas()

        current_task_id = self.active_task.get("task_id") if keep_selection and self.active_task else None
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
        self.store.ensure_detail(task_id, action_by=self.current_username)

    def collect_follow_form_payload(self):
        merchant_raw_text = self.merchant_name_entry.get().strip()
        status = self.selected_status
        note = self.note_box.get("1.0", "end").strip()
        deadline_date = self.deadline_date_entry.get().strip()
        handoff_option = self.get_handoff_option_by_display_name(self.selected_handoff_to) or {}

        if not merchant_raw_text:
            return None, "Merchant Name khong duoc de trong."

        if deadline_date == "DD-MM-YYYY":
            deadline_date = ""

        if not deadline_date:
            return None, "Ngay hen khong duoc de trong."

        if not self.is_valid_deadline_date(deadline_date):
            return None, "Ngay hen khong hop le."

        if status == "DONE" and not note:
            return None, "Status DONE bat buoc phai nhap note."

        payload = {
            "action_by_username": self.current_username,
            "merchant_raw_text": merchant_raw_text,
            "phone": self.phone_entry.get().strip(),
            "problem_summary": self.problem_entry.get().strip(),
            "handoff_to_type": str(handoff_option.get("type", "TEAM")).strip().upper(),
            "handoff_to_username": str(handoff_option.get("username", "")).strip(),
            "handoff_to_display_name": self.selected_handoff_to,
            "status": status,
            "deadline_date": deadline_date,
            "deadline_time": self.deadline_time_combo.get().strip(),
            "deadline_period": self.deadline_period_combo.get().strip(),
            "note": note,
        }
        return payload, ""

    def apply_follow_search(self):
        self.follow_tasks = self.store.get_all()
        self.filtered_follow_tasks = self.store.filter_local(self.search_entry.get().strip())
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

        if self.follow_search_scope == "show_all_with_done":
            hint_text = "Show all mode: active task | Co hien Done"
        elif self.follow_search_scope == "show_all_active_not_done":
            hint_text = "Show all mode: active task | Done hidden"
        else:
            hint_text = "Board mode: active task | Done hidden | Deadline in 3 days"
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

    def bind_follow_mousewheel(self):
        root = self.winfo_toplevel()
        if self.follow_mousewheel_bind_id is None and root is not None:
            self.follow_mousewheel_bind_id = root.bind(
                "<MouseWheel>",
                self.on_global_mousewheel,
                add="+",
            )

    def unbind_follow_mousewheel(self):
        root = self.winfo_toplevel()
        if self.follow_mousewheel_bind_id is not None and root is not None:
            try:
                root.unbind("<MouseWheel>", self.follow_mousewheel_bind_id)
            except Exception:
                pass
            self.follow_mousewheel_bind_id = None

    def set_active_scroll_target(self, target_name):
        self.active_scroll_target = target_name

    def clear_active_scroll_target(self, target_name):
        if getattr(self, "active_scroll_target", None) == target_name:
            self.active_scroll_target = None

    def on_global_mousewheel(self, event):
        target = getattr(self, "active_scroll_target", None)
        if target == "detail" and hasattr(self, "detail_canvas"):
            self.detail_canvas.yview_scroll(-int(event.delta / 120), "units")
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
            empty_text = "Chua co task nao trong board hien tai."
            if self.follow_show_all and self.follow_include_done:
                empty_text = "Khong co task nao khop bo loc Show all + Include Done."
            elif self.follow_show_all:
                empty_text = "Khong co task nao khop bo loc Show all."
            elif self.search_entry.get().strip():
                empty_text = "Khong tim thay task nao khop merchant search trong board hien tai."
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
        self.detail_hint.configure(
            text=f"Dang xem task: {task['merchant_name']} | Day la task cu, doi status/note xong bam Update."
        )

        self.set_entry_value(self.merchant_name_entry, task["merchant_raw"])
        self.set_entry_value(self.phone_entry, task["phone"])
        self.set_entry_value(self.problem_entry, task["problem"])

        self.handoff_from_entry.configure(state="normal")
        self.set_entry_value(self.handoff_from_entry, task["handoff_from"])
        self.handoff_from_entry.configure(state="disabled")

        if task["handoff_to"] in self.handoff_buttons:
            self.select_handoff(task["handoff_to"])
        self.select_status(task["status"])

        self.set_entry_value(self.deadline_date_entry, task["deadline_date"])
        self.last_valid_deadline_text = task["deadline_date"]
        self.last_deadline_edit_text = task["deadline_date"]
        self.deadline_time_combo.set(task["deadline_time"])
        self.deadline_period_combo.set(task["deadline_period"])

        self.note_box.delete("1.0", "end")
        self.note_box.insert("1.0", task["note"])

        self.render_history(task["history"])
        self.update_follow_form_mode()
        self.after_idle(self.update_detail_scrollregion)

    def clear_follow_form(self):
        self.active_task = None
        self.detail_hint.configure(text="Khong co task nao khop search.")

        for entry in [
            self.merchant_name_entry,
            self.phone_entry,
            self.problem_entry,
        ]:
            self.set_entry_value(entry, "")

        self.set_entry_value(self.deadline_date_entry, "DD-MM-YYYY")

        self.handoff_from_entry.configure(state="normal")
        self.set_entry_value(self.handoff_from_entry, self.current_display_name)
        self.handoff_from_entry.configure(state="disabled")

        self.note_box.delete("1.0", "end")
        self.select_handoff("Tech Team")
        self.select_status("FOLLOW")
        self.last_valid_deadline_text = ""
        self.last_deadline_edit_text = "DD-MM-YYYY"
        self.render_history([])
        self.update_follow_form_mode()
        self.after_idle(self.update_detail_scrollregion)

    def start_new_task(self):
        self.active_task = None
        self.clear_follow_form()
        self.detail_hint.configure(
            text="Dang tao task moi. Neu muon tao moi thi bam Save. Neu dang sua task cu thi chon task ben trai roi bam Update."
        )
        self.deadline_time_combo.set("02:00")
        self.deadline_period_combo.set("AM")

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

        for item in history_items:
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

            ctk.CTkLabel(
                card,
                text=item["note"],
                font=("Segoe UI", 12),
                text_color=TEXT_MUTED,
                justify="left",
                wraplength=330,
            ).pack(anchor="w", padx=10, pady=(0, 8))

        self.after_idle(self.update_detail_scrollregion)

    def on_follow_save(self):
        if self.active_task and self.active_task.get("task_id"):
            messagebox.showwarning(
                "Task Follow",
                "Task nay dang o che do update. Neu ban muon sua status/note thi bam Update, khong dung Save.",
            )
            return

        payload, error_message = self.collect_follow_form_payload()
        if error_message:
            messagebox.showwarning("Task Follow", error_message)
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
            messagebox.showwarning("Task Follow", "Hay chon task can update.")
            return

        payload, error_message = self.collect_follow_form_payload()
        if error_message:
            messagebox.showwarning("Task Follow", error_message)
            return

        self.store.update_item(
            self.active_task["task_id"],
            payload,
            actor_display_name=self.current_display_name,
            action_by=self.current_username,
        )

