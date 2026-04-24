import calendar
import re
import threading
import textwrap
from datetime import datetime, timedelta
from tkinter import messagebox
import tkinter as tk
from bisect import bisect_right

import customtkinter as ctk

from services.task_report_service import TaskReportService
from services.timezone_service import (
    current_local_datetime,
    lookup_timezone_by_zip,
    normalize_timezone_name,
)


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

PROCESSING_OPTIONS = [
    "DONE",
    "IN PROGRESS",
    "FOLLOW UP",
    "CALL BACK",
    "WAITING CUSTOMER",
    "PENDING",
]

FILTER_MODES = ["Daily", "Week", "Month", "Range"]

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


def format_phone_digits(digits):
    if not digits:
        return ""
    if len(digits) <= 3:
        return f"({digits}"
    if len(digits) <= 6:
        return f"({digits[:3]}) {digits[3:]}"
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:10]}"


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

        self._build_ui()
        self.reset_filter_defaults()
        self.reset_form_defaults()
        self.start_report_clock()
        self.load_reports(force=False)

    def _build_ui(self):
        content = ctk.CTkScrollableFrame(
            self,
            fg_color=self.panel_inner,
            corner_radius=18,
            border_width=1,
            border_color=self.border_soft,
        )
        content.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        content.grid_columnconfigure(0, weight=1)

        self.form_card = ctk.CTkFrame(
            content,
            fg_color=FORM_CARD_BG,
            corner_radius=16,
            border_width=1,
            border_color=FORM_CARD_BORDER,
        )
        self.form_card.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
        for column in range(4):
            self.form_card.grid_columnconfigure(column, weight=1)

        self._create_card_header(
            self.form_card,
            row=0,
            text="Daily Case Note",
            subtitle="Quick daily note. Saved reports stay visible below.",
            badge_text="ENTRY",
            accent_color=FORM_ACCENT,
            badge_text_color="#fff7e8",
            columnspan=4,
        )

        self.merchant_entry = self._create_labeled_entry(self.form_card, 1, 0, "MERCHANT", "NAIL TOPIA 48327")
        self.caller_phone_entry = self._create_labeled_entry(
            self.form_card,
            1,
            1,
            "CALLER PHONE",
            "(000) 000-0000",
            width=160,
        )
        self.caller_phone_entry.bind("<KeyRelease>", self.on_phone_input)
        self.report_datetime_value_label, self.report_datetime_hint = self._create_labeled_display_value(
            self.form_card,
            1,
            2,
            "DATE & TIME",
            width=320,
            columnspan=2,
        )

        self.processing_combo = self._create_labeled_combo(
            self.form_card,
            2,
            0,
            "PROCESSING",
            PROCESSING_OPTIONS,
            width=170,
        )
        self.technician_value_label, self.technician_hint_label = self._create_labeled_display_value(
            self.form_card,
            2,
            1,
            "TECHNICIAN",
            width=220,
            hint_text="Automatically linked to the logged-in account.",
        )
        self.sync_current_technician_display()

        self.problem_box = self._create_labeled_textbox(
            self.form_card,
            3,
            "PROBLEM",
            height=68,
            column=0,
            columnspan=2,
        )
        self.solution_box = self._create_labeled_textbox(
            self.form_card,
            3,
            "SOLUTION",
            height=68,
            column=2,
            columnspan=2,
        )

        action_row = ctk.CTkFrame(self.form_card, fg_color="transparent")
        action_row.grid(row=4, column=0, columnspan=4, sticky="ew", padx=18, pady=(4, 12))

        self.save_button = ctk.CTkButton(
            action_row,
            text="Save Report",
            width=112,
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
            action_row,
            text="Update",
            width=92,
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

        self.delete_button = ctk.CTkButton(
            action_row,
            text="Delete",
            width=92,
            height=34,
            corner_radius=12,
            fg_color="#9f2d2d",
            hover_color="#ba3a3a",
            text_color="#fff7f0",
            font=("Segoe UI", 11, "bold"),
            command=self.on_delete,
        )
        self.delete_button.pack(side="left", padx=(0, 8))

        self.clear_button = ctk.CTkButton(
            action_row,
            text="Clear",
            width=92,
            height=34,
            corner_radius=12,
            fg_color="#5a483d",
            hover_color="#6a5548",
            text_color="#f5efe6",
            font=("Segoe UI", 11, "bold"),
            command=self.start_new_report,
        )
        self.clear_button.pack(side="left")

        self.feedback_label = ctk.CTkLabel(
            action_row,
            text="",
            font=("Segoe UI", 11, "bold"),
            text_color=self.text_muted,
            anchor="w",
            justify="left",
        )
        self.feedback_label.pack(side="right")

        self.filter_card = ctk.CTkFrame(
            content,
            fg_color=FILTER_CARD_BG,
            corner_radius=16,
            border_width=1,
            border_color=FILTER_CARD_BORDER,
        )
        self.filter_card.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
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
        self.filter_mode_button.set("Month")

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
            placeholder_text="Merchant / Problem / Solution",
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
        self.table_card.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self.table_card.grid_columnconfigure(0, weight=1)
        self.table_card.grid_rowconfigure(3, weight=1)

        self._create_card_header(
            self.table_card,
            row=0,
            text="Saved Reports",
            subtitle="Browse saved entries below and click a row to edit it.",
            badge_text="HISTORY",
            accent_color=TABLE_ACCENT,
            badge_text_color="#fff7e8",
        )

        table_title_row = ctk.CTkFrame(self.table_card, fg_color="transparent")
        table_title_row.grid(row=1, column=0, sticky="ew", padx=18, pady=(4, 8))
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

        self._build_table_header()

        self.list_body = ctk.CTkFrame(
            self.table_card,
            fg_color=MUTED_BG,
            corner_radius=12,
            border_width=1,
            border_color=self.border_soft,
        )
        self.list_body.grid(row=3, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self.list_body.grid_columnconfigure(0, weight=1)
        self.list_body.grid_rowconfigure(0, weight=1)

        self.list_canvas = tk.Canvas(
            self.list_body,
            bg=MUTED_BG,
            highlightthickness=0,
            bd=0,
        )
        self.list_canvas.grid(row=0, column=0, sticky="nsew")
        self.list_canvas.bind("<Configure>", self._on_report_canvas_configure, add="+")
        self.list_canvas.bind("<MouseWheel>", self._on_report_list_mousewheel, add="+")
        self.list_canvas.bind("<Button-4>", self._on_report_list_mousewheel, add="+")
        self.list_canvas.bind("<Button-5>", self._on_report_list_mousewheel, add="+")

        self.list_scrollbar = ctk.CTkScrollbar(
            self.list_body,
            orientation="vertical",
            width=REPORT_TABLE_SCROLLBAR_WIDTH,
            command=self._on_report_scrollbar,
        )
        self.list_scrollbar.grid(row=0, column=1, sticky="ns", padx=(8, 8), pady=8)
        self.list_canvas.configure(yscrollcommand=self.list_scrollbar.set)

        self.list_viewport = ctk.CTkFrame(
            self.list_canvas,
            fg_color="transparent",
            corner_radius=0,
            width=1,
            height=1,
        )
        self.list_viewport_window = self.list_canvas.create_window(
            (0, 0),
            window=self.list_viewport,
            anchor="nw",
        )

        self.empty_label = ctk.CTkLabel(
            self.list_viewport,
            text="Loading reports...",
            font=("Segoe UI", 12),
            text_color=self.text_muted,
            anchor="w",
            justify="left",
        )
        self.empty_label.place(x=10, y=12)

        self.after(50, self._schedule_table_header_sync)

        self.update_filter_inputs()
        self.update_form_mode()

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
    ):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=0, columnspan=columnspan, sticky="ew", padx=18, pady=(14, 10))
        wrap.grid_columnconfigure(0, weight=1)

        accent_bar = ctk.CTkFrame(
            wrap,
            fg_color=accent_color,
            corner_radius=999,
            height=4,
        )
        accent_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            wrap,
            text=text,
            font=("Segoe UI", 16, "bold"),
            text_color=self.text_dark,
        ).grid(row=1, column=0, sticky="w")

        if badge_text:
            ctk.CTkLabel(
                wrap,
                text=badge_text,
                fg_color=accent_color,
                corner_radius=999,
                text_color=badge_text_color,
                font=("Segoe UI", 10, "bold"),
                padx=10,
                pady=4,
            ).grid(row=1, column=1, sticky="e", padx=(12, 0))

        if subtitle:
            ctk.CTkLabel(
                wrap,
                text=subtitle,
                font=("Segoe UI", 11),
                text_color=self.text_muted,
                justify="left",
            ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

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

    def _create_labeled_display_value(
        self,
        parent,
        row,
        column,
        label_text,
        width=None,
        columnspan=1,
        hint_text="Auto-filled from the current system clock.",
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
            display_card.configure(width=width, height=48)

        value_label = ctk.CTkLabel(
            display_card,
            text="",
            font=("Segoe UI", 12, "bold"),
            text_color=self.text_dark,
            anchor="w",
            justify="left",
        )
        value_label.grid(row=0, column=0, sticky="ew", padx=12, pady=(9, 9))

        hint = ctk.CTkLabel(
            wrap,
            text=hint_text,
            font=("Segoe UI", 10),
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
        self.processing_combo.set(PROCESSING_OPTIONS[0])
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
        self.filter_mode_button.set("Month")
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
                for widget in self.report_row_widgets.values():
                    widget.set_selected(False)

        if not self.filtered_report_items:
            text = (
                "No report found in the current range."
                if not normalize_text(self.search_entry.get())
                else "No report matched the current local search."
            )
            self.empty_label.configure(text=text)
            self.empty_label.place(x=10, y=12)
            self.empty_label.lift()
            self._hide_report_rows()
            self._rebuild_virtual_report_metrics()
            self.list_canvas.yview_moveto(0)
            return

        self.empty_label.place_forget()
        self._rebuild_virtual_report_metrics()
        self._schedule_virtual_report_refresh()

    def get_report_by_id(self, report_id):
        for item in self.report_items:
            if item.get("report_id") == report_id:
                return item
        return None

    def select_report(self, report_id):
        item = self.get_report_by_id(report_id)
        if not item:
            return
        self.active_report = dict(item)
        self.selected_report_id = report_id

        for widget in self.report_row_widgets.values():
            widget.set_selected(widget.report_id == report_id)

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
        self.processing_combo.set(processing_text)
        self.sync_current_technician_display()
        self.set_feedback("", is_error=False)

    def start_new_report(self):
        self.active_report = None
        self.selected_report_id = None
        for widget in self.report_row_widgets.values():
            widget.set_selected(False)
        self.reset_form_defaults()
        self.update_form_mode()
        self.set_feedback("", is_error=False)

    def update_form_mode(self):
        is_edit_mode = bool(self.active_report and self.active_report.get("report_id"))
        if is_edit_mode:
            self.save_button.configure(state="disabled", fg_color="#d9c7aa", hover_color="#d9c7aa", text_color="#8f7a62")
            self.update_button.configure(state="normal", fg_color="#3a2d25", hover_color="#4b3b31", text_color="#f5efe6")
            self.delete_button.configure(state="normal", fg_color="#9f2d2d", hover_color="#ba3a3a", text_color="#fff7f0")
        else:
            self.save_button.configure(state="normal", fg_color="#8b5e1a", hover_color="#a06c1e", text_color="#fff7e8")
            self.update_button.configure(state="disabled", fg_color="#b8aba0", hover_color="#b8aba0", text_color="#f4eee7")
            self.delete_button.configure(state="disabled", fg_color="#d7b7b7", hover_color="#d7b7b7", text_color="#fff7f0")

        if self.is_saving:
            self.save_button.configure(state="disabled")
            self.update_button.configure(state="disabled")
            self.delete_button.configure(state="disabled")

    def collect_form_payload(self):
        if not self.active_report or not self.active_report.get("report_id"):
            self.sync_live_report_datetime()
        report_date = normalize_text(self.report_date_value)
        report_time = normalize_text(self.report_time_value)
        merchant = normalize_text(self.merchant_entry.get())
        caller_phone = normalize_text(self.caller_phone_entry.get())
        problem = normalize_text(self.problem_box.get("1.0", "end"))
        solution = normalize_text(self.solution_box.get("1.0", "end"))
        processing = normalize_text(self.processing_combo.get())
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
            messagebox.showwarning("Task Report", "This report is already saved. Use Delete or Clear to continue.")
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
            if item_visible and item.get("report_id") is not None:
                self.select_report(item.get("report_id"))

        message = result.get("message", "Report saved successfully.")
        if item and not item_visible:
            message = f"{message} It is outside the current loaded date range."
        self.set_feedback(message, is_error=False)
        if action_name == "create" and item is not None and item_visible:
            self.active_report = dict(item)
            self.selected_report_id = item.get("report_id")
            self.update_form_mode()
        elif item and not item_visible:
            self.start_new_report()

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
