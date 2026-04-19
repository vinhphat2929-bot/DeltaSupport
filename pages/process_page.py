import calendar
import re
import tkinter as tk
from datetime import datetime
import time
from tkinter import messagebox

import customtkinter as ctk

from services.task_service import TASK_STATUSES
from stores.task_store import TaskStore
from pages.process.service import ProcessService
from pages.process.logic import ProcessLogic
from pages.process.renderers import ProcessRenderer
from pages.process.layout import ProcessLayout
from pages.process.handlers_ui import ProcessUIHandler



class ProcessPage(ctk.CTkFrame):
    # Theme Colors
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
    BTN_INACTIVE = "#e5e7eb"
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

    TRAINING_RESULT_OPTIONS = ["", "DONE", "X"]
    TRAINING_CANVAS_BG = "#fffef9"
    TRAINING_BANNER_BG = "#ffef3a"
    TRAINING_SUBHEADER_BG = "#21d8e2"
    TRAINING_GROUP_BG = "#fff8ec"

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
        self.logic = ProcessLogic()
        self.service = ProcessService(self.store, self.current_user)
        self.renderer = ProcessRenderer(self)
        self.layout = ProcessLayout(self)
        self.ui_handler = ProcessUIHandler(self)

        self.selected_status = "FOLLOW"
        self.selected_handoff_to = "Tech Team"
        self.selected_handoff_targets = ["Tech Team"]
        self.status_buttons = {}
        self.handoff_buttons = {}
        self.handoff_options = [{"username": "", "display_name": "Tech Team", "type": "TEAM"}]
        self.canvas_row_hits = []
        self.deadline_time_slots = self.logic.get_deadline_time_slots()
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
            fg_color=self.BG_PANEL,
            corner_radius=22,
            border_width=1,
            border_color=self.BORDER,
        )
        self.header_card.grid(row=0, column=0, sticky="ew", pady=(4, 12))

        self.title_label = ctk.CTkLabel(
            self.header_card,
            text="Task",
            font=("Segoe UI", 20, "bold"),
            text_color=self.TEXT_DARK,
        )
        self.title_label.pack(anchor="w", padx=22, pady=(18, 4))

        self.subtitle_label = ctk.CTkLabel(
            self.header_card,
            text="Task function will be built here.",
            font=("Segoe UI", 13),
            text_color=self.TEXT_MUTED,
            justify="left",
        )
        self.subtitle_label.pack(anchor="w", padx=22, pady=(0, 18))

        self.body_card = ctk.CTkFrame(
            self,
            fg_color=self.BG_PANEL,
            corner_radius=22,
            border_width=1,
            border_color=self.BORDER,
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
            fg_color=self.BG_PANEL_INNER,
            corner_radius=18,
            border_width=1,
            border_color=self.BORDER_SOFT,
        )
        content.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        content.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            content,
            text=title,
            font=("Segoe UI", 22, "bold"),
            text_color=self.TEXT_DARK,
        ).pack(anchor="w", padx=22, pady=(22, 8))

        ctk.CTkLabel(
            content,
            text=(
                "Function nay se duoc build tiep theo.\n"
                "Tam thoi minh giu san khung de sau nay gan API, bang SQL va giao dien chi tiet."
            ),
            font=("Segoe UI", 14),
            text_color=self.TEXT_MUTED,
            justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 18))

    def create_info_value(self, parent, row, column, label_text):
        return self.layout.create_info_value(parent, row, column, label_text, self.TEXT_DARK, self.TEXT_MUTED)

    # UI Helpers moved to layout.py

    def get_training_stage_key(self, task=None):
        return self.logic.get_training_stage_key((task or self.active_task or {}).get("status", ""))

    def get_training_template_sections(self, stage_key=None):
        return self.logic.get_training_template_sections(
            stage_key or self.get_training_stage_key(),
            self.logic.first_template,
            self.logic.second_template
        )

    def merge_training_form_with_template(self, saved_sections, stage_key=None):
        templates = self.get_training_template_sections(stage_key)
        return self.logic.merge_training_form_with_template(saved_sections, templates)

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
        return self.renderer.estimate_training_row_height(row)

    def redraw_training_canvas(self):
        canvas = getattr(self, "training_canvas", None)
        if canvas is None:
            return
        
        content_height, layout = self.renderer.redraw_training_canvas(
            canvas=canvas,
            flat_rows=self.training_canvas_flat_rows,
            training_note_entries=self.training_note_entries,
            training_note_values=self.training_note_values,
            canvas_width=max(720, canvas.winfo_width()),
            banner_bg=self.TRAINING_BANNER_BG,
            subheader_bg=self.TRAINING_SUBHEADER_BG,
            group_bg=self.TRAINING_GROUP_BG
        )
        self.training_canvas_row_layout = layout
        self.training_canvas_content_height = content_height

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
                            btn_widget.configure(fg_color=self.INPUT_BG, hover_color="#f0e8d8", text_color=self.TEXT_MUTED, text="—")
                    return _toggle

                toggle_fn = make_toggle(result_var)
                if current_val == "DONE":
                    btn_fg, btn_hover, btn_tc, btn_txt = "#ef4444", "#dc2626", "#ffffff", "DONE"
                elif current_val == "X":
                    btn_fg, btn_hover, btn_tc, btn_txt = "#f59e0b", "#d97706", "#ffffff", "X"
                else:
                    btn_fg, btn_hover, btn_tc, btn_txt = self.INPUT_BG, "#f0e8d8", self.TEXT_MUTED, "—"

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
                    fg_color=self.INPUT_BG,
                    border_color=self.INPUT_BORDER,
                    text_color=self.TEXT_DARK,
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
        self.ui_handler.render_handoff_buttons()

    def render_follow_ui(self):
        if not hasattr(self, "body_card") or not self.body_card.winfo_exists():
            return

        for child in self.body_card.winfo_children():
            child.destroy()

        colors = {
            "BG_PANEL_INNER": self.BG_PANEL_INNER,
            "BORDER_SOFT": self.BORDER_SOFT,
            "TEXT_DARK": self.TEXT_DARK,
            "TEXT_MUTED": self.TEXT_MUTED,
            "INPUT_BG": self.INPUT_BG,
            "INPUT_BORDER": self.INPUT_BORDER,
            "BTN_ACTIVE": self.BTN_ACTIVE,
            "BTN_ACTIVE_HOVER": self.BTN_ACTIVE_HOVER,
            "BTN_IDLE": self.BTN_IDLE,
            "BTN_IDLE_HOVER": self.BTN_IDLE_HOVER,
            "BTN_DARK": self.BTN_DARK,
            "BTN_DARK_HOVER": self.BTN_DARK_HOVER,
            "TEXT_LIGHT": self.TEXT_LIGHT,
            "BTN_INACTIVE": self.BTN_INACTIVE,
            "TRAINING_CANVAS_BG": self.TRAINING_CANVAS_BG,
        }

        callbacks = {
            "on_search": self.apply_follow_search,
            "on_clear": self.clear_follow_search,
            "on_create": self.start_new_task,
            "on_toggle_show_all": self.toggle_follow_show_all,
        }

        # Build Main Layout
        layout_widgets = self.layout.build_main_layout(self.body_card, colors, callbacks)
        self.follow_wrap = layout_widgets["follow_wrap"]
        self.follow_top_card = layout_widgets["follow_top_card"]
        self.search_entry = layout_widgets["search_entry"]
        self.show_all_button = layout_widgets["show_all_button"]
        self.follow_board_card = layout_widgets["follow_board_card"]
        self.follow_canvas = layout_widgets["follow_canvas"]
        self.follow_scrollbar = layout_widgets["follow_scrollbar"]
        self.detail_form = layout_widgets["detail_form"]
        self.follow_header_canvas = layout_widgets["follow_header_canvas"]
        self.follow_scope_label = layout_widgets["follow_scope_label"]
        self.detail_card = layout_widgets["detail_card"]
        self.table_card = layout_widgets["table_card"]
        self.follow_canvas_wrap = layout_widgets["follow_canvas_wrap"]

        # Bindings
        self.follow_wrap.bind("<Configure>", self.on_follow_wrap_configure)
        self.search_entry.bind("<KeyRelease>", lambda _e: self.apply_follow_search())
        self.follow_canvas.bind("<Enter>", lambda _e: self.bind_follow_mousewheel())
        self.follow_canvas.bind("<Leave>", lambda _e: self.unbind_follow_mousewheel())
        self.follow_canvas.bind("<Button-1>", self.on_follow_canvas_click)

        # Build Form (Follow or Training)
        titles = {
            "detail_title": self.get_task_detail_title(),
            "detail_hint": self.get_default_detail_hint(),
        }

        if self.is_setup_training_section():
            form_callbacks = {
                "on_canvas_yview": self.on_training_canvas_yview,
                "on_update": self.on_follow_update,
                "on_complete_training": self.on_complete_first_training,
                "on_handoff_change": self.select_handoff,
            }
            form_widgets = self.layout.build_setup_training_detail_form(self.detail_form, colors, form_callbacks, titles)
            
            self.detail_hint = form_widgets["detail_hint"]
            self.training_merchant_label = form_widgets["training_merchant_label"]
            self.training_date_label = form_widgets["training_date_label"]
            self.training_stage_badge = form_widgets["training_stage_badge"]
            self.handoff_button_wrap = form_widgets["handoff_button_wrap"]
            self.note_box = form_widgets["note_box"]
            self.training_sections_wrap = form_widgets["training_sections_wrap"]
            self.training_canvas = form_widgets["training_canvas"]
            self.training_canvas_scrollbar = form_widgets["training_canvas_scrollbar"]
            self.follow_update_button = form_widgets["follow_update_button"]
            self.follow_complete_training_button = form_widgets["follow_complete_training_button"]
            self.history_box = form_widgets["history_box"]
            
            self.training_canvas.bind("<Configure>", self.on_training_canvas_configure)
            self.training_canvas.bind("<Enter>", lambda _e: self.set_active_scroll_target("training_canvas"))
            self.training_canvas.bind("<Leave>", lambda _e: self.clear_active_scroll_target("training_canvas"))
        else:
            form_callbacks = {
                "on_deadline_click": self.toggle_deadline_popup,
                "on_status_change": self.select_status,
                "on_save": self.on_follow_save,
                "on_update": self.on_follow_update,
                "on_start_training": self.open_setup_training_from_follow,
            }
            form_widgets = self.layout.build_follow_detail_form(self.detail_form, colors, form_callbacks, titles)
            
            self.detail_hint = form_widgets["detail_hint"]
            self.merchant_name_entry = form_widgets["merchant_name_entry"]
            self.phone_entry = form_widgets["phone_entry"]
            self.problem_entry = form_widgets["problem_entry"]
            self.handoff_from_entry = form_widgets["handoff_from_entry"]
            self.deadline_picker_button = form_widgets["deadline_picker_button"]
            self.deadline_value_hint = form_widgets["deadline_value_hint"]
            self.handoff_button_wrap = form_widgets["handoff_button_wrap"]
            self.status_buttons = form_widgets["status_buttons"]
            self.note_box = form_widgets["note_box"]
            self.follow_save_button = form_widgets["follow_save_button"]
            self.follow_update_button = form_widgets["follow_update_button"]
            self.follow_start_training_button = form_widgets["follow_start_training_button"]
            self.history_box = form_widgets["history_box"]

            self.phone_entry.bind("<KeyRelease>", self.on_phone_input)
            self.selected_status = self.get_default_task_status()
            self.select_status(self.selected_status)
            self.update_deadline_button_text()

        self.render_handoff_buttons()
        self.select_handoff(self.selected_handoff_to)
        
        if not self.is_setup_training_section():
            self.handoff_from_entry.configure(state="normal")
            self.set_entry_value(self.handoff_from_entry, self.current_display_name)
            self.handoff_from_entry.configure(state="disabled")
            self.update_follow_form_mode()
        else:
            self.refresh_follow_action_button_states()
            
        self.refresh_follow_action_button_states()
        self.load_follow_bootstrap()

    def select_status(self, status_name):
        self.selected_status = status_name

        for name, button in self.status_buttons.items():
            if name == status_name:
                meta = self.logic.status_meta.get(name, {"bg": self.BTN_ACTIVE, "text": self.TEXT_DARK})
                button.configure(
                    fg_color=meta["bg"],
                    hover_color=meta["bg"],
                    text_color=meta["text"],
                )
            else:
                button.configure(
                    fg_color=self.BTN_IDLE,
                    hover_color=self.BTN_IDLE_HOVER,
                    text_color=self.TEXT_LIGHT,
                )

    def update_follow_form_mode(self):
        is_edit_mode = bool(self.active_task and self.active_task.get("task_id"))

        if self.is_setup_training_section():
            if hasattr(self, "follow_update_button"):
                is_locked = self._follow_action_is_locked("update") or not is_edit_mode
                self.follow_update_button.configure(
                    state="disabled" if is_locked else "normal",
                    fg_color="#b8aba0" if is_locked else self.BTN_DARK,
                    hover_color="#b8aba0" if is_locked else self.BTN_DARK_HOVER,
                    text_color="#f4eee7" if is_locked else self.TEXT_LIGHT,
                )
            if hasattr(self, "follow_complete_training_button"):
                can_complete = (
                    is_edit_mode
                    and str((self.active_task or {}).get("status", "")).strip().upper() == "SET UP & TRAINING"
                    and not self._follow_action_is_locked("update")
                )
                self.follow_complete_training_button.configure(
                    state="normal" if can_complete else "disabled",
                    fg_color=self.BTN_ACTIVE if can_complete else "#d9c7aa",
                    hover_color=self.BTN_ACTIVE_HOVER if can_complete else "#d9c7aa",
                    text_color=self.TEXT_DARK if can_complete else "#8f7a62",
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
                    fg_color=self.BTN_ACTIVE,
                    hover_color=self.BTN_ACTIVE_HOVER,
                    text_color=self.TEXT_DARK,
                )

        if hasattr(self, "follow_update_button"):
            if is_edit_mode and not self._follow_action_is_locked("update"):
                self.follow_update_button.configure(
                    state="normal",
                    fg_color=self.BTN_DARK,
                    hover_color=self.BTN_DARK_HOVER,
                    text_color=self.TEXT_LIGHT,
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
                text_color=self.TEXT_LIGHT if can_start_training else "#edf3f1",
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
                fg_color="#dac6a5" if is_locked else self.BTN_ACTIVE,
                hover_color="#dac6a5" if is_locked else self.BTN_ACTIVE_HOVER,
                text_color="#8f7a62" if is_locked else self.TEXT_DARK,
            )

        if hasattr(self, "follow_save_button"):
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
        self.ui_handler.set_selected_handoffs(handoff_names)

    def toggle_handoff(self, handoff_name):
        self.ui_handler.toggle_handoff(handoff_name)

    def select_handoff(self, handoff_name):
        self.ui_handler.select_handoff(handoff_name)

    def on_phone_input(self, _event=None):
        self.ui_handler.on_phone_input(_event)

    def toggle_deadline_popup(self):
        self.ui_handler.toggle_deadline_popup()

    def close_deadline_popup(self):
        self.ui_handler.close_deadline_popup()

    def shift_deadline_popup_month(self, delta):
        self.ui_handler.shift_deadline_popup_month(delta)

    def redraw_deadline_calendar(self):
        self.ui_handler.redraw_deadline_calendar()

    def on_deadline_calendar_click(self, event):
        self.ui_handler.on_deadline_calendar_click(event)

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
        return self.logic.format_phone(digits)

    def is_valid_deadline_date(self, date_text):
        return self.logic.is_valid_deadline_date(date_text)

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
        deadline_date, deadline_time, deadline_period = self.get_confirmed_deadline_parts()
        form_data = {
            "merchant_name": self.merchant_name_entry.get(),
            "status": self.selected_status,
            "note": self.note_box.get("1.0", "end"),
            "deadline_date": deadline_date,
            "deadline_time": deadline_time,
            "deadline_period": deadline_period,
            "handoff_targets": self.selected_handoff_targets,
            "handoff_options": self.handoff_options,
            "phone": self.phone_entry.get(),
            "problem": self.problem_entry.get(),
        }
        return self.service.build_follow_payload(form_data)

    def collect_setup_training_payload(self, complete_first=False):
        form_data = {
            "handoff_targets": self.selected_handoff_targets,
            "handoff_options": self.handoff_options,
            "note": self.note_box.get("1.0", "end"),
            "training_form": self.collect_training_form_sections(),
        }
        return self.service.build_training_payload(self.active_task, form_data, complete_first=complete_first)

    def apply_follow_search(self):
        self.ui_handler.apply_follow_search()

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
                    fg_color=self.BTN_ACTIVE,
                    hover_color=self.BTN_ACTIVE_HOVER,
                    text_color=self.TEXT_DARK,
                )
            else:
                self.show_all_button.configure(
                    text="Show All: OFF",
                    fg_color=self.BTN_DARK,
                    hover_color=self.BTN_DARK_HOVER,
                    text_color=self.TEXT_LIGHT,
                )

        if hasattr(self, "include_done_switch"):
            if self.follow_include_done:
                self.include_done_switch.select()
            else:
                self.include_done_switch.deselect()

    def toggle_follow_show_all(self):
        self.ui_handler.toggle_show_all_tasks()

    def on_follow_include_done_toggle(self):
        self.follow_include_done = bool(self.include_done_switch.get())
        if self.follow_include_done and not self.follow_show_all:
            self.follow_show_all = True
        self.update_follow_filter_controls()
        self.refresh_follow_tasks(keep_selection=False)

    def clear_follow_search(self):
        self.ui_handler.clear_follow_search()

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

    def set_active_scroll_target(self, target):
        self.ui_handler.set_active_scroll_target(target)

    def clear_active_scroll_target(self, target):
        self.ui_handler.clear_active_scroll_target(target)

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

        self.renderer.draw_round_rect(
            header_canvas,
            x,
            6,
            board_right,
            6 + row_height,
            14,
            self.CANVAS_HEADER,
            self.CANVAS_HEADER,
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
                fill=self.TEXT_MUTED,
                font=("Segoe UI", 12),
            )
            canvas.configure(scrollregion=(0, 0, board_right + 10, y + 70))
            header_canvas.configure(scrollregion=(0, 0, board_right + 10, row_height + 14))
            return

        for index, task in enumerate(tasks):
            row_top = y + (index * (row_height + 6))
            row_bottom = row_top + row_height
            row_fill, row_text = self.get_task_row_theme(task, index)

            self.renderer.draw_round_rect(
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

                status_meta = self.logic.status_meta.get(task["status"], {"bg": self.BTN_ACTIVE, "text": self.TEXT_DARK})
                pill_x1 = current_x + 8
                pill_y1 = row_top + 9
                pill_x2 = board_right - 8
                pill_y2 = row_bottom - 9
                self.renderer.draw_round_rect(
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
                return self.CANVAS_OVERDUE, self.CANVAS_OVERDUE_TEXT
            if days_left == 0:
                return self.CANVAS_TODAY, self.CANVAS_TODAY_TEXT
            if days_left == 1:
                return self.CANVAS_TOMORROW, self.CANVAS_TOMORROW_TEXT
            if days_left == 2:
                return self.CANVAS_DAY_AFTER, self.CANVAS_DAY_AFTER_TEXT
        except Exception:
            pass

        return (self.CANVAS_ROW if index % 2 == 0 else self.CANVAS_ROW_ALT), self.TEXT_DARK

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
        self.ui_handler.open_setup_training_from_follow()

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
        self.ui_handler.on_follow_wrap_configure(_event)

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
                text_color=self.TEXT_MUTED,
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
                text_color=self.TEXT_DARK,
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
                    text_color=self.TEXT_MUTED,
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