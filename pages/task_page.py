import re
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from services.task_service import TASK_STATUSES
from stores.task_store import TaskStore


BG_PANEL_INNER = "#fffaf3"
BG_CARD = "#fbf5ec"
BG_ROW = "#fffaf3"
BG_ROW_ALT = "#fcf5eb"
BG_SELECTED = "#f8e3c4"
BG_MUTED = "#f7efe2"
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
SUCCESS_BG = "#d4edda"
SUCCESS_TEXT = "#155724"
ERROR_BG = "#fde2e2"
ERROR_TEXT = "#7f1d1d"

STATUS_META = {
    "FOLLOW": {"bg": "#2d6cdf", "text": "#ffffff"},
    "FOLLOW REQUEST": {"bg": "#2563eb", "text": "#ffffff"},
    "CHECK TRACKING NUMBER": {"bg": "#0f766e", "text": "#ffffff"},
    "SET UP & TRAINING": {"bg": "#9333ea", "text": "#ffffff"},
    "MISS TIP / CHARGE BACK": {"bg": "#f59e0b", "text": "#2a221d"},
    "DONE": {"bg": "#ef4444", "text": "#ffffff"},
    "DEMO": {"bg": "#ec4899", "text": "#ffffff"},
}


class TaskRowWidget(ctk.CTkFrame):
    def __init__(self, parent, on_click):
        super().__init__(
            parent,
            fg_color=BG_ROW,
            corner_radius=14,
            border_width=1,
            border_color="#e5d0ad",
        )
        self._task_id = None
        self._selected = False
        self._task = {}
        self._on_click = on_click

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=2)
        self.grid_columnconfigure(3, weight=2)
        self.grid_columnconfigure(4, weight=2)

        self.merchant_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 12, "bold"), text_color=TEXT_DARK, anchor="w", justify="left")
        self.merchant_label.grid(row=0, column=0, sticky="ew", padx=(14, 8), pady=(10, 2))

        self.problem_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 11), text_color=TEXT_MUTED, anchor="w", justify="left")
        self.problem_label.grid(row=1, column=0, sticky="ew", padx=(14, 8), pady=(0, 10))

        self.handoff_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 11), text_color=TEXT_DARK)
        self.handoff_label.grid(row=0, column=1, rowspan=2, sticky="ew", padx=8)

        self.deadline_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 11), text_color=TEXT_DARK)
        self.deadline_label.grid(row=0, column=2, rowspan=2, sticky="ew", padx=8)

        self.phone_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 11), text_color=TEXT_DARK)
        self.phone_label.grid(row=0, column=3, rowspan=2, sticky="ew", padx=8)

        self.status_badge = ctk.CTkLabel(self, text="", font=("Segoe UI", 10, "bold"), corner_radius=999, width=110, height=30)
        self.status_badge.grid(row=0, column=4, rowspan=2, sticky="e", padx=(8, 14))

        for widget in (self, self.merchant_label, self.problem_label, self.handoff_label, self.deadline_label, self.phone_label, self.status_badge):
            widget.bind("<Button-1>", self._handle_click)

    def _handle_click(self, _event=None):
        if self._task_id is not None:
            self._on_click(self._task_id)

    def set_selected(self, selected):
        self._selected = bool(selected)
        self._apply_colors()

    def update_task(self, task, alt=False):
        self._task = dict(task or {})
        self._task_id = self._task.get("task_id")
        self.merchant_label.configure(text=self._task.get("merchant_raw", ""))
        self.problem_label.configure(text=self._task.get("problem", ""))
        self.handoff_label.configure(text=self._task.get("handoff_to", "Tech Team"))
        self.deadline_label.configure(text=self._task.get("deadline", ""))
        self.phone_label.configure(text=self._task.get("phone", ""))

        meta = STATUS_META.get(self._task.get("status"), {"bg": BTN_ACTIVE, "text": TEXT_DARK})
        self.status_badge.configure(text=self._build_status_text(), fg_color=meta["bg"], text_color=meta["text"])
        self._alt = alt
        self._apply_colors()

    def _build_status_text(self):
        status = self._task.get("status", "")
        if self._task.get("is_saving"):
            return f"{status} | saving"
        if self._task.get("is_optimistic"):
            return f"{status} | pending"
        return status

    def _apply_colors(self):
        base_color = BG_SELECTED if self._selected else (BG_ROW_ALT if getattr(self, "_alt", False) else BG_ROW)
        text_color = TEXT_DARK
        if self._task.get("error"):
            base_color = ERROR_BG
            text_color = ERROR_TEXT
        self.configure(fg_color=base_color)
        self.merchant_label.configure(text_color=text_color)
        self.problem_label.configure(text_color=TEXT_MUTED if not self._task.get("error") else ERROR_TEXT)
        self.handoff_label.configure(text_color=text_color)
        self.deadline_label.configure(text_color=text_color)
        self.phone_label.configure(text_color=text_color)


