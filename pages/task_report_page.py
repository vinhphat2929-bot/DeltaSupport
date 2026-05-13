import calendar
import os
import re
import tempfile
import threading
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from xml.sax.saxutils import escape
import tkinter as tk

import customtkinter as ctk
from PIL import Image

from services.task_report_service import TaskReportService
from services.task_service import TaskService
from services.timezone_service import (
    current_local_datetime,
    lookup_timezone_by_zip,
    normalize_timezone_name,
)
from utils.resource_utils import get_data_path
from utils.window_icon_utils import apply_app_window_icon


CARD_BG = "#fbf5ec"
CARD_ALT_BG = "#fffaf3"
CARD_SELECTED_BG = "#f8e3c4"
MUTED_BG = "#f7efe2"
HEADER_BG = "#2359c4"
HEADER_TEXT = "#ffb000"
SUCCESS_TEXT = "#0f766e"
ERROR_TEXT = "#9f2d2d"
PROCESSING_COLOR = "#ef4444"
PROCESSING_BG = "#f7d0d0"
FORM_CARD_BG = "#fff8ef"
FORM_CARD_BORDER = "#d8b780"
FORM_ACCENT = "#8b5e1a"
FILTER_CARD_BG = "#fffaf2"
FILTER_CARD_BORDER = "#d8c39d"
FILTER_ACCENT = "#c58b42"
TABLE_CARD_BG = "#f8f1e6"
TABLE_CARD_BORDER = "#cfb585"
TABLE_ACCENT = "#2359c4"
TASK_REPORT_SCHEDULE_ZIP_CODE = "77072"
TASK_REPORT_DEFAULT_TIMEZONE = "America/Chicago"

PROCESSING_OPTIONS = ["DONE", "FOLLOW", "SYNC"]

FILTER_MODES = ["Daily", "Week", "Month", "Range"]

REPORT_LIST_COLUMNS = [
    {"key": "date_time", "label": "DATE / TIME", "width": 168, "anchor": "center"},
    {"key": "merchant", "label": "MERCHANT", "width": 220, "anchor": "w"},
    {"key": "caller_phone", "label": "CALLER PHONE", "width": 150, "anchor": "center"},
    {"key": "processing", "label": "STATUS", "width": 124, "anchor": "center"},
    {"key": "technician", "label": "TECHNICIAN", "width": 140, "anchor": "center"},
    {"key": "problem", "label": "PROBLEM PREVIEW", "width": 340, "anchor": "w", "heading_anchor": "w"},
    {"key": "solution", "label": "SOLUTION PREVIEW", "width": 320, "anchor": "w", "heading_anchor": "w"},
]

REPORT_TABLE_COLUMNS = [
    {"key": "report_date", "label": "DATE", "width": 170, "wraplength": 92, "center": True},
    {"key": "report_time", "label": "TIME", "width": 170, "wraplength": 86, "center": True},
    {"key": "merchant", "label": "MERCHANT", "width": 170, "wraplength": 220, "bold": True, "center": True},
    {"key": "caller_phone", "label": "CALLER PHONE", "width": 170, "wraplength": 120, "center": True},
    {"key": "problem", "label": "PROBLEM", "width": 170, "wraplength": 260},
    {"key": "solution", "label": "SOLUTION", "width": 170, "wraplength": 280},
    {"key": "processing", "label": "PROCESSING", "width": 170, "wraplength": 120, "center": True},
    {
        "key": "technician_display_name",
        "label": "TECHNICIANS",
        "width": 170,
        "wraplength": 130,
        "center": True,
    },
]

REPORT_TABLE_CELL_PADX = 8
REPORT_TABLE_ROW_PADY = 8
REPORT_TABLE_ROW_OUTER_PADX = 8
REPORT_TABLE_ROW_GAP_Y = 2
REPORT_TABLE_HEADER_PADY = 10
REPORT_TABLE_ROW_FONT_SIZE = 12
REPORT_TABLE_HEADER_FONT_SIZE = 13
REPORT_TABLE_BADGE_WIDTH = 110
REPORT_TABLE_BADGE_HEIGHT = 26
REPORT_TABLE_SCROLLBAR_WIDTH = 16
REPORT_TABLE_MIN_ROW_HEIGHT = REPORT_TABLE_BADGE_HEIGHT + (REPORT_TABLE_ROW_PADY * 2)
REPORT_TABLE_ESTIMATED_ROW_HEIGHT = 44
REPORT_TABLE_LINE_HEIGHT = 20
REPORT_TABLE_VIEWPORT_BUFFER_PX = 360
REPORT_TABLE_STRICT_TEXT_COLUMNS = {"problem", "solution"}
REPORT_FORM_PANEL_WIDTH = 370
REPORT_FORM_SCROLLBAR_WIDTH = 14


def normalize_text(value):
    return str(value or "").strip()


def parse_ui_date(value):
    text = normalize_text(value)
    if not text:
        return None
    for pattern in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def format_ui_date(date_value):
    if not date_value:
        return ""
    return date_value.strftime("%d-%m-%Y")


def parse_ui_time(value):
    text = normalize_text(value)
    if not text:
        return None
    for pattern in ("%H:%M:%S", "%H:%M"):
        try:
            parsed = datetime.strptime(text, pattern).time()
            return parsed.replace(microsecond=0)
        except ValueError:
            continue
    return None


def format_ui_time(time_value):
    if not time_value:
        return ""
    return time_value.strftime("%H:%M:%S")


def format_picker_time(value):
    parsed_time = parse_ui_time(value) if not hasattr(value, "strftime") else value
    if not parsed_time:
        return ""
    return parsed_time.strftime("%I:%M %p")


def split_task_deadline_time(value):
    parsed_time = parse_ui_time(value) if not hasattr(value, "strftime") else value
    if not parsed_time:
        return "08:00", "AM"
    return parsed_time.strftime("%I:%M").lstrip("0"), parsed_time.strftime("%p")


def format_phone_digits(digits):
    if not digits:
        return ""
    if len(digits) <= 3:
        return f"({digits}"
    if len(digits) <= 6:
        return f"({digits[:3]}) {digits[3:]}"
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:10]}"


def build_single_line_preview(value, limit=96):
    text = " ".join(normalize_text(value).split())
    if not text:
        return "-"
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def shift_date_by_month(date_value, month_delta):
    total_month = (date_value.year * 12 + date_value.month - 1) + month_delta
    year = total_month // 12
    month = total_month % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date_value.replace(year=year, month=month, day=min(date_value.day, last_day))


def build_report_sort_key(item):
    report_date = parse_ui_date((item or {}).get("report_date")) or datetime.min.date()
    report_time = parse_ui_time((item or {}).get("report_time")) or datetime.min.time()
    updated_at_text = normalize_text((item or {}).get("updated_at"))
    try:
        updated_at = datetime.strptime(updated_at_text, "%d-%m-%Y %H:%M:%S")
    except ValueError:
        updated_at = datetime.min
    return (
        report_date,
        report_time,
        updated_at,
        int((item or {}).get("report_id") or 0),
    )


def get_task_report_schedule_timezone():
    return (
        normalize_timezone_name(lookup_timezone_by_zip(TASK_REPORT_SCHEDULE_ZIP_CODE))
        or TASK_REPORT_DEFAULT_TIMEZONE
    )


class TaskReportRowWidget(ctk.CTkFrame):
    def __init__(self, parent, page, on_click):
        super().__init__(
            parent,
            fg_color=CARD_ALT_BG,
            corner_radius=10,
            border_width=1,
            border_color="#e0c79d",
        )
        self.page = page
        self.on_click = on_click
        self.report_id = None
        self.selected = False
        self.alt = False

        self.cell_frames = {}
        self.cell_labels = {}
        for index, column in enumerate(REPORT_TABLE_COLUMNS):
            self.grid_columnconfigure(index, minsize=column["width"], weight=0)
            key = column["key"]
            self.cell_frames[key] = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
            self.cell_frames[key].grid(row=0, column=index, sticky="nsew")
            if key in REPORT_TABLE_STRICT_TEXT_COLUMNS:
                self.cell_frames[key].configure(width=column["width"])
            self.cell_frames[key].grid_columnconfigure(0, weight=1)
            self.cell_labels[key] = self._make_label(
                key,
                wraplength=column["wraplength"],
                center=column.get("center", False),
            )
        self.grid_columnconfigure(len(REPORT_TABLE_COLUMNS), weight=1)

        for widget in (self, *self.cell_frames.values(), *self.cell_labels.values()):
            widget.bind("<Button-1>", self._handle_click)
            widget.bind("<MouseWheel>", self.page._on_report_list_mousewheel, add="+")
            widget.bind("<Button-4>", self.page._on_report_list_mousewheel, add="+")
            widget.bind("<Button-5>", self.page._on_report_list_mousewheel, add="+")

        self.apply_column_widths(getattr(self.page, "report_table_column_widths", []))

    def _make_label(self, key, wraplength=180, center=False):
        container = self.cell_frames[key]
        if key == "processing":
            badge_wrap = ctk.CTkFrame(container, fg_color="transparent", corner_radius=0)
            badge_wrap.grid(row=0, column=0, sticky="nsew", padx=REPORT_TABLE_CELL_PADX, pady=REPORT_TABLE_ROW_PADY)
            badge_wrap.grid_rowconfigure(0, weight=1)
            badge_wrap.grid_columnconfigure(0, weight=1)
            label = ctk.CTkLabel(
                badge_wrap,
                text="",
                font=("Segoe UI", REPORT_TABLE_ROW_FONT_SIZE, "bold"),
                text_color=PROCESSING_COLOR,
                fg_color=PROCESSING_BG,
                corner_radius=999,
                width=REPORT_TABLE_BADGE_WIDTH,
                height=REPORT_TABLE_BADGE_HEIGHT,
                anchor="center",
                justify="center",
            )
            label.grid(row=0, column=0)
            return label

        label_padx = (0, REPORT_TABLE_CELL_PADX) if key in REPORT_TABLE_STRICT_TEXT_COLUMNS else REPORT_TABLE_CELL_PADX
        label = ctk.CTkLabel(
            container,
            text="",
            font=("Segoe UI", REPORT_TABLE_ROW_FONT_SIZE, "bold"),
            text_color=self.page.text_dark,
            anchor="center" if center else "w",
            justify="center" if center else "left",
            wraplength=wraplength,
        )
        label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=label_padx,
            pady=REPORT_TABLE_ROW_PADY,
        )
        return label

    def _handle_click(self, _event=None):
        if self.report_id is not None:
            self.on_click(self.report_id)

    def measure_height(self):
        max_height = REPORT_TABLE_MIN_ROW_HEIGHT

        for column in REPORT_TABLE_COLUMNS:
            key = column["key"]
            if key == "processing":
                cell_height = REPORT_TABLE_MIN_ROW_HEIGHT
            else:
                cell_height = int(self.cell_labels[key].winfo_reqheight() or 0) + (REPORT_TABLE_ROW_PADY * 2)
            max_height = max(max_height, cell_height)

        return max_height

    def apply_column_widths(self, column_widths):
        if not column_widths or len(column_widths) != len(REPORT_TABLE_COLUMNS):
            return

        for index, column in enumerate(REPORT_TABLE_COLUMNS):
            width = max(int(column_widths[index]), 1)
            self.grid_columnconfigure(index, minsize=width, weight=0)
            if column["key"] in REPORT_TABLE_STRICT_TEXT_COLUMNS:
                content_width = max(width - (REPORT_TABLE_CELL_PADX * 2) - 6, 24)
                self.cell_frames[column["key"]].configure(width=width)
                self.cell_labels[column["key"]].configure(
                    width=content_width,
                    wraplength=content_width,
                )
            elif column["key"] != "processing":
                self.cell_labels[column["key"]].configure(
                    wraplength=max(width - (REPORT_TABLE_CELL_PADX * 2) - 6, 24)
                )

    def update_report(self, item, alt=False, selected=False):
        payload = item or {}
        self.report_id = payload.get("report_id")
        self.alt = bool(alt)
        self.selected = bool(selected)

        for column in REPORT_TABLE_COLUMNS:
            value = normalize_text(payload.get(column["key"]))
            if column["key"] in {"processing", "technician_display_name"}:
                value = value or "-"
            self.cell_labels[column["key"]].configure(text=value)

        self._apply_theme()

    def set_selected(self, selected):
        self.selected = bool(selected)
        self._apply_theme()

    def _apply_theme(self):
        bg_color = CARD_SELECTED_BG if self.selected else (CARD_BG if self.alt else CARD_ALT_BG)
        self.configure(fg_color=bg_color)

        common_text_color = self.page.text_dark
        for key, label in self.cell_labels.items():
            if key == "processing":
                continue
            label.configure(text_color=common_text_color)

        self.cell_labels["processing"].configure(
            fg_color=PROCESSING_BG,
            text_color=PROCESSING_COLOR,
            corner_radius=999,
            width=REPORT_TABLE_BADGE_WIDTH,
            height=REPORT_TABLE_BADGE_HEIGHT,
        )