class TaskPage(ctk.CTkFrame):
    def __init__(self, parent, current_user=None, store=None):
        super().__init__(
            parent,
            fg_color=BG_PANEL_INNER,
            corner_radius=18,
            border_width=1,
            border_color=BORDER_SOFT,
        )
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        self.current_user = current_user or {}
        self.current_username = str(self.current_user.get("username", "")).strip()
        self.current_full_name = str(self.current_user.get("full_name", "")).strip()

        self.store = store or TaskStore()
        self.row_widgets = {}
        self.visible_task_ids = []
        self.selected_task_id = None
        self.search_after_id = None
        self.poll_after_id = None
        self.current_query = ""
        self.current_display_name = self.current_full_name or self.current_username
        self.handoff_options = [{"username": "", "display_name": "Tech Team", "type": "TEAM"}]
        self.follow_show_all = False
        self.follow_include_done = False
        self.active_task = None

        self.build_ui()
        self.bind_events()
        self.bootstrap()

    def destroy(self):
        if self.search_after_id:
            self.after_cancel(self.search_after_id)
            self.search_after_id = None
        if self.poll_after_id:
            self.after_cancel(self.poll_after_id)
            self.poll_after_id = None
        super().destroy()

    def build_ui(self):
        self.top_card = ctk.CTkFrame(
            self,
            fg_color=BG_CARD,
            corner_radius=16,
            border_width=1,
            border_color="#e0c79d",
        )
        self.top_card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 12))
        self.top_card.grid_columnconfigure(1, weight=1)
        self.top_card.grid_columnconfigure(7, weight=1)

        ctk.CTkLabel(self.top_card, text="Search merchant", font=("Segoe UI", 12), text_color=TEXT_MUTED).grid(row=0, column=0, sticky="w", padx=(18, 8), pady=16)
        self.search_entry = ctk.CTkEntry(
            self.top_card,
            width=240,
            height=34,
            placeholder_text="Merchant name...",
            fg_color=INPUT_BG,
            border_color=INPUT_BORDER,
            text_color=TEXT_DARK,
        )
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=16)

        ctk.CTkButton(self.top_card, text="Search", width=82, height=34, corner_radius=12, fg_color=BTN_ACTIVE, hover_color=BTN_ACTIVE_HOVER, text_color=TEXT_DARK, font=("Segoe UI", 12, "bold"), command=self.apply_search).grid(row=0, column=2, sticky="w", padx=(0, 8), pady=16)
        ctk.CTkButton(self.top_card, text="Clear", width=82, height=34, corner_radius=12, fg_color=BTN_DARK, hover_color=BTN_DARK_HOVER, text_color=TEXT_LIGHT, font=("Segoe UI", 12, "bold"), command=self.clear_search).grid(row=0, column=3, sticky="w", padx=(0, 16), pady=16)
        ctk.CTkButton(self.top_card, text="Create Task", width=104, height=34, corner_radius=12, fg_color=BTN_DARK, hover_color=BTN_DARK_HOVER, text_color=TEXT_LIGHT, font=("Segoe UI", 12, "bold"), command=self.start_new_task).grid(row=0, column=4, sticky="w", padx=(0, 16), pady=16)

        self.show_all_button = ctk.CTkButton(self.top_card, text="Show All: OFF", width=110, height=34, corner_radius=12, fg_color=BTN_DARK, hover_color=BTN_DARK_HOVER, text_color=TEXT_LIGHT, font=("Segoe UI", 12, "bold"), command=self.toggle_show_all)
        self.show_all_button.grid(row=0, column=5, sticky="w", padx=(0, 10), pady=16)

        self.include_done_switch = ctk.CTkSwitch(
            self.top_card,
            text="Include Done",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_DARK,
            progress_color=BTN_ACTIVE,
            button_color=BTN_DARK,
            button_hover_color=BTN_DARK_HOVER,
            fg_color="#dbc29c",
            command=self.on_include_done_toggle,
        )
        self.include_done_switch.grid(row=0, column=6, sticky="w", padx=(0, 12), pady=16)

        self.scope_label = ctk.CTkLabel(self.top_card, text="", font=("Segoe UI", 10, "italic"), text_color=TEXT_MUTED)
        self.scope_label.grid(row=0, column=7, sticky="w", padx=(0, 10), pady=16)

        self.refresh_button = ctk.CTkButton(self.top_card, text="Refresh", width=98, height=34, corner_radius=12, fg_color=BTN_ACTIVE, hover_color=BTN_ACTIVE_HOVER, text_color=TEXT_DARK, font=("Segoe UI", 12, "bold"), command=lambda: self.request_load(force=True))
        self.refresh_button.grid(row=0, column=8, sticky="e", padx=(0, 18), pady=16)

        self.table_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color="#e0c79d")
        self.table_card.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))
        self.table_card.grid_columnconfigure(0, weight=1)
        self.table_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.table_card, text="Task Board", font=("Segoe UI", 18, "bold"), text_color=TEXT_DARK).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 10))

        self.board_scroll = ctk.CTkScrollableFrame(
            self.table_card,
            fg_color=BG_MUTED,
            corner_radius=14,
            border_width=1,
            border_color=BORDER_SOFT,
        )
        self.board_scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.board_scroll.grid_columnconfigure(0, weight=1)

        self.empty_label = ctk.CTkLabel(self.board_scroll, text="Loading tasks...", font=("Segoe UI", 12), text_color=TEXT_MUTED)
        self.empty_label.grid(row=0, column=0, sticky="w", padx=14, pady=14)

        self.detail_card = ctk.CTkScrollableFrame(self, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color="#e0c79d")
        self.detail_card.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))
        self.detail_card.grid_columnconfigure(0, weight=1)

        self._build_detail_form()

    def _build_detail_form(self):
        ctk.CTkLabel(self.detail_card, text="Task Detail", font=("Segoe UI", 18, "bold"), text_color=TEXT_DARK).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 10))
        self.detail_hint = ctk.CTkLabel(self.detail_card, text="Chon 1 task ben trai de xem chi tiet.", font=("Segoe UI", 12), text_color=TEXT_MUTED, justify="left")
        self.detail_hint.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

        self.merchant_name_entry = self.create_labeled_entry(2, "Merchant Name", "SAPPHIRE NAILS 45805")
        self.phone_entry = self.create_labeled_entry(3, "Phone", "(012) 345-6789")
        self.problem_entry = self.create_labeled_entry(4, "Problem", "Setup + 1st training")
        self.handoff_from_entry = self.create_labeled_entry(5, "Nguoi ban giao", "Current Display Name", state="disabled")

        self.create_section_label(6, "Nguoi nhan ban giao")
        self.handoff_combo = ctk.CTkComboBox(self.detail_card, values=["Tech Team"], height=36, fg_color=INPUT_BG, border_color=INPUT_BORDER, button_color=BTN_ACTIVE, button_hover_color=BTN_ACTIVE_HOVER, text_color=TEXT_DARK, dropdown_fg_color=INPUT_BG, dropdown_text_color=TEXT_DARK)
        self.handoff_combo.grid(row=7, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.handoff_combo.set("Tech Team")

        self.create_section_label(8, "Status")
        self.status_combo = ctk.CTkComboBox(self.detail_card, values=list(TASK_STATUSES), height=36, fg_color=INPUT_BG, border_color=INPUT_BORDER, button_color=BTN_ACTIVE, button_hover_color=BTN_ACTIVE_HOVER, text_color=TEXT_DARK, dropdown_fg_color=INPUT_BG, dropdown_text_color=TEXT_DARK)
        self.status_combo.grid(row=9, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.status_combo.set(TASK_STATUSES[0])

        deadline_wrap = ctk.CTkFrame(self.detail_card, fg_color="transparent")
        deadline_wrap.grid(row=10, column=0, sticky="ew", padx=18, pady=(2, 10))
        ctk.CTkLabel(deadline_wrap, text="Ngay hen", font=("Segoe UI", 12, "bold"), text_color=TEXT_DARK).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ctk.CTkLabel(deadline_wrap, text="Gio hen", font=("Segoe UI", 12, "bold"), text_color=TEXT_DARK).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 6))

        self.deadline_date_entry = ctk.CTkEntry(deadline_wrap, width=128, height=36, placeholder_text="DD-MM-YYYY", fg_color=INPUT_BG, border_color=INPUT_BORDER, text_color=TEXT_DARK)
        self.deadline_date_entry.grid(row=1, column=0, sticky="w")

        self.deadline_time_combo = ctk.CTkComboBox(deadline_wrap, values=["08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "01:00", "01:30", "02:00", "02:30", "03:00", "03:30", "04:00", "04:30", "05:00", "05:30", "06:00", "06:30", "07:00", "07:30"], width=108, height=36, fg_color=INPUT_BG, border_color=INPUT_BORDER, button_color=BTN_ACTIVE, button_hover_color=BTN_ACTIVE_HOVER, text_color=TEXT_DARK, dropdown_fg_color=INPUT_BG, dropdown_text_color=TEXT_DARK)
        self.deadline_time_combo.grid(row=1, column=1, sticky="w", padx=(10, 8))
        self.deadline_time_combo.set("02:00")
        self.deadline_time_combo.configure(command=lambda _v=None: self.refresh_handoff_options_from_deadline())

        self.deadline_period_combo = ctk.CTkComboBox(deadline_wrap, values=["AM", "PM"], width=72, height=36, fg_color=INPUT_BG, border_color=INPUT_BORDER, button_color=BTN_ACTIVE, button_hover_color=BTN_ACTIVE_HOVER, text_color=TEXT_DARK, dropdown_fg_color=INPUT_BG, dropdown_text_color=TEXT_DARK)
        self.deadline_period_combo.grid(row=1, column=2, sticky="w")
        self.deadline_period_combo.set("AM")
        self.deadline_period_combo.configure(command=lambda _v=None: self.refresh_handoff_options_from_deadline())

        self.create_section_label(11, "Note")
        self.note_box = ctk.CTkTextbox(self.detail_card, height=110, fg_color=INPUT_BG, border_color=INPUT_BORDER, border_width=1, text_color=TEXT_DARK, corner_radius=12)
        self.note_box.grid(row=12, column=0, sticky="ew", padx=18, pady=(0, 12))

        action_row = ctk.CTkFrame(self.detail_card, fg_color="transparent")
        action_row.grid(row=13, column=0, sticky="ew", padx=18, pady=(0, 14))
        self.save_button = ctk.CTkButton(action_row, text="Save", width=110, height=40, corner_radius=12, fg_color=BTN_ACTIVE, hover_color=BTN_ACTIVE_HOVER, text_color=TEXT_DARK, font=("Segoe UI", 13, "bold"), command=self.on_save)
        self.save_button.pack(side="left", padx=(0, 8))
        self.update_button = ctk.CTkButton(action_row, text="Update", width=110, height=40, corner_radius=12, fg_color=BTN_DARK, hover_color=BTN_DARK_HOVER, text_color=TEXT_LIGHT, font=("Segoe UI", 13, "bold"), command=self.on_update)
        self.update_button.pack(side="left")

        self.feedback_label = ctk.CTkLabel(self.detail_card, text="", font=("Segoe UI", 11, "bold"), text_color=TEXT_MUTED)
        self.feedback_label.grid(row=14, column=0, sticky="w", padx=18, pady=(0, 8))

        self.create_section_label(15, "History / Log")
        self.history_box = ctk.CTkScrollableFrame(self.detail_card, height=180, fg_color="#fff7ed", border_width=1, border_color=INPUT_BORDER, corner_radius=12)
        self.history_box.grid(row=16, column=0, sticky="ew", padx=18, pady=(0, 18))

        self.handoff_from_entry.configure(state="normal")
        self.set_entry_value(self.handoff_from_entry, self.current_display_name)
        self.handoff_from_entry.configure(state="disabled")
        self.clear_form()

    def create_labeled_entry(self, row, label_text, placeholder, state="normal"):
        wrap = ctk.CTkFrame(self.detail_card, fg_color="transparent")
        wrap.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(wrap, text=label_text, font=("Segoe UI", 12, "bold"), text_color=TEXT_DARK).grid(row=0, column=0, sticky="w", pady=(0, 6))
        entry = ctk.CTkEntry(wrap, height=38, placeholder_text=placeholder, fg_color=INPUT_BG, border_color=INPUT_BORDER, text_color=TEXT_DARK, state=state)
        entry.grid(row=1, column=0, sticky="ew")
        return entry

    def create_section_label(self, row, text):
        ctk.CTkLabel(self.detail_card, text=text, font=("Segoe UI", 12, "bold"), text_color=TEXT_DARK).grid(row=row, column=0, sticky="w", padx=18, pady=(2, 6))

    def bind_events(self):
        self.search_entry.bind("<KeyRelease>", self.on_search_key_release)
        self.phone_entry.bind("<KeyRelease>", self.on_phone_input)
        self.deadline_date_entry.bind("<FocusOut>", self.on_deadline_focus_out)

    def bootstrap(self):
        self.update_filter_controls()
        self.store.set_view(show_all=self.follow_show_all, include_done=self.follow_include_done)
        self.store.load_handoff_options(self.current_username, task_date="")
        self.request_load(force=False)
        self.poll_store_events()

    def on_deadline_focus_out(self, _event=None):
        self.refresh_handoff_options_from_deadline()

    def refresh_handoff_options_from_deadline(self):
        if not self.current_username:
            return
        deadline_date = self.deadline_date_entry.get().strip()
        if not deadline_date or not self.is_valid_deadline_date(deadline_date):
            return
        self.store.load_handoff_options(
            self.current_username,
            task_date=deadline_date,
            task_time=self.deadline_time_combo.get().strip(),
            task_period=self.deadline_period_combo.get().strip(),
        )

    def poll_store_events(self):
        for event in self.store.drain_events():
            self.handle_store_event(event)
        self.poll_after_id = self.after(120, self.poll_store_events)

    def handle_store_event(self, event):
        event_type = event.get("type")
        if event_type == "tasks_loaded":
            self.update_scope_hint(event.get("search_scope"))
            self.apply_search(use_cached=True)
            return

        if event_type == "tasks_loading":
            self.feedback_label.configure(text="Dang refresh du lieu nen...")
            return

        if event_type == "tasks_load_failed":
            messagebox.showerror("Task Follow", event.get("message", "Khong load duoc task."))
            self.feedback_label.configure(text=event.get("message", ""))
            return

        if event_type == "handoff_options_loaded":
            self.handoff_options = event.get("options") or self.handoff_options
            self.current_display_name = event.get("current_display_name") or self.current_display_name
            self.handoff_combo.configure(values=[item["display_name"] for item in self.handoff_options])
            if self.handoff_options:
                self.handoff_combo.set(self.handoff_options[0]["display_name"])
            self.handoff_from_entry.configure(state="normal")
            self.set_entry_value(self.handoff_from_entry, self.current_display_name)
            self.handoff_from_entry.configure(state="disabled")
            return

        if event_type == "task_upserted":
            item = event.get("item") or {}
            self.upsert_row_widget(item)
            self.rebuild_visible_rows(preserve_selection=True)
            if self.selected_task_id == item.get("task_id"):
                self.load_task_into_form(item, keep_feedback=True)
            return

        if event_type == "task_removed":
            item_id = event.get("item_id")
            widget = self.row_widgets.pop(item_id, None)
            if widget is not None:
                widget.destroy()
            self.rebuild_visible_rows(preserve_selection=True)
            if self.selected_task_id == item_id:
                self.selected_task_id = None
                self.active_task = None
                self.clear_form()
            return

        if event_type == "task_detail_loaded":
            item = event.get("item") or {}
            self.upsert_row_widget(item)
            if self.selected_task_id == item.get("task_id"):
                self.load_task_into_form(item, keep_feedback=True)
            return

        if event_type == "task_detail_failed":
            messagebox.showerror("Task Follow", event.get("message", "Khong load duoc task detail."))
            return

        if event_type == "task_save_succeeded":
            self.feedback_label.configure(text=event.get("message", ""), text_color=SUCCESS_TEXT)
            return

        if event_type == "task_save_failed":
            self.feedback_label.configure(text=event.get("message", ""), text_color=ERROR_TEXT)
            messagebox.showerror("Task Follow", event.get("message", "Save failed."))
            rollback_item = event.get("rollback_item")
            if rollback_item and event.get("action") == "update":
                self.upsert_row_widget(rollback_item)
                self.rebuild_visible_rows(preserve_selection=True)
                if self.selected_task_id == rollback_item.get("task_id"):
                    self.load_task_into_form(rollback_item, keep_feedback=True)

    def request_load(self, force=False):
        self.store.set_view(show_all=self.follow_show_all, include_done=self.follow_include_done)
        self.store.load(self.current_username, force=force, background_if_stale=True)

    def on_search_key_release(self, _event=None):
        if self.search_after_id:
            self.after_cancel(self.search_after_id)
        self.search_after_id = self.after(400, self.apply_search)

    def apply_search(self, use_cached=False):
        if self.search_after_id and not use_cached:
            self.after_cancel(self.search_after_id)
            self.search_after_id = None
        self.current_query = self.search_entry.get().strip()
        self.rebuild_visible_rows(preserve_selection=True)

    def clear_search(self):
        self.search_entry.delete(0, "end")
        self.current_query = ""
        self.rebuild_visible_rows(preserve_selection=True)

    def toggle_show_all(self):
        self.follow_show_all = not self.follow_show_all
        if not self.follow_show_all:
            self.follow_include_done = False
        self.update_filter_controls()
        self.request_load(force=False)

    def on_include_done_toggle(self):
        self.follow_include_done = bool(self.include_done_switch.get())
        if self.follow_include_done and not self.follow_show_all:
            self.follow_show_all = True
        self.update_filter_controls()
        self.request_load(force=False)

    def update_filter_controls(self):
        if self.follow_show_all:
            self.show_all_button.configure(text="Show All: ON", fg_color=BTN_ACTIVE, hover_color=BTN_ACTIVE_HOVER, text_color=TEXT_DARK)
        else:
            self.show_all_button.configure(text="Show All: OFF", fg_color=BTN_DARK, hover_color=BTN_DARK_HOVER, text_color=TEXT_LIGHT)

        if self.follow_include_done:
            self.include_done_switch.select()
        else:
            self.include_done_switch.deselect()

        self.update_scope_hint(self.store.search_scope)

    def update_scope_hint(self, scope):
        normalized = str(scope or "board").strip() or "board"
        if normalized == "show_all_with_done":
            text = "Show all mode: active task | Co hien Done"
        elif normalized == "show_all_active_not_done":
            text = "Show all mode: active task | Done hidden"
        else:
            text = "Board mode: active task | Done hidden | Deadline in 3 days"
        self.scope_label.configure(text=text)

    def rebuild_visible_rows(self, preserve_selection=False):
        tasks = self.store.filter_local(self.current_query)
        self.visible_task_ids = [item["task_id"] for item in tasks if item.get("task_id") is not None]

        if not tasks:
            self.empty_label.configure(
                text="Khong co task nao khop bo loc hien tai." if not self.current_query else "Khong tim thay task nao trong cache hien tai."
            )
            self.empty_label.grid(row=0, column=0, sticky="w", padx=14, pady=14)
        else:
            self.empty_label.grid_remove()

        for index, task in enumerate(tasks):
            self.upsert_row_widget(task, alt=bool(index % 2))

        visible_set = set(self.visible_task_ids)
        for item_id, widget in list(self.row_widgets.items()):
            if item_id not in visible_set:
                widget.grid_remove()

        for index, task_id in enumerate(self.visible_task_ids):
            widget = self.row_widgets.get(task_id)
            if widget is None:
                continue
            widget.grid(row=index, column=0, sticky="ew", padx=10, pady=(0, 8))
            widget.set_selected(task_id == self.selected_task_id)

        if not preserve_selection:
            self.selected_task_id = None

        if self.selected_task_id not in visible_set:
            self.selected_task_id = self.visible_task_ids[0] if self.visible_task_ids else None
            if self.selected_task_id is not None:
                self.select_task(self.selected_task_id)
            elif not tasks:
                self.active_task = None
                self.clear_form()
        elif preserve_selection and self.selected_task_id is not None:
            self.select_task(self.selected_task_id, load_detail=False)

    def upsert_row_widget(self, task, alt=False):
        task_id = task.get("task_id")
        if task_id is None:
            return
        widget = self.row_widgets.get(task_id)
        if widget is None:
            widget = TaskRowWidget(self.board_scroll, on_click=self.select_task)
            self.row_widgets[task_id] = widget
        widget.update_task(task, alt=alt)
        widget.set_selected(task_id == self.selected_task_id)

    def select_task(self, task_id, load_detail=True):
        self.selected_task_id = task_id
        for current_id, widget in self.row_widgets.items():
            widget.set_selected(current_id == task_id)

        item = self.store.get_by_id(task_id)
        if not item:
            return
        self.load_task_into_form(item)
        if load_detail:
            self.store.ensure_detail(task_id, action_by=self.current_username)

    def load_task_into_form(self, task, keep_feedback=False):
        self.active_task = dict(task or {})
        self.selected_task_id = self.active_task.get("task_id")
        self.detail_hint.configure(text=f"Dang xem task: {self.active_task.get('merchant_name') or self.active_task.get('merchant_raw')}")
        self.set_entry_value(self.merchant_name_entry, self.active_task.get("merchant_raw", ""))
        self.set_entry_value(self.phone_entry, self.active_task.get("phone", ""))
        self.set_entry_value(self.problem_entry, self.active_task.get("problem", ""))
        self.handoff_from_entry.configure(state="normal")
        self.set_entry_value(self.handoff_from_entry, self.active_task.get("handoff_from", self.current_display_name))
        self.handoff_from_entry.configure(state="disabled")
        self.handoff_combo.set(self.active_task.get("handoff_to", "Tech Team"))
        self.status_combo.set(self.active_task.get("status", TASK_STATUSES[0]))
        self.set_entry_value(self.deadline_date_entry, self.active_task.get("deadline_date", ""))
        if self.current_username and self.active_task.get("deadline_date"):
            self.store.load_handoff_options(
                self.current_username,
                task_date=self.active_task.get("deadline_date"),
                task_time=self.active_task.get("deadline_time", ""),
                task_period=self.active_task.get("deadline_period", ""),
            )
        self.deadline_time_combo.set(self.active_task.get("deadline_time", "02:00"))
        self.deadline_period_combo.set(self.active_task.get("deadline_period", "AM"))
        self.note_box.delete("1.0", "end")
        self.note_box.insert("1.0", self.active_task.get("note", ""))
        self.render_history(self.active_task.get("history") or [])
        self.update_form_mode()
        if not keep_feedback:
            self.feedback_label.configure(text="", text_color=TEXT_MUTED)

    def clear_form(self):
        self.active_task = None
        self.detail_hint.configure(text="Dang tao task moi hoac chua co task nao duoc chon.")
        self.set_entry_value(self.merchant_name_entry, "")
        self.set_entry_value(self.phone_entry, "")
        self.set_entry_value(self.problem_entry, "")
        self.handoff_from_entry.configure(state="normal")
        self.set_entry_value(self.handoff_from_entry, self.current_display_name)
        self.handoff_from_entry.configure(state="disabled")
        if self.handoff_options:
            self.handoff_combo.set(self.handoff_options[0]["display_name"])
        self.status_combo.set(TASK_STATUSES[0])
        self.set_entry_value(self.deadline_date_entry, "")
        self.deadline_time_combo.set("02:00")
        self.deadline_period_combo.set("AM")
        self.note_box.delete("1.0", "end")
        self.render_history([])
        self.update_form_mode()

    def start_new_task(self):
        self.selected_task_id = None
        for widget in self.row_widgets.values():
            widget.set_selected(False)
        self.clear_form()
        self.detail_hint.configure(text="Dang tao task moi. Nhap thong tin roi bam Save.")

    def update_form_mode(self):
        is_edit_mode = bool(self.active_task and self.active_task.get("task_id"))
        if is_edit_mode:
            self.save_button.configure(state="disabled", fg_color="#d9c7aa", hover_color="#d9c7aa", text_color="#8f7a62")
            self.update_button.configure(state="normal", fg_color=BTN_DARK, hover_color=BTN_DARK_HOVER, text_color=TEXT_LIGHT)
        else:
            self.save_button.configure(state="normal", fg_color=BTN_ACTIVE, hover_color=BTN_ACTIVE_HOVER, text_color=TEXT_DARK)
            self.update_button.configure(state="disabled", fg_color="#b8aba0", hover_color="#b8aba0", text_color="#f4eee7")

    def render_history(self, history_items):
        for widget in self.history_box.winfo_children():
            widget.destroy()

        if not history_items:
            ctk.CTkLabel(self.history_box, text="Chua co history.", font=("Segoe UI", 12), text_color=TEXT_MUTED).pack(anchor="w", padx=8, pady=8)
            return

        for item in history_items:
            card = ctk.CTkFrame(self.history_box, fg_color="#fffaf3", corner_radius=10, border_width=1, border_color="#e6cfab")
            card.pack(fill="x", padx=6, pady=5)
            ctk.CTkLabel(card, text=f"{item.get('user', '')} | {item.get('time', '')}", font=("Segoe UI", 12, "bold"), text_color=TEXT_DARK).pack(anchor="w", padx=10, pady=(8, 4))
            ctk.CTkLabel(card, text=item.get("note", ""), font=("Segoe UI", 12), text_color=TEXT_MUTED, justify="left", wraplength=330).pack(anchor="w", padx=10, pady=(0, 8))

    def on_phone_input(self, _event=None):
        digits = re.sub(r"\D", "", self.phone_entry.get())[:10]
        formatted = self.format_phone(digits)
        self.phone_entry.delete(0, "end")
        self.phone_entry.insert(0, formatted)

    def format_phone(self, digits):
        if not digits:
            return ""
        if len(digits) <= 3:
            return f"({digits}"
        if len(digits) <= 6:
            return f"({digits[:3]}) {digits[3:]}"
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:10]}"

    def set_entry_value(self, entry, value):
        entry.delete(0, "end")
        if value:
            entry.insert(0, value)

    def get_handoff_option(self, display_name):
        target = str(display_name or "").strip()
        for option in self.handoff_options:
            if option["display_name"] == target:
                return option
        return self.handoff_options[0] if self.handoff_options else {"username": "", "display_name": "Tech Team", "type": "TEAM"}

    def collect_form_payload(self):
        merchant_raw_text = self.merchant_name_entry.get().strip()
        note = self.note_box.get("1.0", "end").strip()
        deadline_date = self.deadline_date_entry.get().strip()
        status = self.status_combo.get().strip()
        handoff_option = self.get_handoff_option(self.handoff_combo.get())

        if not merchant_raw_text:
            return None, "Merchant Name khong duoc de trong."
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
            "handoff_to_type": handoff_option.get("type", "TEAM"),
            "handoff_to_username": handoff_option.get("username", ""),
            "handoff_to_display_name": handoff_option.get("display_name", "Tech Team"),
            "status": status,
            "deadline_date": deadline_date,
            "deadline_time": self.deadline_time_combo.get().strip(),
            "deadline_period": self.deadline_period_combo.get().strip(),
            "note": note,
        }
        return payload, ""

    def is_valid_deadline_date(self, date_text):
        try:
            datetime.strptime(date_text, "%d-%m-%Y")
            return True
        except ValueError:
            return False

    def on_save(self):
        if self.active_task and self.active_task.get("task_id"):
            messagebox.showwarning("Task Follow", "Dang o che do update. Muon tao task moi thi bam Create Task truoc.")
            return

        payload, error_message = self.collect_form_payload()
        if error_message:
            messagebox.showwarning("Task Follow", error_message)
            return

        self.feedback_label.configure(text="Dang tao task nen...", text_color=TEXT_MUTED)
        temp_id = self.store.create_item(payload, actor_display_name=self.current_display_name, action_by=self.current_username)
        self.rebuild_visible_rows(preserve_selection=True)
        self.select_task(temp_id, load_detail=False)

    def on_update(self):
        if not self.active_task or not self.active_task.get("task_id"):
            messagebox.showwarning("Task Follow", "Hay chon task can update.")
            return

        payload, error_message = self.collect_form_payload()
        if error_message:
            messagebox.showwarning("Task Follow", error_message)
            return

        self.feedback_label.configure(text="Dang update task nen...", text_color=TEXT_MUTED)
        self.store.update_item(
            self.active_task["task_id"],
            payload,
            actor_display_name=self.current_display_name,
            action_by=self.current_username,
        )