class TaskReportPage(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        title,
        text_dark,
        text_muted,
        panel_bg,
        panel_inner,
        border,
        border_soft,
        current_user=None,
        current_username="",
        current_display_name="",
    ):
        super().__init__(
            parent,
            fg_color=panel_bg,
            corner_radius=22,
            border_width=1,
            border_color=border,
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.title = title
        self.text_dark = text_dark
        self.text_muted = text_muted
        self.panel_bg = panel_bg
        self.panel_inner = panel_inner
        self.border = border
        self.border_soft = border_soft

        self.current_user = current_user or {}
        self.current_username = normalize_text(current_username) or normalize_text(self.current_user.get("username"))
        self.current_display_name = (
            normalize_text(current_display_name)
            or normalize_text(self.current_user.get("full_name"))
            or self.current_username
        )
        self.report_schedule_timezone = get_task_report_schedule_timezone()

        self.service = TaskReportService()
        self.task_service = TaskService()
        self.report_items = []
        self.filtered_report_items = []
        self.report_row_widgets = {}
        self.visible_report_widget_ids = []
        self.selected_report_id = None
        self.active_report = None
        self.search_after_id = None
        self.load_reports_request_id = 0
        self.loaded_from_date = ""
        self.loaded_to_date = ""
        self.is_reports_loading = False
        self.is_saving = False
        self.report_date_value = ""
        self.report_time_value = ""
        self.report_clock_after_id = None
        self.filter_anchor_date_value = ""
        self.filter_from_date_value = ""
        self.filter_to_date_value = ""
        self.filter_popup = None
        self.filter_popup_target = "anchor"
        self.filter_popup_month = self.get_report_schedule_now().replace(day=1)
        self.filter_calendar_canvas = None
        self.filter_month_label = None
        self.filter_calendar_hits = []
        self.pending_filter_date = ""
        self.selected_processing = PROCESSING_OPTIONS[0]
        self.processing_buttons = {}
        self.report_tree_syncing = False
        self.table_header_sync_job = None
        self.report_table_column_widths = []
        self.table_header_labels = {}
        self.report_row_heights = []
        self.report_row_offsets = []
        self.report_virtual_total_height = 0
        self.report_visible_assignments = []
        self.virtual_refresh_job = None
        self.report_row_measure_job = None
        self.report_canvas_width = 1
        self.report_canvas_height = 1
        self.form_scrollbar_visible = False
        self.form_mousewheel_bound_widgets = set()
        self.follow_task_popup = None
        self.follow_task_popup_widgets = {}
        self.follow_task_handoff_options = [{"username": "", "display_name": "Tech Team", "type": "TEAM"}]
        self.follow_task_selected_handoff = "Tech Team"
        self.follow_task_deadline_date = ""
        self.follow_task_deadline_time = ""
        self.follow_task_deadline_period = "AM"
        self.follow_task_deadline_popup = None
        self.follow_task_deadline_month = datetime.now().replace(day=1)
        self.follow_task_deadline_hits = []
        self.follow_task_icon_ref = None
        self.follow_task_bitmap_icon_path = ""
        self.follow_task_logo_image = None

        self._build_ui()
        self.reset_filter_defaults()
        self.reset_form_defaults()
        self.start_report_clock()
        self.load_reports(force=False)

    def _build_ui(self):
        content = ctk.CTkFrame(
            self,
            fg_color=self.panel_inner,
            corner_radius=18,
            border_width=1,
            border_color=self.border_soft,
        )
        content.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        content.grid_columnconfigure(0, weight=0, minsize=REPORT_FORM_PANEL_WIDTH)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=0)
        content.grid_rowconfigure(1, weight=1)

        self.form_card = ctk.CTkFrame(
            content,
            fg_color=FORM_CARD_BG,
            corner_radius=16,
            border_width=1,
            border_color=FORM_CARD_BORDER,
        )
        self.form_card.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(14, 6), pady=(10, 14))
        self.form_card.configure(width=REPORT_FORM_PANEL_WIDTH)
        self.form_card.grid_propagate(False)
        self.form_card.grid_columnconfigure(0, weight=1)
        self.form_card.grid_rowconfigure(0, weight=1)

        self.form_scroll_canvas = tk.Canvas(
            self.form_card,
            highlightthickness=0,
            bd=0,
            bg=FORM_CARD_BG,
            yscrollincrement=24,
        )
        self.form_scroll_canvas.grid(row=0, column=0, sticky="nsew")

        self.form_scrollbar = ctk.CTkScrollbar(
            self.form_card,
            orientation="vertical",
            width=REPORT_FORM_SCROLLBAR_WIDTH,
            command=self.form_scroll_canvas.yview,
            fg_color=FORM_CARD_BG,
            button_color="#c58b42",
            button_hover_color="#d49a50",
        )
        self.form_scroll_canvas.configure(yscrollcommand=self._on_form_scrollbar_set)

        self.form_content = ctk.CTkFrame(self.form_scroll_canvas, fg_color="transparent")
        self.form_content_window = self.form_scroll_canvas.create_window(
            (0, 0),
            window=self.form_content,
            anchor="nw",
        )
        self.form_content.grid_columnconfigure(0, weight=1)
        self.form_content.bind("<Configure>", self._on_form_content_configure, add="+")
        self.form_scroll_canvas.bind("<Configure>", self._on_form_canvas_configure, add="+")
        self.form_scroll_canvas.bind("<MouseWheel>", self._on_form_mousewheel, add="+")
        self.form_scroll_canvas.bind("<Button-4>", self._on_form_mousewheel, add="+")
        self.form_scroll_canvas.bind("<Button-5>", self._on_form_mousewheel, add="+")

        form_parent = self.form_content
        self._create_card_header(
            form_parent,
            row=0,
            text="Daily Case Note",
            subtitle="",
            badge_text="ENTRY",
            accent_color=FORM_ACCENT,
            badge_text_color="#fff7e8",
            columnspan=1,
            compact=True,
        )

        self.merchant_entry = self._create_labeled_entry(form_parent, 1, 0, "MERCHANT", "NAIL TOPIA 48327")
        self.merchant_entry.configure(font=("Segoe UI", 12, "bold"))
        self.caller_phone_entry = self._create_labeled_entry(
            form_parent,
            2,
            0,
            "CALLER PHONE",
            "(000) 000-0000",
            width=160,
        )
        self.caller_phone_entry.configure(font=("Segoe UI", 12, "bold"))
        self.caller_phone_entry.bind("<KeyRelease>", self.on_phone_input)
        self.problem_box = self._create_labeled_textbox(
            form_parent,
            3,
            "PROBLEM",
            height=64,
            column=0,
            columnspan=1,
        )
        self.solution_box = self._create_labeled_textbox(
            form_parent,
            4,
            "SOLUTION",
            height=64,
            column=0,
            columnspan=1,
        )
        self.processing_wrap = self._create_processing_buttons(form_parent, 5, 0)
        self.report_datetime_value_label, self.report_datetime_hint = self._create_labeled_display_value(
            form_parent,
            6,
            0,
            "DATE & TIME",
            width=220,
            compact=True,
        )
        self.technician_value_label, self.technician_hint_label = self._create_labeled_display_value(
            form_parent,
            7,
            0,
            "TECHNICIANS",
            width=180,
            hint_text="Saved using your configured Display Name from schedule setup.",
            compact=True,
        )
        self.technician_value_label.configure(font=("Segoe UI", 12, "bold"))
        self.sync_current_technician_display()

        action_row = ctk.CTkFrame(form_parent, fg_color="transparent")
        action_row.grid(row=8, column=0, columnspan=1, sticky="ew", padx=18, pady=(2, 10))
        action_row.grid_columnconfigure(0, weight=1)

        button_row = ctk.CTkFrame(action_row, fg_color="transparent")
        button_row.grid(row=0, column=0, sticky="w")

        self.save_button = ctk.CTkButton(
            button_row,
            text="Save Report",
            width=110,
            height=34,
            corner_radius=12,
            fg_color="#8b5e1a",
            hover_color="#a06c1e",
            text_color="#fff7e8",
            font=("Segoe UI", 11, "bold"),
            command=self.on_save,
        )
        self.save_button.pack(side="left", padx=(0, 8))

        self.update_button = ctk.CTkButton(
            button_row,
            text="Update",
            width=88,
            height=34,
            corner_radius=12,
            fg_color="#3a2d25",
            hover_color="#4b3b31",
            text_color="#f5efe6",
            font=("Segoe UI", 11, "bold"),
            command=self.on_update,
        )
        self.update_button.pack(side="left", padx=(0, 8))
        self.update_button.pack_forget()

        self.new_report_button = ctk.CTkButton(
            button_row,
            text="New Report",
            width=108,
            height=34,
            corner_radius=12,
            fg_color="#5a483d",
            hover_color="#6a5548",
            text_color="#f5efe6",
            font=("Segoe UI", 11, "bold"),
            command=self.start_new_report,
        )
        self.new_report_button.pack(side="left", padx=(0, 8))

        self.delete_button = ctk.CTkButton(
            button_row,
            text="Delete",
            width=88,
            height=34,
            corner_radius=12,
            fg_color="#9f2d2d",
            hover_color="#ba3a3a",
            text_color="#fff7f0",
            font=("Segoe UI", 11, "bold"),
            command=self.on_delete,
        )
        self.delete_button.pack(side="left", padx=(0, 8))

        self.feedback_label = ctk.CTkLabel(
            action_row,
            text="",
            width=REPORT_FORM_PANEL_WIDTH - 54,
            wraplength=REPORT_FORM_PANEL_WIDTH - 54,
            font=("Segoe UI", 11, "bold"),
            text_color=self.text_muted,
            anchor="w",
            justify="left",
        )
        self.feedback_label.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self._bind_form_mousewheel_tree(self.form_card)

        self.filter_card = ctk.CTkFrame(
            content,
            fg_color=FILTER_CARD_BG,
            corner_radius=16,
            border_width=1,
            border_color=FILTER_CARD_BORDER,
        )
        self.filter_card.grid(row=0, column=1, sticky="ew", padx=(6, 14), pady=(10, 10))
        self.filter_card.grid_columnconfigure(0, weight=1)

        self._create_card_header(
            self.filter_card,
            row=0,
            text="Date Filter",
            subtitle="Choose the period you want to browse before loading reports.",
            badge_text="BROWSE",
            accent_color=FILTER_ACCENT,
            badge_text_color="#1f160f",
        )

        filter_top = ctk.CTkFrame(self.filter_card, fg_color="transparent")
        filter_top.grid(row=1, column=0, sticky="ew", padx=18, pady=(4, 8))
        filter_top.grid_columnconfigure(2, weight=1)

        self.filter_mode_button = ctk.CTkSegmentedButton(
            filter_top,
            values=FILTER_MODES,
            height=34,
            fg_color="#5a483d",
            selected_color="#c58b42",
            selected_hover_color="#d49a50",
            unselected_color="#6a5548",
            unselected_hover_color="#7a6558",
            text_color="#f5efe6",
            font=("Segoe UI", 11, "bold"),
            command=self.on_filter_mode_change,
        )
        self.filter_mode_button.grid(row=0, column=0, sticky="w")
        self.filter_mode_button.set("Daily")

        self.filter_prev_button = ctk.CTkButton(
            filter_top,
            text="<<",
            width=42,
            height=34,
            corner_radius=10,
            fg_color="#3a2d25",
            hover_color="#4b3b31",
            text_color="#f5efe6",
            font=("Segoe UI", 11, "bold"),
            command=lambda: self.shift_filter_period(-1),
        )
        self.filter_prev_button.grid(row=0, column=1, sticky="w", padx=(10, 6))

        self.filter_value_button = ctk.CTkButton(
            filter_top,
            text="Choose date",
            height=36,
            corner_radius=12,
            fg_color=self.panel_inner,
            hover_color="#f6ead7",
            border_width=1,
            border_color="#d1b180",
            text_color=self.text_dark,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
            command=lambda: self.open_filter_date_popup("anchor"),
        )
        self.filter_value_button.grid(row=0, column=2, sticky="ew", padx=(0, 8))

        self.filter_range_wrap = ctk.CTkFrame(filter_top, fg_color="transparent")
        self.filter_range_wrap.grid(row=0, column=2, sticky="ew", padx=(0, 8))
        self.filter_range_wrap.grid_columnconfigure(0, weight=1)
        self.filter_range_wrap.grid_columnconfigure(1, weight=1)

        self.filter_from_button = ctk.CTkButton(
            self.filter_range_wrap,
            text="From date",
            height=36,
            corner_radius=12,
            fg_color=self.panel_inner,
            hover_color="#f6ead7",
            border_width=1,
            border_color="#d1b180",
            text_color=self.text_dark,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
            command=lambda: self.open_filter_date_popup("from"),
        )
        self.filter_from_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.filter_to_button = ctk.CTkButton(
            self.filter_range_wrap,
            text="To date",
            height=36,
            corner_radius=12,
            fg_color=self.panel_inner,
            hover_color="#f6ead7",
            border_width=1,
            border_color="#d1b180",
            text_color=self.text_dark,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
            command=lambda: self.open_filter_date_popup("to"),
        )
        self.filter_to_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.filter_next_button = ctk.CTkButton(
            filter_top,
            text=">>",
            width=42,
            height=34,
            corner_radius=10,
            fg_color="#3a2d25",
            hover_color="#4b3b31",
            text_color="#f5efe6",
            font=("Segoe UI", 11, "bold"),
            command=lambda: self.shift_filter_period(1),
        )
        self.filter_next_button.grid(row=0, column=3, sticky="w", padx=(0, 8))

        self.today_button = ctk.CTkButton(
            filter_top,
            text="Today",
            width=88,
            height=34,
            corner_radius=10,
            fg_color="#3a2d25",
            hover_color="#4b3b31",
            text_color="#f5efe6",
            font=("Segoe UI", 11, "bold"),
            command=self.on_set_today_filter,
        )
        self.today_button.grid(row=0, column=4, sticky="w", padx=(0, 8))

        self.apply_filter_button = ctk.CTkButton(
            filter_top,
            text="Load",
            width=88,
            height=34,
            corner_radius=10,
            fg_color="#8b5e1a",
            hover_color="#a06c1e",
            text_color="#fff7e8",
            font=("Segoe UI", 11, "bold"),
            command=lambda: self.load_reports(force=True),
        )
        self.apply_filter_button.grid(row=0, column=5, sticky="e")

        self.filter_picker_hint_label = ctk.CTkLabel(
            filter_top,
            text="",
            font=("Segoe UI", 10),
            text_color=self.text_muted,
            anchor="w",
            justify="left",
        )
        self.filter_picker_hint_label.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(8, 0))

        filter_bottom = ctk.CTkFrame(self.filter_card, fg_color="transparent")
        filter_bottom.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))
        filter_bottom.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            filter_bottom,
            text="SEARCH",
            font=("Segoe UI", 12, "bold"),
            text_color=self.text_dark,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.search_entry = ctk.CTkEntry(
            filter_bottom,
            height=36,
            placeholder_text="Merchant / Problem / Solution / Status",
            fg_color=self.panel_inner,
            border_color="#d1b180",
            text_color=self.text_dark,
        )
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", self.on_search_key_release)

        self.clear_search_button = ctk.CTkButton(
            filter_bottom,
            text="Clear Search",
            width=110,
            height=36,
            corner_radius=10,
            fg_color="#3a2d25",
            hover_color="#4b3b31",
            text_color="#f5efe6",
            font=("Segoe UI", 11, "bold"),
            command=self.clear_search,
        )
        self.clear_search_button.grid(row=0, column=2, sticky="e", padx=(0, 8))

        self.refresh_button = ctk.CTkButton(
            filter_bottom,
            text="Refresh",
            width=88,
            height=36,
            corner_radius=10,
            fg_color="#8b5e1a",
            hover_color="#a06c1e",
            text_color="#fff7e8",
            font=("Segoe UI", 11, "bold"),
            command=lambda: self.load_reports(force=True),
        )
        self.refresh_button.grid(row=0, column=3, sticky="e")

        self.export_button = ctk.CTkButton(
            filter_bottom,
            text="Export Excel",
            width=110,
            height=36,
            corner_radius=10,
            fg_color="#0f766e",
            hover_color="#115e59",
            text_color="#ffffff",
            font=("Segoe UI", 11, "bold"),
            command=self.export_visible_reports,
        )
        self.export_button.grid(row=0, column=4, sticky="e", padx=(8, 0))

        self.filter_summary_label = ctk.CTkLabel(
            self.filter_card,
            text="",
            font=("Segoe UI", 10),
            text_color=self.text_muted,
            anchor="w",
            justify="left",
        )
        self.filter_summary_label.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 12))

        self.table_card = ctk.CTkFrame(
            content,
            fg_color=TABLE_CARD_BG,
            corner_radius=16,
            border_width=1,
            border_color=TABLE_CARD_BORDER,
        )
        self.table_card.grid(row=1, column=1, sticky="nsew", padx=(6, 14), pady=(0, 14))
        self.table_card.grid_columnconfigure(0, weight=1)
        self.table_card.grid_rowconfigure(3, weight=1)

        self._create_card_header(
            self.table_card,
            row=0,
            text="Saved Reports",
            subtitle="",
            badge_text="HISTORY",
            accent_color=TABLE_ACCENT,
            badge_text_color="#fff7e8",
        )

        table_title_row = ctk.CTkFrame(self.table_card, fg_color="transparent")
        table_title_row.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 6))
        table_title_row.grid_columnconfigure(0, weight=1)

        self.list_status_label = ctk.CTkLabel(
            table_title_row,
            text="",
            font=("Segoe UI", 11),
            text_color=self.text_muted,
            anchor="e",
            justify="right",
        )
        self.list_status_label.grid(row=0, column=1, sticky="e")

        self.list_body = ctk.CTkFrame(
            self.table_card,
            fg_color=MUTED_BG,
            corner_radius=12,
            border_width=1,
            border_color=self.border_soft,
        )
        self.list_body.grid(row=3, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self.list_body.grid_columnconfigure(0, weight=1)
        self.list_body.grid_columnconfigure(1, weight=0)
        self.list_body.grid_rowconfigure(0, weight=1)
        self.list_body.grid_rowconfigure(1, weight=0)

        self._setup_report_list_style()

        self.report_tree = ttk.Treeview(
            self.list_body,
            columns=[column["key"] for column in REPORT_LIST_COLUMNS],
            show="headings",
            selectmode="browse",
            style="TaskReport.Treeview",
        )
        self.report_tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 0))

        for column in REPORT_LIST_COLUMNS:
            self.report_tree.heading(
                column["key"],
                text=column["label"],
                anchor=column.get("heading_anchor", "center"),
            )
            self.report_tree.column(
                column["key"],
                width=column["width"],
                minwidth=column["width"] if column["key"] != "problem" else 240,
                anchor=column["anchor"],
                stretch=(column["key"] == "problem"),
            )

        self.report_tree.tag_configure("even", background=CARD_BG)
        self.report_tree.tag_configure("odd", background=CARD_ALT_BG)

        self.report_tree_scrollbar = ttk.Scrollbar(
            self.list_body,
            orient="vertical",
            command=self.report_tree.yview,
        )
        self.report_tree_scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=(8, 0))
        self.report_tree_x_scrollbar = ttk.Scrollbar(
            self.list_body,
            orient="horizontal",
            command=self.report_tree.xview,
        )
        self.report_tree_x_scrollbar.grid(row=1, column=0, sticky="ew", padx=(8, 0), pady=(0, 8))
        self.report_tree_scroll_corner = ctk.CTkFrame(
            self.list_body,
            fg_color=MUTED_BG,
            width=18,
            height=18,
            corner_radius=0,
        )
        self.report_tree_scroll_corner.grid(row=1, column=1, sticky="nsew", padx=(0, 8), pady=(0, 8))
        self.report_tree.configure(
            yscrollcommand=self.report_tree_scrollbar.set,
            xscrollcommand=self.report_tree_x_scrollbar.set,
        )
        self.report_tree.bind("<<TreeviewSelect>>", self.on_report_tree_select, add="+")
        self.report_tree.bind("<Button-1>", self.on_report_tree_click, add="+")
        self._bind_report_tree_mousewheel(self.report_tree)
        self._bind_report_tree_mousewheel(self.report_tree_scrollbar)
        self._bind_report_tree_mousewheel(self.report_tree_x_scrollbar)
        self._bind_report_tree_mousewheel(self.list_body)

        self.empty_label = ctk.CTkLabel(
            self.list_body,
            text="Loading reports...",
            font=("Segoe UI", 12),
            text_color=self.text_muted,
            anchor="center",
            justify="center",
        )
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self._bind_report_tree_mousewheel(self.empty_label)

        self.update_filter_inputs()
        self.update_form_mode()

    def _on_form_scrollbar_set(self, first, last):
        if not self._form_scroll_widgets_alive():
            return
        if hasattr(self, "form_scrollbar"):
            self.form_scrollbar.set(first, last)
        self.after_idle(self._update_form_scrollbar_visibility)

    def _bind_form_mousewheel_tree(self, widget):
        if widget is None:
            return

        self._bind_form_mousewheel_widget(widget)
        for attr_name in ("_entry", "_textbox", "_canvas", "_text_label", "_button", "_dropdown_button"):
            child = getattr(widget, attr_name, None)
            if child is not None:
                self._bind_form_mousewheel_widget(child)

        try:
            children = widget.winfo_children()
        except tk.TclError:
            children = []
        for child in children:
            self._bind_form_mousewheel_tree(child)

    def _bind_form_mousewheel_widget(self, widget):
        if widget is None:
            return

        widget_key = str(widget)
        if widget_key in self.form_mousewheel_bound_widgets:
            return
        self.form_mousewheel_bound_widgets.add(widget_key)

        try:
            widget.bind("<MouseWheel>", self._on_form_mousewheel, add="+")
            widget.bind("<Button-4>", self._on_form_mousewheel, add="+")
            widget.bind("<Button-5>", self._on_form_mousewheel, add="+")
        except tk.TclError:
            pass

    def _form_scroll_widgets_alive(self):
        canvas = getattr(self, "form_scroll_canvas", None)
        if canvas is None:
            return False
        try:
            return bool(canvas.winfo_exists())
        except tk.TclError:
            return False

    def _on_form_content_configure(self, _event=None):
        if not self._form_scroll_widgets_alive():
            return
        self.form_scroll_canvas.configure(scrollregion=self.form_scroll_canvas.bbox("all"))
        self.after_idle(self._update_form_scrollbar_visibility)

    def _on_form_canvas_configure(self, event=None):
        if not self._form_scroll_widgets_alive() or not hasattr(self, "form_content_window"):
            return
        width = max(int(getattr(event, "width", self.form_scroll_canvas.winfo_width()) or 1), 1)
        self.form_scroll_canvas.itemconfigure(self.form_content_window, width=width)
        self.after_idle(self._update_form_scrollbar_visibility)

    def _update_form_scrollbar_visibility(self):
        if not self._form_scroll_widgets_alive() or not hasattr(self, "form_scrollbar"):
            return

        canvas_height = max(int(self.form_scroll_canvas.winfo_height() or 0), 0)
        bbox = self.form_scroll_canvas.bbox("all")
        content_height = max(int((bbox[3] - bbox[1]) if bbox else 0), 0)
        needs_scroll = bool(canvas_height and content_height > canvas_height + 2)

        if needs_scroll and not self.form_scrollbar_visible:
            self.form_scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 4), pady=10)
            self.form_scrollbar_visible = True
            self.after_idle(self._on_form_content_configure)
            return

        if not needs_scroll and self.form_scrollbar_visible:
            self.form_scrollbar.grid_remove()
            self.form_scrollbar_visible = False
            self.form_scroll_canvas.yview_moveto(0)
            self.after_idle(self._on_form_content_configure)

    def _on_form_mousewheel(self, event):
        if not self.form_scrollbar_visible or not self._form_scroll_widgets_alive():
            return None

        if getattr(event, "num", None) == 4:
            scroll_units = -1
        elif getattr(event, "num", None) == 5:
            scroll_units = 1
        else:
            delta = getattr(event, "delta", 0)
            scroll_units = int(-delta / 120)
            if scroll_units == 0:
                scroll_units = -1 if delta > 0 else 1

        self.form_scroll_canvas.yview_scroll(scroll_units, "units")
        return "break"

    def _create_card_header(
        self,
        parent,
        row,
        text,
        subtitle="",
        badge_text="",
        accent_color="#c58b42",
        badge_text_color="#fff7e8",
        columnspan=1,
        compact=False,
    ):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(
            row=row,
            column=0,
            columnspan=columnspan,
            sticky="ew",
            padx=18,
            pady=(10, 8) if compact else (14, 10),
        )
        wrap.grid_columnconfigure(0, weight=1)

        accent_bar = ctk.CTkFrame(
            wrap,
            fg_color=accent_color,
            corner_radius=999,
            height=3 if compact else 4,
        )
        accent_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8 if compact else 10))

        ctk.CTkLabel(
            wrap,
            text=text,
            font=("Segoe UI", 15 if compact else 16, "bold"),
            text_color=self.text_dark,
        ).grid(row=1, column=0, sticky="w")

        if badge_text:
            ctk.CTkLabel(
                wrap,
                text=badge_text,
                fg_color=accent_color,
                corner_radius=999,
                text_color=badge_text_color,
                font=("Segoe UI", 9 if compact else 10, "bold"),
                padx=10,
                pady=3 if compact else 4,
            ).grid(row=1, column=1, sticky="e", padx=(12, 0))

        if subtitle:
            ctk.CTkLabel(
                wrap,
                text=subtitle,
                font=("Segoe UI", 10 if compact else 11),
                text_color=self.text_muted,
                justify="left",
            ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(3 if compact else 4, 0))

    def _create_labeled_entry(self, parent, row, column, label_text, placeholder, width=None):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=column, sticky="new", padx=18, pady=(0, 10))
        wrap.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            wrap,
            text=label_text,
            font=("Segoe UI", 11, "bold"),
            text_color=self.text_dark,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        entry = ctk.CTkEntry(
            wrap,
            height=36,
            width=width if width is not None else 220,
            placeholder_text=placeholder,
            fg_color=self.panel_inner,
            border_color="#d1b180",
            text_color=self.text_dark,
        )
        entry.grid(row=1, column=0, sticky="ew")
        return entry

    def _create_labeled_combo(self, parent, row, column, label_text, values, width=None):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=column, sticky="new", padx=18, pady=(0, 10))
        wrap.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            wrap,
            text=label_text,
            font=("Segoe UI", 11, "bold"),
            text_color=self.text_dark,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        combo = ctk.CTkComboBox(
            wrap,
            values=list(values or [""]),
            height=36,
            width=width if width is not None else 220,
            fg_color=self.panel_inner,
            border_color="#d1b180",
            button_color="#c58b42",
            button_hover_color="#d49a50",
            text_color=self.text_dark,
            dropdown_fg_color=self.panel_inner,
            dropdown_text_color=self.text_dark,
        )
        combo.grid(row=1, column=0, sticky="ew")
        return combo

    def _create_processing_buttons(self, parent, row, column):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=column, sticky="ew", padx=18, pady=(0, 10))
        wrap.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            wrap,
            text="PROCESSING",
            font=("Segoe UI", 11, "bold"),
            text_color=self.text_dark,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        button_row = ctk.CTkFrame(wrap, fg_color="transparent")
        button_row.grid(row=1, column=0, sticky="ew")
        for index in range(len(PROCESSING_OPTIONS)):
            button_row.grid_columnconfigure(index, weight=1, uniform="processing_status")

        self.processing_buttons = {}
        for index, status in enumerate(PROCESSING_OPTIONS):
            button = ctk.CTkButton(
                button_row,
                text=status,
                height=36,
                corner_radius=10,
                font=("Segoe UI", 11, "bold"),
                command=lambda value=status: self.select_processing(value),
            )
            button.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 6, 0))
            self.processing_buttons[status] = button

        self.select_processing(self.selected_processing)
        return wrap

    def select_processing(self, status):
        normalized = normalize_text(status).upper()
        if normalized not in PROCESSING_OPTIONS:
            normalized = PROCESSING_OPTIONS[0]
        self.selected_processing = normalized
        for name, button in getattr(self, "processing_buttons", {}).items():
            if name == normalized:
                button.configure(
                    fg_color="#8b5e1a",
                    hover_color="#a06c1e",
                    text_color="#fff7e8",
                    border_width=0,
                )
            else:
                button.configure(
                    fg_color="#f5ead8",
                    hover_color="#ead7b8",
                    text_color="#6b4f35",
                    border_width=1,
                    border_color="#d6b485",
                )

    def _create_labeled_display_value(
        self,
        parent,
        row,
        column,
        label_text,
        width=None,
        columnspan=1,
        hint_text="Auto-filled from the current system clock.",
        compact=False,
    ):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=column, columnspan=columnspan, sticky="new", padx=18, pady=(0, 8))
        wrap.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            wrap,
            text=label_text,
            font=("Segoe UI", 11, "bold"),
            text_color=self.text_dark,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        display_card = ctk.CTkFrame(
            wrap,
            fg_color=self.panel_inner,
            corner_radius=12,
            border_width=1,
            border_color="#d1b180",
        )
        display_card.grid(row=1, column=0, sticky="ew")
        display_card.grid_columnconfigure(0, weight=1)
        if width is not None:
            display_card.grid_propagate(False)
            display_card.configure(width=width, height=36 if compact else 44)

        value_label = ctk.CTkLabel(
            display_card,
            text="",
            font=("Segoe UI", 12, "bold"),
            text_color=self.text_dark,
            anchor="w",
            justify="left",
        )
        value_label.grid(row=0, column=0, sticky="ew", padx=12, pady=(5, 5) if compact else (9, 9))

        hint = ctk.CTkLabel(
            wrap,
            text=hint_text,
            font=("Segoe UI", 9 if compact else 10),
            text_color=self.text_muted,
            anchor="w",
            justify="left",
        )
        hint.grid(row=2, column=0, sticky="w", pady=(6, 0))
        return value_label, hint

    def _create_labeled_textbox(self, parent, row, label_text, height=90, column=0, columnspan=4):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=column, columnspan=columnspan, sticky="ew", padx=18, pady=(0, 8))
        wrap.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            wrap,
            text=label_text,
            font=("Segoe UI", 11, "bold"),
            text_color=self.text_dark,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        box = ctk.CTkTextbox(
            wrap,
            height=height,
            wrap="word",
            fg_color=self.panel_inner,
            border_color="#d1b180",
            border_width=1,
            text_color=self.text_dark,
            corner_radius=12,
            font=("Segoe UI", 12),
        )
        box.grid(row=1, column=0, sticky="ew")
        return box

    def _create_inline_entry(self, parent, row, column, placeholder, width=120):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=column, sticky="w", padx=(0, 8))

        entry = ctk.CTkEntry(
            wrap,
            width=width,
            height=34,
            placeholder_text=placeholder,
            fg_color=self.panel_inner,
            border_color="#d1b180",
            text_color=self.text_dark,
        )
        entry.pack(anchor="w")
        return entry

    def _setup_report_list_style(self):
        style = ttk.Style()
        try:
            if "clam" in style.theme_names() and style.theme_use() != "clam":
                style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "TaskReport.Treeview",
            background=MUTED_BG,
            fieldbackground=MUTED_BG,
            foreground=self.text_dark,
            borderwidth=0,
            relief="flat",
            rowheight=34,
            font=("Segoe UI", 10),
        )
        style.configure(
            "TaskReport.Treeview.Heading",
            background=HEADER_BG,
            foreground=HEADER_TEXT,
            borderwidth=0,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "TaskReport.Treeview",
            background=[("selected", CARD_SELECTED_BG)],
            foreground=[("selected", self.text_dark)],
        )
        style.map(
            "TaskReport.Treeview.Heading",
            background=[("active", "#1b4ba5")],
            foreground=[("active", HEADER_TEXT)],
        )

    def _format_report_tree_datetime(self, item):
        date_text = normalize_text((item or {}).get("report_date"))
        time_text = normalize_text((item or {}).get("report_time"))
        picker_time_text = format_picker_time(time_text)
        if date_text and picker_time_text:
            return f"{date_text}  {picker_time_text}"
        return date_text or time_text or "-"

    def _build_report_tree_values(self, item):
        payload = item or {}
        return (
            self._format_report_tree_datetime(payload),
            normalize_text(payload.get("merchant")) or "-",
            normalize_text(payload.get("caller_phone")) or "-",
            normalize_text(payload.get("processing")) or "-",
            normalize_text(payload.get("technician_display_name")) or "-",
            build_single_line_preview(payload.get("problem")),
            build_single_line_preview(payload.get("solution")),
        )

    def _clear_report_tree(self):
        tree = getattr(self, "report_tree", None)
        if tree is None:
            return
        children = tree.get_children()
        if children:
            tree.delete(*children)

    def _set_report_tree_empty_state(self, text=""):
        if not hasattr(self, "empty_label"):
            return
        if text:
            self.empty_label.configure(text=text)
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
            self.empty_label.lift()
            return
        self.empty_label.place_forget()

    def _sync_report_tree_selection(self, report_id=None):
        tree = getattr(self, "report_tree", None)
        if tree is None:
            return

        self.report_tree_syncing = True
        try:
            current_selection = tree.selection()
            if current_selection:
                tree.selection_remove(current_selection)
            if report_id is None:
                tree.focus("")
                return

            item_id = str(report_id)
            if tree.exists(item_id):
                tree.selection_set(item_id)
                tree.focus(item_id)
                tree.see(item_id)
        finally:
            self.report_tree_syncing = False

    def on_report_tree_select(self, _event=None):
        if self.report_tree_syncing:
            return

        selection = getattr(self, "report_tree", None)
        if selection is None:
            return

        selected_items = self.report_tree.selection()
        if not selected_items:
            return

        try:
            report_id = int(selected_items[0])
        except (TypeError, ValueError):
            return

        if self.selected_report_id == report_id and self.active_report is not None:
            return
        self.select_report(report_id, allow_toggle=False)

    def on_report_tree_click(self, event):
        tree = getattr(self, "report_tree", None)
        if tree is None:
            return None

        row_id = tree.identify_row(event.y)
        if not row_id:
            if self.selected_report_id is not None and self.active_report is not None:
                self.start_new_report()
                return "break"
            return None

        try:
            report_id = int(row_id)
        except (TypeError, ValueError):
            return None

        if self.selected_report_id == report_id and self.active_report is not None:
            self.start_new_report()
            return "break"

        return None

    def _bind_report_tree_mousewheel(self, widget):
        if widget is None:
            return
        widget.bind("<MouseWheel>", self._on_report_tree_mousewheel, add="+")
        widget.bind("<Button-4>", self._on_report_tree_mousewheel, add="+")
        widget.bind("<Button-5>", self._on_report_tree_mousewheel, add="+")

    def _on_report_tree_mousewheel(self, event):
        tree = getattr(self, "report_tree", None)
        if tree is None:
            return "break"

        if getattr(event, "num", None) == 4:
            scroll_units = -1
        elif getattr(event, "num", None) == 5:
            scroll_units = 1
        else:
            delta = int(getattr(event, "delta", 0) or 0)
            if delta == 0:
                return "break"
            scroll_units = int(-delta / 120)
            if scroll_units == 0:
                scroll_units = -1 if delta > 0 else 1

        tree.yview_scroll(scroll_units, "units")
        return "break"

    def _build_table_header(self):
        self.table_header_shell = ctk.CTkFrame(
            self.table_card,
            fg_color="transparent",
            corner_radius=0,
        )
        self.table_header_shell.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 8))
        self.table_header_shell.grid_columnconfigure(0, weight=1)
        self.table_header_shell.grid_columnconfigure(1, minsize=REPORT_TABLE_SCROLLBAR_WIDTH + 16, weight=0)

        self.table_header = ctk.CTkFrame(
            self.table_header_shell,
            fg_color=HEADER_BG,
            corner_radius=10,
            border_width=1,
            border_color="#1b4ba5",
        )
        self.table_header.grid(row=0, column=0, sticky="ew")

        for index, column in enumerate(REPORT_TABLE_COLUMNS):
            self.table_header.grid_columnconfigure(index, minsize=column["width"], weight=0)
            self.table_header_labels[column["key"]] = ctk.CTkLabel(
                self.table_header,
                text=column["label"],
                font=("Segoe UI", REPORT_TABLE_HEADER_FONT_SIZE, "bold"),
                text_color=HEADER_TEXT,
                anchor="center" if column.get("center", False) else "w",
                justify="center" if column.get("center", False) else "left",
            )
            if column["key"] in REPORT_TABLE_STRICT_TEXT_COLUMNS:
                self.table_header_labels[column["key"]].configure(
                    width=max(column["width"] - (REPORT_TABLE_CELL_PADX * 2) - 6, 24)
                )
            self.table_header_labels[column["key"]].grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=REPORT_TABLE_CELL_PADX,
                pady=REPORT_TABLE_HEADER_PADY,
            )
        self.table_header.grid_columnconfigure(len(REPORT_TABLE_COLUMNS), weight=1)

        self.table_header_scrollbar_spacer = ctk.CTkFrame(
            self.table_header_shell,
            fg_color="transparent",
            corner_radius=0,
            width=REPORT_TABLE_SCROLLBAR_WIDTH + 16,
            height=1,
        )
        self.table_header_scrollbar_spacer.grid(row=0, column=1, sticky="ns")

    def _calculate_report_column_widths(self, total_width):
        usable_width = max(int(total_width), len(REPORT_TABLE_COLUMNS))
        column_count = len(REPORT_TABLE_COLUMNS)
        base_width = usable_width // column_count
        remainder = usable_width - (base_width * column_count)
        column_widths = [base_width for _ in range(column_count)]

        for index in range(remainder):
            column_widths[index] += 1

        return column_widths

    def _apply_report_column_widths(self, body_width):
        column_widths = self._calculate_report_column_widths(body_width)
        if column_widths == self.report_table_column_widths:
            return

        self.report_table_column_widths = column_widths

        for index, column in enumerate(REPORT_TABLE_COLUMNS):
            width = max(column_widths[index], 1)
            self.table_header.grid_columnconfigure(index, minsize=width, weight=0)
            header_content_width = max(width - (REPORT_TABLE_CELL_PADX * 2) - 6, 24)
            if column["key"] in REPORT_TABLE_STRICT_TEXT_COLUMNS:
                self.table_header_labels[column["key"]].configure(
                    width=header_content_width,
                    wraplength=header_content_width,
                )
            else:
                self.table_header_labels[column["key"]].configure(
                    wraplength=header_content_width
                )

        for widget in self.report_row_widgets.values():
            widget.apply_column_widths(column_widths)

        if self.filtered_report_items:
            self._rebuild_virtual_report_metrics()

    def _schedule_table_header_sync(self, _event=None):
        if self.table_header_sync_job is not None:
            return
        self.table_header_sync_job = self.after(10, self._sync_table_header_layout)

    def _sync_table_header_layout(self):
        self.table_header_sync_job = None

        if not hasattr(self, "table_header") or not hasattr(self, "list_canvas"):
            return

        body_width = max(int(self.list_canvas.winfo_width()), 1)
        if self.table_card.winfo_width() <= 1 or body_width <= 1:
            self.after(50, self._schedule_table_header_sync)
            return

        self.report_canvas_width = body_width
        self._apply_report_column_widths(
            max(body_width - (REPORT_TABLE_ROW_OUTER_PADX * 2), 1)
        )
        self._schedule_virtual_report_refresh()

    def _on_report_canvas_configure(self, event=None):
        if not hasattr(self, "list_canvas") or not hasattr(self, "list_viewport_window"):
            return
        width = max(int(getattr(event, "width", self.list_canvas.winfo_width()) or 1), 1)
        height = max(int(getattr(event, "height", self.list_canvas.winfo_height()) or 1), 1)
        self.report_canvas_width = width
        self.report_canvas_height = height
        self.list_canvas.itemconfigure(self.list_viewport_window, width=width)
        self._update_report_scrollregion()
        self._schedule_table_header_sync()

    def _on_report_scrollbar(self, *args):
        self.list_canvas.yview(*args)
        self._schedule_virtual_report_refresh()

    def _on_report_list_mousewheel(self, event):
        if not hasattr(self, "list_canvas"):
            return None

        if getattr(event, "num", None) == 4:
            self.list_canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            self.list_canvas.yview_scroll(1, "units")
        else:
            delta = getattr(event, "delta", 0)
            if delta == 0:
                return "break"
            self.list_canvas.yview_scroll(int(-delta / 120), "units")

        self._schedule_virtual_report_refresh()
        return "break"

    def _update_report_scrollregion(self):
        if not hasattr(self, "list_canvas") or not hasattr(self, "list_viewport"):
            return

        viewport_height = max(self.report_virtual_total_height, self.report_canvas_height, 1)
        viewport_width = max(self.report_canvas_width, 1)
        self.list_viewport.configure(width=viewport_width, height=viewport_height)
        self.list_canvas.itemconfigure(
            self.list_viewport_window,
            width=viewport_width,
            height=viewport_height,
        )
        self.list_canvas.configure(scrollregion=(0, 0, viewport_width, viewport_height))

    def _clamp_report_scroll_position(self):
        if not hasattr(self, "list_canvas"):
            return

        max_top = max(self.report_virtual_total_height - self.report_canvas_height, 0)
        current_top = max(int(self.list_canvas.canvasy(0) or 0), 0)
        if current_top <= max_top:
            return

        if self.report_virtual_total_height <= 0 or max_top <= 0:
            self.list_canvas.yview_moveto(0)
            return

        self.list_canvas.yview_moveto(min(max_top / float(self.report_virtual_total_height), 1.0))

    def _get_report_column_wraplength(self, column_key):
        for index, column in enumerate(REPORT_TABLE_COLUMNS):
            if column["key"] == column_key:
                width = (
                    self.report_table_column_widths[index]
                    if index < len(self.report_table_column_widths)
                    else column["width"]
                )
                return max(int(width) - (REPORT_TABLE_CELL_PADX * 2) - 6, 24)
        return 120

    def _estimate_wrapped_line_count(self, text, wraplength):
        content = normalize_text(text)
        if not content:
            return 1

        approx_chars_per_line = max(int(max(wraplength, 24) / 7), 1)
        line_count = 0
        for raw_line in content.splitlines() or [""]:
            wrapped = textwrap.wrap(
                raw_line,
                width=approx_chars_per_line,
                break_long_words=True,
                break_on_hyphens=False,
            )
            line_count += len(wrapped or [""])
        return max(line_count, 1)

    def _estimate_report_row_height(self, item):
        payload = item or {}
        max_height = REPORT_TABLE_BADGE_HEIGHT + (REPORT_TABLE_ROW_PADY * 2)

        for column in REPORT_TABLE_COLUMNS:
            key = column["key"]
            if key == "processing":
                continue

            value = normalize_text(payload.get(key))
            if key in {"processing", "technician_display_name"}:
                value = value or "-"
            line_count = self._estimate_wrapped_line_count(
                value,
                self._get_report_column_wraplength(key),
            )
            cell_height = (line_count * REPORT_TABLE_LINE_HEIGHT) + (REPORT_TABLE_ROW_PADY * 2)
            max_height = max(max_height, cell_height)

        return max(max_height, REPORT_TABLE_ESTIMATED_ROW_HEIGHT)

    def _rebuild_virtual_report_metrics(self):
        if not self.filtered_report_items:
            self.report_row_heights = []
            self.report_row_offsets = []
            self.report_virtual_total_height = 0
            self._update_report_scrollregion()
            self._clamp_report_scroll_position()
            return

        self.report_row_heights = [
            self._estimate_report_row_height(item)
            for item in self.filtered_report_items
        ]
        running_offset = 0
        self.report_row_offsets = []
        for row_height in self.report_row_heights:
            self.report_row_offsets.append(running_offset)
            running_offset += row_height + REPORT_TABLE_ROW_GAP_Y
        self.report_virtual_total_height = max(running_offset - REPORT_TABLE_ROW_GAP_Y, 0)
        self._update_report_scrollregion()
        self._clamp_report_scroll_position()

    def _ensure_report_row_pool(self, target_count):
        while len(self.report_row_widgets) < target_count:
            pool_index = len(self.report_row_widgets)
            self.report_row_widgets[pool_index] = TaskReportRowWidget(
                self.list_viewport,
                self,
                self.select_report,
            )

    def _hide_report_rows(self):
        self.report_visible_assignments = []
        for widget in self.report_row_widgets.values():
            widget.place_forget()

    def _schedule_virtual_report_refresh(self, _event=None):
        if self.virtual_refresh_job is not None:
            return
        self.virtual_refresh_job = self.after(10, self._refresh_virtual_report_rows)

    def _refresh_virtual_report_rows(self):
        self.virtual_refresh_job = None

        if not self.filtered_report_items:
            self._hide_report_rows()
            self._update_report_scrollregion()
            return

        canvas_height = max(int(self.list_canvas.winfo_height() or self.report_canvas_height or 1), 1)
        canvas_width = max(int(self.list_canvas.winfo_width() or self.report_canvas_width or 1), 1)
        viewport_top = max(int(self.list_canvas.canvasy(0)), 0)
        viewport_bottom = viewport_top + canvas_height
        buffered_top = max(viewport_top - REPORT_TABLE_VIEWPORT_BUFFER_PX, 0)
        buffered_bottom = viewport_bottom + REPORT_TABLE_VIEWPORT_BUFFER_PX

        start_index = max(bisect_right(self.report_row_offsets, buffered_top) - 1, 0)
        end_index = bisect_right(self.report_row_offsets, buffered_bottom)
        end_index = min(max(end_index, start_index + 1), len(self.filtered_report_items))

        visible_count = max(end_index - start_index, 0)
        self._ensure_report_row_pool(visible_count)
        self.report_visible_assignments = []

        row_width = max(canvas_width - (REPORT_TABLE_ROW_OUTER_PADX * 2), 1)
        for pool_index in range(visible_count):
            item_index = start_index + pool_index
            item = self.filtered_report_items[item_index]
            widget = self.report_row_widgets[pool_index]
            widget.apply_column_widths(self.report_table_column_widths)
            widget.update_report(
                item,
                alt=bool(item_index % 2),
                selected=(item.get("report_id") == self.selected_report_id),
            )
            widget.configure(
                width=row_width,
            )
            widget.place(
                x=REPORT_TABLE_ROW_OUTER_PADX,
                y=self.report_row_offsets[item_index],
            )
            self.report_visible_assignments.append((pool_index, item_index))

        for pool_index in range(visible_count, len(self.report_row_widgets)):
            self.report_row_widgets[pool_index].place_forget()

        self._schedule_report_row_measurement()

    def _schedule_report_row_measurement(self):
        if self.report_row_measure_job is not None:
            return
        self.report_row_measure_job = self.after_idle(self._measure_visible_report_rows)

    def _measure_visible_report_rows(self):
        self.report_row_measure_job = None
        changed = False

        for pool_index, item_index in self.report_visible_assignments:
            widget = self.report_row_widgets.get(pool_index)
            if widget is None:
                continue
            widget.update_idletasks()
            measured_height = max(widget.measure_height(), REPORT_TABLE_MIN_ROW_HEIGHT)
            if item_index < len(self.report_row_heights) and measured_height != self.report_row_heights[item_index]:
                self.report_row_heights[item_index] = measured_height
                changed = True

        if changed:
            running_offset = 0
            self.report_row_offsets = []
            for row_height in self.report_row_heights:
                self.report_row_offsets.append(running_offset)
                running_offset += row_height + REPORT_TABLE_ROW_GAP_Y
            self.report_virtual_total_height = max(running_offset - REPORT_TABLE_ROW_GAP_Y, 0)
            self._update_report_scrollregion()
            self._schedule_virtual_report_refresh()

    def reset_form_defaults(self):
        self.sync_live_report_datetime()
        self.set_entry_value(self.merchant_entry, "")
        self.set_entry_value(self.caller_phone_entry, "")
        self.problem_box.delete("1.0", "end")
        self.solution_box.delete("1.0", "end")
        self.select_processing(PROCESSING_OPTIONS[0])
        self.sync_current_technician_display()

    def get_report_schedule_now(self):
        return current_local_datetime(self.report_schedule_timezone)

    def get_report_schedule_today(self):
        return self.get_report_schedule_now().date()

    def get_current_technician_payload(self):
        username = normalize_text(self.current_username)
        return {
            "username": username,
            "display_name": "",
        }

    def sync_current_technician_display(self):
        technician = self.get_current_technician_payload()
        display_text = normalize_text(self.current_display_name) or technician.get("username") or "-"
        if hasattr(self, "technician_value_label"):
            self.technician_value_label.configure(text=display_text)
        if hasattr(self, "technician_hint_label"):
            self.technician_hint_label.configure(
                text=(
                    f"Saved using your configured Display Name from schedule setup "
                    f"({technician.get('username') or 'unknown user'})."
                )
            )

    def reset_filter_defaults(self):
        today_text = self.get_report_schedule_now().strftime("%d-%m-%Y")
        self.filter_mode_button.set("Daily")
        self.filter_anchor_date_value = today_text
        self.filter_from_date_value = today_text
        self.filter_to_date_value = today_text
        self.update_filter_inputs()

    def set_entry_value(self, entry, value):
        entry.delete(0, "end")
        if value:
            entry.insert(0, value)

    def update_filter_inputs(self):
        mode = self.filter_mode_button.get()
        if mode == "Range":
            self.filter_value_button.grid_remove()
            self.filter_range_wrap.grid()
        else:
            self.filter_range_wrap.grid_remove()
            self.filter_value_button.grid()
        self.update_filter_button_labels()

    def on_filter_mode_change(self, _value=None):
        today_text = self.get_report_schedule_now().strftime("%d-%m-%Y")
        mode = self.filter_mode_button.get()
        if mode == "Range":
            if not normalize_text(self.filter_from_date_value):
                self.filter_from_date_value = self.filter_anchor_date_value or today_text
            if not normalize_text(self.filter_to_date_value):
                self.filter_to_date_value = self.filter_anchor_date_value or today_text
        elif not normalize_text(self.filter_anchor_date_value):
            self.filter_anchor_date_value = self.filter_from_date_value or self.filter_to_date_value or today_text
        self.update_filter_inputs()

    def on_set_today_filter(self):
        today_text = self.get_report_schedule_now().strftime("%d-%m-%Y")
        self.filter_anchor_date_value = today_text
        self.filter_from_date_value = today_text
        self.filter_to_date_value = today_text
        self.update_filter_button_labels()
        self.load_reports(force=True)

    def shift_filter_period(self, direction):
        direction = -1 if int(direction) < 0 else 1
        today = self.get_report_schedule_today()
        mode = self.filter_mode_button.get()

        if mode == "Range":
            from_date = parse_ui_date(self.filter_from_date_value) or today
            to_date = parse_ui_date(self.filter_to_date_value) or from_date
            if from_date > to_date:
                from_date, to_date = to_date, from_date
            span_days = max(1, (to_date - from_date).days + 1)
            offset = timedelta(days=span_days * direction)
            from_date = from_date + offset
            to_date = to_date + offset
            self.filter_from_date_value = format_ui_date(from_date)
            self.filter_to_date_value = format_ui_date(to_date)
            self.filter_anchor_date_value = self.filter_from_date_value
        elif mode == "Daily":
            anchor_date = parse_ui_date(self.filter_anchor_date_value) or today
            anchor_date = anchor_date + timedelta(days=direction)
            anchor_text = format_ui_date(anchor_date)
            self.filter_anchor_date_value = anchor_text
            self.filter_from_date_value = anchor_text
            self.filter_to_date_value = anchor_text
        elif mode == "Week":
            anchor_date = parse_ui_date(self.filter_anchor_date_value) or today
            anchor_date = anchor_date + timedelta(days=7 * direction)
            anchor_text = format_ui_date(anchor_date)
            self.filter_anchor_date_value = anchor_text
            self.filter_from_date_value = anchor_text
            self.filter_to_date_value = anchor_text
        else:
            anchor_date = parse_ui_date(self.filter_anchor_date_value) or today
            anchor_date = shift_date_by_month(anchor_date, direction)
            anchor_text = format_ui_date(anchor_date)
            self.filter_anchor_date_value = anchor_text
            self.filter_from_date_value = anchor_text
            self.filter_to_date_value = anchor_text

        self.update_filter_button_labels()
        self.load_reports(force=True)

    def on_search_key_release(self, _event=None):
        if self.search_after_id:
            self.after_cancel(self.search_after_id)
        self.search_after_id = self.after(250, self.apply_local_filters)

    def clear_search(self):
        self.search_entry.delete(0, "end")
        self.apply_local_filters()

    def on_phone_input(self, _event=None):
        digits = re.sub(r"\D", "", self.caller_phone_entry.get())[:10]
        formatted = format_phone_digits(digits)
        self.caller_phone_entry.delete(0, "end")
        self.caller_phone_entry.insert(0, formatted)

    def get_filter_date_range(self):
        mode = self.filter_mode_button.get()
        if mode == "Range":
            from_date = parse_ui_date(self.filter_from_date_value)
            to_date = parse_ui_date(self.filter_to_date_value)
        else:
            anchor_date = parse_ui_date(self.filter_anchor_date_value)
            if anchor_date is None:
                return None, None, "Date must be DD-MM-YYYY."
            if mode == "Daily":
                from_date = anchor_date
                to_date = anchor_date
            elif mode == "Week":
                from_date = anchor_date - timedelta(days=anchor_date.weekday())
                to_date = from_date + timedelta(days=6)
            else:
                from_date = anchor_date.replace(day=1)
                if anchor_date.month == 12:
                    to_date = anchor_date.replace(month=12, day=31)
                else:
                    next_month = anchor_date.replace(month=anchor_date.month + 1, day=1)
                    to_date = next_month - timedelta(days=1)

        if from_date is None or to_date is None:
            return None, None, "Date must be DD-MM-YYYY."
        if from_date > to_date:
            return None, None, "From date must be before or equal to to date."
        return format_ui_date(from_date), format_ui_date(to_date), ""

    def update_filter_button_labels(self):
        mode = self.filter_mode_button.get()
        anchor_date = parse_ui_date(self.filter_anchor_date_value)
        from_date = parse_ui_date(self.filter_from_date_value)
        to_date = parse_ui_date(self.filter_to_date_value)

        if mode == "Range":
            self.filter_from_button.configure(
                text=f"From: {format_ui_date(from_date)}" if from_date else "From date"
            )
            self.filter_to_button.configure(
                text=f"To: {format_ui_date(to_date)}" if to_date else "To date"
            )
            if from_date and to_date:
                self.filter_picker_hint_label.configure(
                    text=f"Selected range: {format_ui_date(from_date)} -> {format_ui_date(to_date)}"
                )
            else:
                self.filter_picker_hint_label.configure(text="Choose a start date and an end date for the range.")
            return

        if mode == "Daily":
            self.filter_value_button.configure(
                text=f"Daily: {format_ui_date(anchor_date)}" if anchor_date else "Choose day"
            )
            self.filter_picker_hint_label.configure(
                text=f"Load only the selected day." if anchor_date else "Choose a day to load reports."
            )
            return

        if mode == "Week":
            if anchor_date:
                week_start = anchor_date - timedelta(days=anchor_date.weekday())
                week_end = week_start + timedelta(days=6)
                self.filter_value_button.configure(text=f"Week: {format_ui_date(week_start)}")
                self.filter_picker_hint_label.configure(
                    text=f"Week range: {format_ui_date(week_start)} -> {format_ui_date(week_end)}"
                )
            else:
                self.filter_value_button.configure(text="Choose week")
                self.filter_picker_hint_label.configure(text="Choose any date inside the week you want to load.")
            return

        if anchor_date:
            month_start = anchor_date.replace(day=1)
            if anchor_date.month == 12:
                month_end = anchor_date.replace(month=12, day=31)
            else:
                month_end = anchor_date.replace(month=anchor_date.month + 1, day=1) - timedelta(days=1)
            self.filter_value_button.configure(text=f"Month: {anchor_date.strftime('%B %Y')}")
            self.filter_picker_hint_label.configure(
                text=f"Month range: {format_ui_date(month_start)} -> {format_ui_date(month_end)}"
            )
        else:
            self.filter_value_button.configure(text="Choose month")
            self.filter_picker_hint_label.configure(text="Choose a month to load reports.")

    def is_item_in_loaded_range(self, item):
        item_date = parse_ui_date((item or {}).get("report_date"))
        loaded_from = parse_ui_date(self.loaded_from_date)
        loaded_to = parse_ui_date(self.loaded_to_date)
        if item_date is None or loaded_from is None or loaded_to is None:
            return False
        return loaded_from <= item_date <= loaded_to

    def set_feedback(self, text, is_error=False):
        self.feedback_label.configure(
            text=text,
            text_color=ERROR_TEXT if is_error else SUCCESS_TEXT if text else self.text_muted,
        )

    def set_list_status(self, text, is_error=False):
        self.list_status_label.configure(
            text=text,
            text_color=ERROR_TEXT if is_error else self.text_muted,
        )

    def update_filter_summary(self):
        if not self.loaded_from_date or not self.loaded_to_date:
            self.filter_summary_label.configure(text="No report range loaded yet.")
            return

        summary = f"Loaded range: {self.loaded_from_date} -> {self.loaded_to_date} | Showing {len(self.filtered_report_items)} report(s)"
        query = normalize_text(self.search_entry.get())
        if query:
            summary += f" | Local search: {query}"
        self.filter_summary_label.configure(text=summary)

    def export_visible_reports(self):
        if not self.filtered_report_items:
            messagebox.showinfo("Task Report", "No visible reports to export.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Export visible reports",
            defaultextension=".xlsx",
            initialfile=f"task_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
        )
        if not file_path:
            return

        headers = [column["label"] for column in REPORT_LIST_COLUMNS]
        rows = [list(self._build_report_tree_values(item)) for item in self.filtered_report_items]
        try:
            self._write_simple_xlsx(file_path, headers, rows)
        except Exception as exc:
            messagebox.showerror("Task Report", f"Unable to export Excel file.\n{exc}")
            return
        messagebox.showinfo("Task Report", f"Exported {len(rows)} visible report(s).\n{file_path}")

    def _write_simple_xlsx(self, file_path, headers, rows):
        def col_name(index):
            name = ""
            index += 1
            while index:
                index, remainder = divmod(index - 1, 26)
                name = chr(65 + remainder) + name
            return name

        def cell_xml(row_index, col_index, value, style_id=0):
            cell_ref = f"{col_name(col_index)}{row_index}"
            text = escape(str(value or ""))
            return f'<c r="{cell_ref}" t="inlineStr" s="{style_id}"><is><t>{text}</t></is></c>'

        sheet_rows = []
        sheet_rows.append(
            f'<row r="1">{"".join(cell_xml(1, col_index, value, style_id=1) for col_index, value in enumerate(headers))}</row>'
        )
        for row_index, row_values in enumerate(rows, start=2):
            sheet_rows.append(
                f'<row r="{row_index}">{"".join(cell_xml(row_index, col_index, value) for col_index, value in enumerate(row_values))}</row>'
            )

        column_widths = [18, 28, 18, 14, 18, 48, 48]
        cols_xml = "".join(
            f'<col min="{index + 1}" max="{index + 1}" width="{width}" customWidth="1"/>'
            for index, width in enumerate(column_widths)
        )
        dimension = f"A1:{col_name(max(len(headers) - 1, 0))}{max(len(rows) + 1, 1)}"
        sheet_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="{dimension}"/>
  <cols>{cols_xml}</cols>
  <sheetData>{''.join(sheet_rows)}</sheetData>
</worksheet>'''
        workbook_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Task Reports" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''
        workbook_rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
        root_rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''
        content_types_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>'''
        styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2"><font><sz val="11"/><name val="Segoe UI"/></font><font><b/><sz val="11"/><name val="Segoe UI"/></font></fonts>
  <fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"/></cellXfs>
</styleSheet>'''

        folder = os.path.dirname(file_path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with zipfile.ZipFile(file_path, "w", compression=zipfile.ZIP_DEFLATED) as workbook:
            workbook.writestr("[Content_Types].xml", content_types_xml)
            workbook.writestr("_rels/.rels", root_rels_xml)
            workbook.writestr("xl/workbook.xml", workbook_xml)
            workbook.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
            workbook.writestr("xl/worksheets/sheet1.xml", sheet_xml)
            workbook.writestr("xl/styles.xml", styles_xml)

    def dispatch_ui(self, callback):
        try:
            if not self.winfo_exists():
                return
            self.after(0, callback)
        except Exception:
            return

    def sync_live_report_datetime(self):
        if self.active_report and self.active_report.get("report_id"):
            return
        now = self.get_report_schedule_now()
        self.report_date_value = now.strftime("%d-%m-%Y")
        self.report_time_value = now.strftime("%H:%M:%S")
        self.update_report_datetime_display()

    def update_report_datetime_display(self):
        if not hasattr(self, "report_datetime_value_label"):
            return

        date_text = normalize_text(self.report_date_value)
        time_text = normalize_text(self.report_time_value)
        picker_time_text = format_picker_time(time_text)
        if date_text and picker_time_text:
            self.report_datetime_value_label.configure(text=f"{date_text}  {picker_time_text}")
            self.report_datetime_hint.configure(
                text=f"Auto-filled from company schedule time ({self.report_schedule_timezone})."
            )
            return
        if date_text:
            self.report_datetime_value_label.configure(text=date_text)
            self.report_datetime_hint.configure(
                text=f"Auto-filled from company schedule time ({self.report_schedule_timezone})."
            )
            return
        self.report_datetime_value_label.configure(text="Waiting for current time...")
        self.report_datetime_hint.configure(
            text=f"Auto-filled from company schedule time ({self.report_schedule_timezone})."
        )

    def start_report_clock(self):
        if self.report_clock_after_id:
            try:
                self.after_cancel(self.report_clock_after_id)
            except Exception:
                pass
            self.report_clock_after_id = None

        def tick():
            self.report_clock_after_id = None
            if not self.winfo_exists():
                return
            self.sync_live_report_datetime()
            self.start_report_clock()

        self.report_clock_after_id = self.after(1000, tick)

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
        return canvas.create_polygon(points, smooth=True, fill=fill, outline=outline)

    def open_filter_date_popup(self, target):
        if self.filter_popup is not None and self.filter_popup.winfo_exists():
            self.filter_popup.focus()
            self.filter_popup.lift()
            return

        source_value = {
            "anchor": self.filter_anchor_date_value,
            "from": self.filter_from_date_value,
            "to": self.filter_to_date_value,
        }.get(target, self.filter_anchor_date_value)
        selected_date = parse_ui_date(source_value) or self.get_report_schedule_today()
        self.pending_filter_date = format_ui_date(selected_date)
        self.filter_popup_target = target
        self.filter_popup_month = datetime(selected_date.year, selected_date.month, 1)

        popup = ctk.CTkToplevel(self)
        popup.title("Choose Filter Date")
        popup.resizable(False, False)
        popup.configure(fg_color="#fff7ed")
        apply_app_window_icon(popup, self)
        popup.attributes("-topmost", True)
        popup.transient(self.winfo_toplevel())
        popup.protocol("WM_DELETE_WINDOW", self.close_filter_date_popup)

        popup_width = 308
        popup_height = 358
        popup.geometry(f"{popup_width}x{popup_height}")
        popup.update_idletasks()

        try:
            anchor_widget = self.filter_value_button if target == "anchor" else (
                self.filter_from_button if target == "from" else self.filter_to_button
            )
            x_pos = anchor_widget.winfo_rootx()
            y_pos = anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + 8
        except Exception:
            root = self.winfo_toplevel()
            x_pos = root.winfo_rootx() + 80
            y_pos = root.winfo_rooty() + 80

        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        x_pos = max(24, min(x_pos, screen_w - popup_width - 24))
        y_pos = max(24, min(y_pos, screen_h - popup_height - 48))
        popup.geometry(f"{popup_width}x{popup_height}+{x_pos}+{y_pos}")

        popup.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            popup,
            text="<",
            width=34,
            height=30,
            corner_radius=10,
            fg_color="#4b382d",
            hover_color="#5b473b",
            text_color="#fff7ed",
            command=lambda: self.shift_filter_popup_month(-1),
        ).grid(row=0, column=0, sticky="w", padx=(14, 6), pady=(14, 10))

        self.filter_month_label = ctk.CTkLabel(
            popup,
            text="",
            font=("Segoe UI", 12, "bold"),
            text_color=self.text_dark,
        )
        self.filter_month_label.grid(row=0, column=1, sticky="ew", pady=(14, 10))

        ctk.CTkButton(
            popup,
            text=">",
            width=34,
            height=30,
            corner_radius=10,
            fg_color="#4b382d",
            hover_color="#5b473b",
            text_color="#fff7ed",
            command=lambda: self.shift_filter_popup_month(1),
        ).grid(row=0, column=2, sticky="e", padx=(6, 14), pady=(14, 10))

        self.filter_calendar_canvas = tk.Canvas(
            popup,
            width=274,
            height=210,
            bg="#fff7ed",
            highlightthickness=0,
            bd=0,
        )
        self.filter_calendar_canvas.grid(row=1, column=0, columnspan=3, padx=12)
        self.filter_calendar_canvas.bind("<Button-1>", self.on_filter_calendar_click)

        ctk.CTkLabel(
            popup,
            text="Choose a date. The selected filter mode decides how that date is used.",
            font=("Segoe UI", 10),
            text_color=self.text_muted,
            justify="left",
            anchor="w",
        ).grid(row=2, column=0, columnspan=3, sticky="ew", padx=14, pady=(8, 0))

        action_row = ctk.CTkFrame(popup, fg_color="transparent")
        action_row.grid(row=3, column=0, columnspan=3, sticky="ew", padx=14, pady=(16, 14))

        ctk.CTkButton(
            action_row,
            text="Cancel",
            width=108,
            height=36,
            corner_radius=10,
            fg_color="#4b382d",
            hover_color="#5b473b",
            text_color="#fff7ed",
            command=self.close_filter_date_popup,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            action_row,
            text="Confirm",
            width=108,
            height=36,
            corner_radius=10,
            fg_color="#c58b42",
            hover_color="#d49a50",
            text_color=self.text_dark,
            command=self.confirm_filter_date_popup,
        ).pack(side="left")

        self.filter_popup = popup
        self.redraw_filter_calendar()

    def close_filter_date_popup(self):
        popup = getattr(self, "filter_popup", None)
        if popup is not None and popup.winfo_exists():
            popup.destroy()
        self.filter_popup = None
        self.filter_calendar_canvas = None
        self.filter_month_label = None
        self.filter_calendar_hits = []

    def shift_filter_popup_month(self, delta):
        current = self.filter_popup_month
        total_month = (current.year * 12 + current.month - 1) + delta
        year = total_month // 12
        month = total_month % 12 + 1
        self.filter_popup_month = current.replace(year=year, month=month, day=1)
        self.redraw_filter_calendar()

    def redraw_filter_calendar(self):
        canvas = getattr(self, "filter_calendar_canvas", None)
        if canvas is None:
            return

        canvas.delete("all")
        self.filter_calendar_hits = []
        month_start = self.filter_popup_month

        if self.filter_month_label is not None:
            self.filter_month_label.configure(text=month_start.strftime("%B %Y"))

        day_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        cell_w = 38
        cell_h = 30
        start_x = 8
        start_y = 24
        radius = 10
        today = self.get_report_schedule_today()
        selected_date = parse_ui_date(self.pending_filter_date)

        for index, label_text in enumerate(day_headers):
            x_pos = start_x + index * cell_w + cell_w / 2
            canvas.create_text(
                x_pos,
                10,
                text=label_text,
                fill=self.text_muted,
                font=("Segoe UI", 9, "bold"),
            )

        for row_index, week in enumerate(calendar.monthcalendar(month_start.year, month_start.month)):
            for col_index, day_number in enumerate(week):
                if not day_number:
                    continue

                x1 = start_x + col_index * cell_w
                y1 = start_y + row_index * cell_h
                x2 = x1 + cell_w - 4
                y2 = y1 + cell_h - 4
                current_date = month_start.replace(day=day_number).date()

                fill = "#fff7ed"
                outline = "#efd8b4"
                text_color = self.text_dark
                if current_date == today:
                    fill = "#fef3c7"
                    outline = "#e6b450"
                if selected_date and current_date == selected_date:
                    fill = "#c58b42"
                    outline = "#c58b42"

                self.draw_round_rect(canvas, x1, y1, x2, y2, radius, fill, outline)
                canvas.create_text(
                    (x1 + x2) / 2,
                    (y1 + y2) / 2,
                    text=str(day_number),
                    fill="#1f160f" if selected_date and current_date == selected_date else text_color,
                    font=("Segoe UI", 10, "bold"),
                )
                self.filter_calendar_hits.append((x1, y1, x2, y2, current_date.strftime("%d-%m-%Y")))

    def on_filter_calendar_click(self, event):
        for x1, y1, x2, y2, date_text in self.filter_calendar_hits:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.pending_filter_date = date_text
                self.redraw_filter_calendar()
                return

    def confirm_filter_date_popup(self):
        selected_date = parse_ui_date(self.pending_filter_date)
        if selected_date is None:
            messagebox.showwarning("Task Report", "Please choose a valid filter date.")
            return

        value_text = selected_date.strftime("%d-%m-%Y")
        if self.filter_popup_target == "from":
            self.filter_from_date_value = value_text
        elif self.filter_popup_target == "to":
            self.filter_to_date_value = value_text
        else:
            self.filter_anchor_date_value = value_text

        self.update_filter_button_labels()
        self.close_filter_date_popup()

    def load_reports(self, force=False):
        from_date, to_date, error_message = self.get_filter_date_range()
        if error_message:
            self.set_list_status(error_message, is_error=True)
            return

        self.load_reports_request_id += 1
        request_id = self.load_reports_request_id
        self.is_reports_loading = True
        self.set_list_status("Loading reports...")
        self.refresh_button.configure(state="disabled")
        self.apply_filter_button.configure(state="disabled")

        def worker():
            result = self.service.get_reports(
                self.current_username,
                from_date=from_date,
                to_date=to_date,
                force=force,
            )
            self.dispatch_ui(lambda: self.finish_load_reports(request_id, result))

        threading.Thread(target=worker, daemon=True).start()

    def finish_load_reports(self, request_id, result):
        if request_id != self.load_reports_request_id:
            return
        self.is_reports_loading = False
        self.refresh_button.configure(state="normal")
        self.apply_filter_button.configure(state="normal")

        if not result.get("success"):
            self.report_items = []
            self.filtered_report_items = []
            self.render_report_rows()
            self.set_list_status(result.get("message", "Unable to load reports."), is_error=True)
            self.loaded_from_date = ""
            self.loaded_to_date = ""
            self.update_filter_summary()
            return

        self.report_items = sorted(
            result.get("data", []),
            key=build_report_sort_key,
            reverse=True,
        )
        self.loaded_from_date = normalize_text(result.get("from_date"))
        self.loaded_to_date = normalize_text(result.get("to_date"))
        self.set_list_status(f"Loaded {len(self.report_items)} report(s).")
        self.apply_local_filters()

    def apply_local_filters(self):
        if self.search_after_id:
            try:
                self.after_cancel(self.search_after_id)
            except Exception:
                pass
            self.search_after_id = None

        keyword = normalize_text(self.search_entry.get()).lower()
        if not keyword:
            self.filtered_report_items = list(self.report_items)
        else:
            filtered = []
            for item in self.report_items:
                haystack = " ".join(
                    [
                        normalize_text(item.get("merchant")),
                        normalize_text(item.get("caller_phone")),
                        normalize_text(item.get("processing")),
                        normalize_text(item.get("problem")),
                        normalize_text(item.get("solution")),
                    ]
                ).lower()
                if keyword in haystack:
                    filtered.append(item)
            self.filtered_report_items = filtered

        self.render_report_rows()
        self.update_filter_summary()

    def render_report_rows(self):
        filtered_ids = {
            item.get("report_id")
            for item in self.filtered_report_items
            if item.get("report_id") is not None
        }
        self.visible_report_widget_ids = list(filtered_ids)

        if self.selected_report_id is not None and self.selected_report_id not in filtered_ids:
            if self.active_report is not None:
                self.start_new_report()
            else:
                self.selected_report_id = None
                self._sync_report_tree_selection(None)

        self._clear_report_tree()

        if not self.filtered_report_items:
            text = (
                "No report found in the current range."
                if not normalize_text(self.search_entry.get())
                else "No report matched the current local search."
            )
            self._set_report_tree_empty_state(text)
            return

        for index, item in enumerate(self.filtered_report_items):
            report_id = item.get("report_id")
            if report_id is None:
                continue
            self.report_tree.insert(
                "",
                "end",
                iid=str(report_id),
                values=self._build_report_tree_values(item),
                tags=("even" if index % 2 == 0 else "odd",),
            )

        self._set_report_tree_empty_state("")
        if self.selected_report_id in filtered_ids:
            self._sync_report_tree_selection(self.selected_report_id)
        else:
            self._sync_report_tree_selection(None)

    def get_report_by_id(self, report_id):
        for item in self.report_items:
            if item.get("report_id") == report_id:
                return item
        return None

    def select_report(self, report_id, allow_toggle=True):
        if allow_toggle and self.selected_report_id == report_id and self.active_report is not None:
            self.start_new_report()
            return

        item = self.get_report_by_id(report_id)
        if not item:
            return
        self.active_report = dict(item)
        self.selected_report_id = report_id
        self._sync_report_tree_selection(report_id)
        self.load_report_into_form(item)
        self.update_form_mode()

    def load_report_into_form(self, item):
        payload = item or {}
        self.report_date_value = normalize_text(payload.get("report_date", ""))
        self.report_time_value = normalize_text(payload.get("report_time", ""))
        self.update_report_datetime_display()
        self.set_entry_value(self.merchant_entry, payload.get("merchant", ""))
        self.set_entry_value(self.caller_phone_entry, payload.get("caller_phone", ""))
        self.problem_box.delete("1.0", "end")
        self.problem_box.insert("1.0", payload.get("problem", ""))
        self.solution_box.delete("1.0", "end")
        self.solution_box.insert("1.0", payload.get("solution", ""))

        processing_text = normalize_text(payload.get("processing")) or PROCESSING_OPTIONS[0]
        self.select_processing(processing_text)
        self.sync_current_technician_display()
        self.set_feedback("", is_error=False)

    def start_new_report(self):
        self.active_report = None
        self.selected_report_id = None
        self._sync_report_tree_selection(None)
        self.reset_form_defaults()
        self.update_form_mode()
        self.set_feedback("", is_error=False)
        try:
            self.merchant_entry.focus()
        except Exception:
            pass

    def update_form_mode(self):
        is_edit_mode = bool(self.active_report and self.active_report.get("report_id"))
        if is_edit_mode:
            self.save_button.configure(state="disabled", fg_color="#d9c7aa", hover_color="#d9c7aa", text_color="#8f7a62")
            self.update_button.configure(state="normal", fg_color="#3a2d25", hover_color="#4b3b31", text_color="#f5efe6")
            self.new_report_button.configure(state="normal", fg_color="#5a483d", hover_color="#6a5548", text_color="#f5efe6")
            self.delete_button.configure(state="normal", fg_color="#9f2d2d", hover_color="#ba3a3a", text_color="#fff7f0")
        else:
            self.save_button.configure(state="normal", fg_color="#8b5e1a", hover_color="#a06c1e", text_color="#fff7e8")
            self.update_button.configure(state="disabled", fg_color="#b8aba0", hover_color="#b8aba0", text_color="#f4eee7")
            self.new_report_button.configure(
                state="disabled",
                fg_color="#b8aba0",
                hover_color="#b8aba0",
                text_color="#f4eee7",
            )
            self.delete_button.configure(state="disabled", fg_color="#d7b7b7", hover_color="#d7b7b7", text_color="#fff7f0")

        if self.is_saving:
            self.save_button.configure(state="disabled")
            self.update_button.configure(state="disabled")
            self.delete_button.configure(state="disabled")
            self.new_report_button.configure(
                state="disabled",
                fg_color="#b8aba0",
                hover_color="#b8aba0",
                text_color="#f4eee7",
            )

    def collect_form_payload(self):
        if not self.active_report or not self.active_report.get("report_id"):
            self.sync_live_report_datetime()
        report_date = normalize_text(self.report_date_value)
        report_time = normalize_text(self.report_time_value)
        merchant = normalize_text(self.merchant_entry.get())
        caller_phone = normalize_text(self.caller_phone_entry.get())
        problem = normalize_text(self.problem_box.get("1.0", "end"))
        solution = normalize_text(self.solution_box.get("1.0", "end"))
        processing = normalize_text(self.selected_processing)
        technician = self.get_current_technician_payload()

        if parse_ui_date(report_date) is None:
            return None, "DATE must be DD-MM-YYYY."
        if parse_ui_time(report_time) is None:
            return None, "TIME must be HH:MM or HH:MM:SS."
        if not merchant:
            return None, "MERCHANT is required."
        if len(re.sub(r"\D", "", caller_phone)) != 10:
            return None, "CALLER PHONE must be in format (___) ___-____."
        if not problem:
            return None, "PROBLEM is required."
        if not solution:
            return None, "SOLUTION is required."
        if not processing:
            return None, "PROCESSING is required."
        if not technician.get("username"):
            return None, "Unable to resolve the logged-in technician username."

        payload = {
            "action_by_username": self.current_username,
            "report_date": report_date,
            "report_time": report_time,
            "merchant": merchant,
            "caller_phone": caller_phone,
            "problem": problem,
            "solution": solution,
            "processing": processing,
            "technician_username": technician.get("username", ""),
            "technician_display_name": technician.get("display_name", ""),
        }
        return payload, ""

    def on_save(self):
        if self.active_report and self.active_report.get("report_id"):
            messagebox.showwarning(
                "Task Report",
                "This report is already saved. Use Update to edit it or New Report to create a new one.",
            )
            return

        payload, error_message = self.collect_form_payload()
        if error_message:
            messagebox.showwarning("Task Report", error_message)
            return

        self.is_saving = True
        self.update_form_mode()
        self.set_feedback("Saving report...", is_error=False)

        def worker():
            result = self.service.create_report(payload)
            self.dispatch_ui(lambda: self.finish_save("create", result))

        threading.Thread(target=worker, daemon=True).start()

    def on_update(self):
        if not self.active_report or not self.active_report.get("report_id"):
            messagebox.showwarning("Task Report", "Select a report first before updating.")
            return

        payload, error_message = self.collect_form_payload()
        if error_message:
            messagebox.showwarning("Task Report", error_message)
            return

        self.is_saving = True
        self.update_form_mode()
        self.set_feedback("Updating report...", is_error=False)
        report_id = self.active_report.get("report_id")

        def worker():
            result = self.service.update_report(report_id, payload)
            self.dispatch_ui(lambda: self.finish_save("update", result))

        threading.Thread(target=worker, daemon=True).start()

    def on_delete(self):
        if not self.active_report or not self.active_report.get("report_id"):
            messagebox.showwarning("Task Report", "Select a report first before deleting.")
            return
        if not messagebox.askyesno("Task Report", "Delete this report note?"):
            return

        self.is_saving = True
        self.update_form_mode()
        self.set_feedback("Deleting report...", is_error=False)
        report_id = self.active_report.get("report_id")

        def worker():
            result = self.service.delete_report(report_id, self.current_username)
            self.dispatch_ui(lambda: self.finish_delete(report_id, result))

        threading.Thread(target=worker, daemon=True).start()

    def finish_save(self, action_name, result):
        self.is_saving = False
        self.update_form_mode()

        if not result.get("success"):
            messagebox.showerror("Task Report", result.get("message", "Save failed."))
            self.set_feedback(result.get("message", "Save failed."), is_error=True)
            return

        item = result.get("data")
        item_visible = bool(item and self.is_item_in_loaded_range(item))
        if item:
            if item_visible:
                self.upsert_report_item(item)
            else:
                self.report_items = [
                    current_item
                    for current_item in self.report_items
                    if current_item.get("report_id") != item.get("report_id")
                ]
            self.apply_local_filters()
            if action_name != "create" and item_visible and item.get("report_id") is not None:
                self.select_report(item.get("report_id"))

        message = result.get("message", "Report saved successfully.")
        if item and not item_visible:
            message = f"{message} It is outside the current loaded date range."
        if action_name == "create":
            if item and normalize_text(item.get("processing")).upper() == "FOLLOW":
                self.open_follow_task_popup(item)
            self.start_new_report()
            self.set_feedback(message, is_error=False)
            return

        self.set_feedback(message, is_error=False)

    def open_follow_task_popup(self, report_item):
        if self.follow_task_popup:
            try:
                self.follow_task_popup.destroy()
            except Exception:
                pass

        popup = ctk.CTkToplevel(self)
        popup.title("DELTA ONE")
        popup.geometry("500x680")
        popup.minsize(460, 560)
        popup.transient(self.winfo_toplevel())
        popup.grab_set()
        popup.configure(fg_color="#fbf5ec")
        self.apply_popup_icon(popup)
        popup.after(80, lambda: popup.winfo_exists() and self.apply_popup_icon(popup))
        popup.after(260, lambda: popup.winfo_exists() and self.apply_popup_icon(popup))
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_rowconfigure(0, weight=1)
        self.follow_task_popup = popup
        self.follow_task_popup_widgets = {}

        panel = ctk.CTkScrollableFrame(
            popup,
            fg_color="#fbf5ec",
            corner_radius=14,
            border_width=0,
        )
        panel.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        panel.grid_columnconfigure(0, weight=1)

        brand_row = ctk.CTkFrame(panel, fg_color="transparent", height=56)
        brand_row.grid(row=0, column=0, sticky="w", padx=18, pady=(12, 8))
        brand_row.grid_propagate(False)

        logo_image = self.get_follow_task_logo_image()
        if logo_image:
            logo_wrap = ctk.CTkFrame(
                brand_row,
                width=132,
                height=56,
                fg_color="transparent",
            )
            logo_wrap.pack(side="left")
            logo_wrap.pack_propagate(False)

            logo_label = ctk.CTkLabel(
                logo_wrap,
                text="",
                image=logo_image,
            )
            logo_label.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            panel,
            text="Task Details",
            font=("Segoe UI", 18, "bold"),
            text_color="#2f241c",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 6))
        ctk.CTkLabel(
            panel,
            text="Daily Case Note is saved. Review and create a Task Follow item if this case needs follow-up.",
            font=("Segoe UI", 11),
            text_color="#6f5c4c",
            justify="left",
            wraplength=420,
        ).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 14))

        report_time_text = normalize_text(report_item.get("report_time"))
        deadline_time, deadline_period = split_task_deadline_time(report_time_text)
        defaults = {
            "merchant": normalize_text(report_item.get("merchant")),
            "phone": normalize_text(report_item.get("caller_phone")),
            "problem": normalize_text(report_item.get("problem")),
            "deadline_date": normalize_text(report_item.get("report_date")) or format_ui_date(self.get_report_schedule_now().date()),
            "deadline_time": deadline_time,
            "deadline_period": deadline_period,
            "note": normalize_text(report_item.get("solution")),
        }
        self.follow_task_deadline_date = defaults["deadline_date"]
        self.follow_task_deadline_time = f"{defaults['deadline_time']} {defaults['deadline_period']}".strip()
        self.follow_task_deadline_period = defaults["deadline_period"]

        row = 3
        self.follow_task_popup_widgets["merchant"] = self._create_popup_labeled_entry(
            panel,
            row,
            "Merchant Name:",
            defaults["merchant"],
            "SAPPHIRE NAILS 45805",
        )
        row += 1
        self.follow_task_popup_widgets["phone"] = self._create_popup_labeled_entry(
            panel,
            row,
            "Phone:",
            defaults["phone"],
            "(012) 345-6789",
        )
        row += 1
        self.follow_task_popup_widgets["problem"] = self._create_popup_labeled_entry(
            panel,
            row,
            "Problem:",
            defaults["problem"],
            "Follow up case note",
        )
        row += 1

        deadline_wrap = ctk.CTkFrame(panel, fg_color="transparent")
        deadline_wrap.grid(row=row, column=0, sticky="ew", padx=18, pady=(2, 10))
        deadline_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            deadline_wrap,
            text="Ngay gio hen",
            font=("Segoe UI", 12, "bold"),
            text_color="#2f241c",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.follow_task_popup_widgets["deadline_button"] = ctk.CTkButton(
            deadline_wrap,
            text="Choose Date & Time",
            width=220,
            height=36,
            fg_color="#fffaf2",
            hover_color="#f6ead7",
            border_color="#d8b780",
            border_width=1,
            text_color="#2f241c",
            corner_radius=12,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
            command=self.toggle_follow_task_deadline_popup,
        )
        self.follow_task_popup_widgets["deadline_button"].grid(row=1, column=0, sticky="w")
        self.follow_task_popup_widgets["deadline_hint"] = ctk.CTkLabel(
            deadline_wrap,
            text="",
            font=("Segoe UI", 10),
            text_color="#6f5c4c",
            justify="left",
        )
        self.follow_task_popup_widgets["deadline_hint"].grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.update_follow_task_deadline_button()
        row += 1

        ctk.CTkLabel(
            panel,
            text="Assignee",
            font=("Segoe UI", 12, "bold"),
            text_color="#2f241c",
        ).grid(row=row, column=0, sticky="w", padx=18, pady=(4, 6))
        row += 1
        self.follow_task_popup_widgets["handoff_wrap"] = ctk.CTkFrame(panel, fg_color="transparent")
        self.follow_task_popup_widgets["handoff_wrap"].grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        row += 1
        self.render_follow_task_handoff_buttons()
        self.load_follow_task_handoff_options(
            defaults["deadline_date"],
            defaults["deadline_time"],
            defaults["deadline_period"],
        )

        ctk.CTkLabel(
            panel,
            text="Status",
            font=("Segoe UI", 12, "bold"),
            text_color="#2f241c",
        ).grid(row=row, column=0, sticky="w", padx=18, pady=(4, 6))
        row += 1
        status_display = ctk.CTkButton(
            panel,
            text="FOLLOW",
            height=34,
            corner_radius=10,
            fg_color="#8b5e1a",
            hover_color="#8b5e1a",
            text_color="#fff7e8",
            font=("Segoe UI", 12, "bold"),
            state="disabled",
        )
        status_display.grid(row=row, column=0, sticky="w", padx=18, pady=(0, 12))
        row += 1

        ctk.CTkLabel(
            panel,
            text="Note",
            font=("Segoe UI", 12, "bold"),
            text_color="#2f241c",
        ).grid(row=row, column=0, sticky="w", padx=18, pady=(4, 6))
        row += 1
        note_box = ctk.CTkTextbox(
            panel,
            height=120,
            wrap="word",
            fg_color="#fffaf2",
            border_color="#d8b780",
            border_width=1,
            text_color="#2f241c",
            corner_radius=12,
            font=("Segoe UI", 12),
        )
        note_box.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        note_box.insert("1.0", defaults["note"])
        self.follow_task_popup_widgets["note"] = note_box
        row += 1

        self.follow_task_popup_widgets["feedback"] = ctk.CTkLabel(
            panel,
            text="",
            font=("Segoe UI", 11),
            text_color="#6f5c4c",
            justify="left",
            wraplength=420,
        )
        self.follow_task_popup_widgets["feedback"].grid(row=row, column=0, sticky="w", padx=18, pady=(0, 8))
        row += 1

        action_row = ctk.CTkFrame(panel, fg_color="transparent")
        action_row.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 16))
        save_button = ctk.CTkButton(
            action_row,
            text="Save",
            width=110,
            height=38,
            corner_radius=12,
            fg_color="#8b5e1a",
            hover_color="#a06c1e",
            text_color="#fff7e8",
            font=("Segoe UI", 12, "bold"),
            command=self.save_follow_task_from_report,
        )
        save_button.pack(side="left", padx=(0, 8))
        self.follow_task_popup_widgets["save_button"] = save_button
        cancel_button = ctk.CTkButton(
            action_row,
            text="Cancel",
            width=96,
            height=38,
            corner_radius=12,
            fg_color="#5a483d",
            hover_color="#6a5548",
            text_color="#f5efe6",
            font=("Segoe UI", 12, "bold"),
            command=self.close_follow_task_popup,
        )
        cancel_button.pack(side="left")

        try:
            popup.update_idletasks()
            x = self.winfo_rootx() + max(20, (self.winfo_width() - popup.winfo_width()) // 2)
            y = self.winfo_rooty() + max(20, (self.winfo_height() - popup.winfo_height()) // 2)
            popup.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def apply_popup_icon(self, popup):
        self.follow_task_bitmap_icon_path = apply_app_window_icon(popup, self)
        return
        bitmap_icon_path = self.resolve_popup_bitmap_icon_path()
        try:
            if bitmap_icon_path and os.path.exists(bitmap_icon_path):
                popup.iconbitmap(bitmap_icon_path)
        except Exception:
            pass
        try:
            if bitmap_icon_path and os.path.exists(bitmap_icon_path):
                popup.iconbitmap(default=bitmap_icon_path)
        except Exception:
            pass
        try:
            icon_refs = list(getattr(self.winfo_toplevel(), "_icon_photo", []) or [])
            if icon_refs:
                popup.iconphoto(True, *icon_refs)
                self.follow_task_icon_ref = icon_refs
        except Exception:
            pass
        try:
            if not self.follow_task_icon_ref:
                icon_path = get_data_path("icon.png")
                if os.path.exists(icon_path):
                    self.follow_task_icon_ref = tk.PhotoImage(file=icon_path)
            if self.follow_task_icon_ref:
                popup.iconphoto(True, *self.follow_task_icon_ref if isinstance(self.follow_task_icon_ref, list) else [self.follow_task_icon_ref])
        except Exception:
            pass

    def get_follow_task_logo_image(self):
        if self.follow_task_logo_image:
            return self.follow_task_logo_image

        for filename in ("logo-goc.png", "logo.png", "app_v3.png", "icon.png"):
            source_path = get_data_path(filename)
            if not os.path.exists(source_path):
                continue
            try:
                image = Image.open(source_path)
                width, height = image.size
                if width <= 0 or height <= 0:
                    continue
                scale = min(116 / width, 44 / height)
                size = (max(1, int(width * scale)), max(1, int(height * scale)))
                self.follow_task_logo_image = ctk.CTkImage(image, size=size)
                return self.follow_task_logo_image
            except Exception:
                continue

        return None

    def resolve_popup_bitmap_icon_path(self):
        if self.follow_task_bitmap_icon_path and os.path.exists(self.follow_task_bitmap_icon_path):
            return self.follow_task_bitmap_icon_path

        root_bitmap_icon_path = normalize_text(getattr(self.winfo_toplevel(), "_bitmap_icon_path", ""))
        if root_bitmap_icon_path and os.path.exists(root_bitmap_icon_path):
            self.follow_task_bitmap_icon_path = root_bitmap_icon_path
            return self.follow_task_bitmap_icon_path

        for filename in ("app_v3.ico", "app.ico"):
            candidate = get_data_path(filename)
            if os.path.exists(candidate):
                self.follow_task_bitmap_icon_path = candidate
                return self.follow_task_bitmap_icon_path

        for filename in ("icon.png", "app_v3.png", "logo.png"):
            source_path = get_data_path(filename)
            if not os.path.exists(source_path):
                continue
            try:
                generated_icon_path = Path(tempfile.gettempdir()) / "DeltaOne" / "task_report_follow_task.ico"
                generated_icon_path.parent.mkdir(parents=True, exist_ok=True)
                with Image.open(source_path) as source_image:
                    icon_image = source_image.convert("RGBA")
                icon_image.thumbnail((256, 256), Image.Resampling.LANCZOS)
                square_icon = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
                square_icon.alpha_composite(
                    icon_image,
                    (
                        (256 - icon_image.width) // 2,
                        (256 - icon_image.height) // 2,
                    ),
                )
                square_icon.save(
                    generated_icon_path,
                    format="ICO",
                    sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
                )
                self.follow_task_bitmap_icon_path = str(generated_icon_path)
                return self.follow_task_bitmap_icon_path
            except Exception:
                continue

        return ""

    def _create_popup_labeled_entry(self, parent, row, label_text, value, placeholder):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 10))
        wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            wrap,
            text=label_text,
            font=("Segoe UI", 12, "bold"),
            text_color="#2f241c",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        entry = ctk.CTkEntry(
            wrap,
            height=36,
            placeholder_text=placeholder,
            fg_color="#fffaf2",
            border_color="#d8b780",
            border_width=1,
            text_color="#2f241c",
            corner_radius=10,
            font=("Segoe UI", 12),
        )
        entry.grid(row=1, column=0, sticky="ew")
        if value:
            entry.insert(0, value)
        return entry

    def render_follow_task_handoff_buttons(self):
        wrap = self.follow_task_popup_widgets.get("handoff_wrap")
        if not wrap:
            return
        for child in wrap.winfo_children():
            child.destroy()
        options = self.follow_task_handoff_options or [{"username": "", "display_name": "Tech Team", "type": "TEAM"}]
        selected = self.follow_task_selected_handoff or "Tech Team"
        for index, option in enumerate(options):
            display_name = normalize_text(option.get("display_name")) or "Tech Team"
            is_selected = display_name == selected
            button = ctk.CTkButton(
                wrap,
                text=display_name,
                height=32,
                corner_radius=10,
                fg_color="#8b5e1a" if is_selected else "#fffaf2",
                hover_color="#a06c1e" if is_selected else "#f1dfc3",
                text_color="#fff7e8" if is_selected else "#2f241c",
                border_width=0 if is_selected else 1,
                border_color="#d8b780",
                font=("Segoe UI", 10, "bold" if is_selected else "normal"),
                command=lambda name=display_name: self.select_follow_task_handoff(name),
            )
            button.grid(row=index // 2, column=index % 2, sticky="ew", padx=(0, 8), pady=(0, 8))
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_columnconfigure(1, weight=1)

    def select_follow_task_handoff(self, display_name):
        self.follow_task_selected_handoff = normalize_text(display_name) or "Tech Team"
        self.render_follow_task_handoff_buttons()

    def update_follow_task_deadline_button(self):
        date_text = normalize_text(self.follow_task_deadline_date)
        time_text = normalize_text(self.follow_task_deadline_time)
        button = self.follow_task_popup_widgets.get("deadline_button")
        hint = self.follow_task_popup_widgets.get("deadline_hint")
        if button:
            if date_text and time_text:
                button.configure(text=f"{date_text} {time_text}")
            else:
                button.configure(text="Choose Date & Time")
        if hint:
            hint.configure(text="Deadline for the Task Follow item.")

    def toggle_follow_task_deadline_popup(self):
        popup = getattr(self, "follow_task_deadline_popup", None)
        if popup is not None and popup.winfo_exists():
            self.close_follow_task_deadline_popup()
            return
        self.open_follow_task_deadline_popup()

    def open_follow_task_deadline_popup(self):
        target_button = self.follow_task_popup_widgets.get("deadline_button")
        if target_button is None:
            return
        if self.follow_task_deadline_popup is not None and self.follow_task_deadline_popup.winfo_exists():
            self.follow_task_deadline_popup.destroy()

        selected_date = parse_ui_date(self.follow_task_deadline_date)
        self.follow_task_deadline_month = (
            datetime.combine(selected_date, datetime.min.time()).replace(day=1)
            if selected_date
            else datetime.now().replace(day=1)
        )

        popup = ctk.CTkFrame(
            self.follow_task_popup,
            fg_color="#fff7ed",
            corner_radius=14,
            border_width=1,
            border_color="#d8b780",
            width=292,
            height=344,
        )
        popup.place(in_=target_button, relx=0, rely=1.0, x=0, y=8, anchor="nw")
        popup.lift()
        popup.grid_columnconfigure(1, weight=1)
        self.follow_task_deadline_popup = popup

        ctk.CTkButton(
            popup,
            text="<",
            width=34,
            height=30,
            corner_radius=10,
            fg_color="#5a483d",
            hover_color="#6a5548",
            text_color="#f5efe6",
            command=lambda: self.shift_follow_task_deadline_month(-1),
        ).grid(row=0, column=0, sticky="w", padx=(12, 6), pady=(12, 8))
        self.follow_task_popup_widgets["deadline_month_label"] = ctk.CTkLabel(
            popup,
            text="",
            font=("Segoe UI", 12, "bold"),
            text_color="#2f241c",
        )
        self.follow_task_popup_widgets["deadline_month_label"].grid(row=0, column=1, sticky="ew", pady=(12, 8))
        ctk.CTkButton(
            popup,
            text=">",
            width=34,
            height=30,
            corner_radius=10,
            fg_color="#5a483d",
            hover_color="#6a5548",
            text_color="#f5efe6",
            command=lambda: self.shift_follow_task_deadline_month(1),
        ).grid(row=0, column=2, sticky="e", padx=(6, 12), pady=(12, 8))

        calendar_canvas = tk.Canvas(popup, width=266, height=198, bg="#fff7ed", highlightthickness=0, bd=0)
        calendar_canvas.grid(row=1, column=0, columnspan=3, padx=12)
        calendar_canvas.bind("<Button-1>", self.on_follow_task_deadline_calendar_click)
        self.follow_task_popup_widgets["deadline_calendar_canvas"] = calendar_canvas

        ctk.CTkLabel(
            popup,
            text="Time",
            font=("Segoe UI", 11, "bold"),
            text_color="#2f241c",
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=12, pady=(4, 6))
        time_values = self.get_follow_task_time_slots()
        time_combo = ctk.CTkComboBox(
            popup,
            values=time_values,
            height=36,
            fg_color="#fffaf2",
            border_color="#d8b780",
            button_color="#8b5e1a",
            button_hover_color="#a06c1e",
            text_color="#2f241c",
            dropdown_fg_color="#fffaf2",
            dropdown_text_color="#2f241c",
        )
        current_time = normalize_text(self.follow_task_deadline_time)
        time_combo.set(current_time if current_time in time_values else (time_values[0] if time_values else ""))
        time_combo.grid(row=3, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 16))
        self.follow_task_popup_widgets["deadline_time_combo"] = time_combo

        action_row = ctk.CTkFrame(popup, fg_color="transparent")
        action_row.grid(row=4, column=0, columnspan=3, sticky="ew", padx=12, pady=(12, 12))
        ctk.CTkButton(
            action_row,
            text="Cancel",
            width=108,
            height=34,
            corner_radius=10,
            fg_color="#5a483d",
            hover_color="#6a5548",
            text_color="#f5efe6",
            command=self.close_follow_task_deadline_popup,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            action_row,
            text="Confirm",
            width=108,
            height=34,
            corner_radius=10,
            fg_color="#8b5e1a",
            hover_color="#a06c1e",
            text_color="#fff7e8",
            command=self.confirm_follow_task_deadline_popup,
        ).pack(side="left")

        self.redraw_follow_task_deadline_calendar()

    def get_follow_task_time_slots(self):
        slots = []
        base = datetime.strptime("12:00 AM", "%I:%M %p")
        for index in range(48):
            slots.append((base + timedelta(minutes=30 * index)).strftime("%I:%M %p").lstrip("0"))
        return slots

    def close_follow_task_deadline_popup(self):
        popup = getattr(self, "follow_task_deadline_popup", None)
        if popup is not None and popup.winfo_exists():
            popup.destroy()
        self.follow_task_deadline_popup = None
        self.follow_task_deadline_hits = []

    def shift_follow_task_deadline_month(self, month_delta):
        current = self.follow_task_deadline_month
        total_month = (current.year * 12 + current.month - 1) + month_delta
        year = total_month // 12
        month = total_month % 12 + 1
        self.follow_task_deadline_month = current.replace(year=year, month=month, day=1)
        self.redraw_follow_task_deadline_calendar()

    def redraw_follow_task_deadline_calendar(self):
        canvas = self.follow_task_popup_widgets.get("deadline_calendar_canvas")
        month_label = self.follow_task_popup_widgets.get("deadline_month_label")
        if canvas is None or month_label is None:
            return

        canvas.delete("all")
        self.follow_task_deadline_hits = []
        month_start = self.follow_task_deadline_month
        month_label.configure(text=month_start.strftime("%B %Y"))
        day_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        cell_w = 36
        cell_h = 28
        start_x = 8
        start_y = 22

        for idx, label in enumerate(day_headers):
            x = start_x + idx * cell_w + cell_w / 2
            canvas.create_text(x, 10, text=label, fill="#6f5c4c", font=("Segoe UI", 9, "bold"))

        selected_date = parse_ui_date(self.follow_task_deadline_date)
        today = self.get_report_schedule_now().date()
        for row_idx, week in enumerate(calendar.monthcalendar(month_start.year, month_start.month)):
            for col_idx, day_num in enumerate(week):
                if not day_num:
                    continue
                x1 = start_x + col_idx * cell_w
                y1 = start_y + row_idx * cell_h
                x2 = x1 + cell_w - 4
                y2 = y1 + cell_h - 4
                current_date = month_start.replace(day=day_num).date()
                fill = "#fff7ed"
                outline = "#efd8b4"
                text_color = "#2f241c"
                if current_date == today:
                    fill = "#fef3c7"
                    outline = "#e6b450"
                if selected_date and current_date == selected_date:
                    fill = "#8b5e1a"
                    outline = "#8b5e1a"
                    text_color = "#fff7e8"
                self.draw_round_rect(canvas, x1, y1, x2, y2, 10, fill, outline)
                canvas.create_text(
                    (x1 + x2) / 2,
                    (y1 + y2) / 2,
                    text=str(day_num),
                    fill=text_color,
                    font=("Segoe UI", 10, "bold"),
                )
                self.follow_task_deadline_hits.append((x1, y1, x2, y2, current_date.strftime("%d-%m-%Y")))

    def on_follow_task_deadline_calendar_click(self, event):
        for x1, y1, x2, y2, date_text in self.follow_task_deadline_hits:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.follow_task_deadline_date = date_text
                self.redraw_follow_task_deadline_calendar()
                return

    def confirm_follow_task_deadline_popup(self):
        if parse_ui_date(self.follow_task_deadline_date) is None:
            messagebox.showwarning("Task Details", "Hay chon ngay hen hop le.")
            return
        time_combo = self.follow_task_popup_widgets.get("deadline_time_combo")
        selected_time = normalize_text(time_combo.get()) if time_combo else ""
        if selected_time not in self.get_follow_task_time_slots():
            messagebox.showwarning("Task Details", "Hay chon gio hen hop le.")
            return
        self.follow_task_deadline_time = selected_time
        self.follow_task_deadline_period = selected_time[-2:].upper()
        self.update_follow_task_deadline_button()
        time_value, period_value = self.get_follow_task_deadline_parts()[1:]
        self.load_follow_task_handoff_options(self.follow_task_deadline_date, time_value, period_value)
        self.close_follow_task_deadline_popup()

    def get_follow_task_deadline_parts(self):
        time_text = normalize_text(self.follow_task_deadline_time)
        if not time_text:
            return self.follow_task_deadline_date, "", self.follow_task_deadline_period
        try:
            parsed = datetime.strptime(time_text, "%I:%M %p")
            return self.follow_task_deadline_date, parsed.strftime("%I:%M").lstrip("0"), parsed.strftime("%p")
        except ValueError:
            return self.follow_task_deadline_date, time_text, self.follow_task_deadline_period

    def load_follow_task_handoff_options(self, deadline_date, deadline_time, deadline_period):
        if not self.current_username:
            return

        def worker():
            result = self.task_service.get_handoff_options(
                self.current_username,
                task_date=deadline_date,
                task_time=deadline_time,
                task_period=deadline_period,
                deadline_timezone="",
            )
            self.dispatch_ui(lambda: self.finish_load_follow_task_handoff_options(result))

        threading.Thread(target=worker, daemon=True).start()

    def finish_load_follow_task_handoff_options(self, result):
        if not self.follow_task_popup or not self.follow_task_popup.winfo_exists():
            return
        if result.get("success"):
            options = result.get("data") or []
            self.follow_task_handoff_options = options or [{"username": "", "display_name": "Tech Team", "type": "TEAM"}]
            names = [normalize_text(option.get("display_name")) for option in self.follow_task_handoff_options]
            if self.follow_task_selected_handoff not in names:
                self.follow_task_selected_handoff = names[0] if names else "Tech Team"
            self.render_follow_task_handoff_buttons()

    def collect_follow_task_popup_payload(self):
        widgets = self.follow_task_popup_widgets
        merchant = normalize_text(widgets["merchant"].get())
        phone = normalize_text(widgets["phone"].get())
        problem = normalize_text(widgets["problem"].get())
        deadline_date, deadline_time, deadline_period = self.get_follow_task_deadline_parts()
        deadline_date = normalize_text(deadline_date)
        deadline_time = normalize_text(deadline_time)
        deadline_period = normalize_text(deadline_period).upper()
        note = normalize_text(widgets["note"].get("1.0", "end"))

        if not merchant:
            return None, "Merchant Name is required."
        if not deadline_date or parse_ui_date(deadline_date) is None:
            return None, "Deadline date must be DD-MM-YYYY."
        try:
            datetime.strptime(f"{deadline_time} {deadline_period}", "%I:%M %p")
        except ValueError:
            return None, "Deadline time must be like 8:30 AM."

        selected_option = next(
            (
                option
                for option in self.follow_task_handoff_options
                if normalize_text(option.get("display_name")) == self.follow_task_selected_handoff
            ),
            {"username": "", "display_name": "Tech Team", "type": "TEAM"},
        )
        option_type = normalize_text(selected_option.get("type")).upper() or "TEAM"
        display_name = normalize_text(selected_option.get("display_name")) or "Tech Team"
        username = normalize_text(selected_option.get("username"))
        if option_type == "TEAM":
            handoff_type = "TEAM"
            handoff_username = ""
            handoff_display_names = [display_name]
            handoff_usernames = []
        else:
            handoff_type = "USER"
            handoff_username = username
            handoff_display_names = [display_name]
            handoff_usernames = [username] if username else []
            if not handoff_usernames:
                return None, "Handoff target is invalid."

        return {
            "action_by_username": self.current_username,
            "merchant_raw_text": merchant,
            "merchant_timezone": "",
            "phone": phone,
            "tracking_number": "",
            "problem_summary": problem,
            "handoff_to_type": handoff_type,
            "handoff_to_username": handoff_username,
            "handoff_to_display_name": ", ".join(handoff_display_names),
            "handoff_to_usernames": handoff_usernames,
            "handoff_to_display_names": handoff_display_names,
            "status": "FOLLOW",
            "deadline_date": deadline_date,
            "deadline_time": deadline_time,
            "deadline_period": deadline_period,
            "note": note,
        }, ""

    def save_follow_task_from_report(self):
        payload, error_message = self.collect_follow_task_popup_payload()
        if error_message:
            messagebox.showwarning("Task Details", error_message)
            return

        save_button = self.follow_task_popup_widgets.get("save_button")
        feedback = self.follow_task_popup_widgets.get("feedback")
        if save_button:
            save_button.configure(state="disabled")
        if feedback:
            feedback.configure(text="Saving Task Follow...", text_color="#6f5c4c")

        def worker():
            result = self.task_service.create_task(payload)
            self.dispatch_ui(lambda: self.finish_save_follow_task_from_report(result))

        threading.Thread(target=worker, daemon=True).start()

    def finish_save_follow_task_from_report(self, result):
        if not self.follow_task_popup or not self.follow_task_popup.winfo_exists():
            return
        save_button = self.follow_task_popup_widgets.get("save_button")
        feedback = self.follow_task_popup_widgets.get("feedback")
        if not result.get("success"):
            if save_button:
                save_button.configure(state="normal")
            if feedback:
                feedback.configure(text=result.get("message", "Unable to create Task Follow."), text_color=ERROR_TEXT)
            return
        self.close_follow_task_popup()
        messagebox.showinfo("Task Details", result.get("message", "Task created successfully."))

    def close_follow_task_popup(self):
        self.close_follow_task_deadline_popup()
        if self.follow_task_popup:
            try:
                self.follow_task_popup.destroy()
            except Exception:
                pass
        self.follow_task_popup = None
        self.follow_task_popup_widgets = {}

    def finish_delete(self, report_id, result):
        self.is_saving = False
        if not result.get("success"):
            self.update_form_mode()
            messagebox.showerror("Task Report", result.get("message", "Delete failed."))
            self.set_feedback(result.get("message", "Delete failed."), is_error=True)
            return

        self.report_items = [item for item in self.report_items if item.get("report_id") != report_id]
        self.apply_local_filters()
        self.start_new_report()
        self.set_feedback(result.get("message", "Report deleted successfully."), is_error=False)

    def upsert_report_item(self, item):
        report_id = item.get("report_id")
        if report_id is None:
            return

        updated = False
        for index, current in enumerate(self.report_items):
            if current.get("report_id") == report_id:
                self.report_items[index] = item
                updated = True
                break
        if not updated:
            self.report_items.append(item)

        self.report_items = sorted(self.report_items, key=build_report_sort_key, reverse=True)

    def destroy(self):
        self.close_filter_date_popup()
        if self.table_header_sync_job:
            try:
                self.after_cancel(self.table_header_sync_job)
            except Exception:
                pass
            self.table_header_sync_job = None
        if self.report_clock_after_id:
            try:
                self.after_cancel(self.report_clock_after_id)
            except Exception:
                pass
            self.report_clock_after_id = None
        if self.search_after_id:
            try:
                self.after_cancel(self.search_after_id)
            except Exception:
                pass
            self.search_after_id = None
        if self.virtual_refresh_job:
            try:
                self.after_cancel(self.virtual_refresh_job)
            except Exception:
                pass
            self.virtual_refresh_job = None
        if self.report_row_measure_job:
            try:
                self.after_cancel(self.report_row_measure_job)
            except Exception:
                pass
            self.report_row_measure_job = None
        super().destroy()
