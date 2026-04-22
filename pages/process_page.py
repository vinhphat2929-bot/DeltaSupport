from copy import deepcopy
from datetime import datetime
import time
from tkinter import messagebox

import customtkinter as ctk

from stores.task_store import TaskStore
from pages.process.service import ProcessService
from pages.process.logic import ProcessLogic
from pages.process.renderers import ProcessRenderer
from pages.process.layout import ProcessLayout
from pages.process.follow_controller import TaskFollowController
from pages.process.setup_training_controller import TaskSetupTrainingController
from pages.process.handlers_ui import ProcessUIHandler
from pages.task_report_page import TaskReportPage


class ProcessPage(ctk.CTkFrame):
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
    CANVAS_PAST_DUE = "#171717"
    CANVAS_PAST_DUE_TEXT = "#f8fafc"
    CANVAS_OVERDUE = "#fde2e2"
    CANVAS_OVERDUE_TEXT = "#7f1d1d"
    CANVAS_TODAY = "#fde2e2"
    CANVAS_TODAY_TEXT = "#7f1d1d"
    CANVAS_TOMORROW = "#ffe7ad"
    CANVAS_TOMORROW_TEXT = "#6b3f00"
    CANVAS_DAY_AFTER = "#dbeafe"
    CANVAS_DAY_AFTER_TEXT = "#1d4ed8"

    TRAINING_RESULT_OPTIONS = ["", "DONE", "X"]
    TRAINING_CANVAS_BG = "#fffaf4"
    TRAINING_BANNER_BG = "#f1dec0"
    TRAINING_SUBHEADER_BG = "#e3c998"
    TRAINING_GROUP_BG = "#f6eee2"

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
        self.follow_controller = TaskFollowController(self)
        self.setup_training_controller = TaskSetupTrainingController(self)

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
        self.follow_click_bind_id = None
        self.follow_poll_after_id = None
        self.follow_refresh_button = None
        self.follow_action_cooldown_ms = 3000
        self.follow_action_ready_at = {}
        self.follow_action_inflight = set()
        self.follow_action_after_ids = {}
        self.follow_layout_after_id = None
        self.follow_layout_pending_size = None
        self.follow_layout_applied_size = (0, 0)
        self.follow_canvas_redraw_after_id = None
        self.follow_canvas_force_redraw = False
        self.follow_canvas_last_render_size = (0, 0)
        self.follow_board_render_signature = None
        self.follow_canvas_row_meta = {}
        self.follow_canvas_active_task_id = None
        self.follow_visible_range = (0, 100)
        self.training_visible_range = (0, 100)
        self.follow_board_virtual_buffer_rows = 10
        self.follow_board_suppress_selection_scroll = False
        self.follow_search_after_id = None
        self.follow_search_debounce_ms = 300
        self.follow_search_pending_query = ""
        self.follow_search_last_applied_query = ""
        self.follow_tasks = []
        self.filtered_follow_tasks = []
        self.active_task = None
        self.training_popup = None
        self.training_info_popup = None
        self.training_result_vars = {}
        self.training_note_entries = {}
        self.training_note_values = {}
        self.training_row_cards = []
        self.training_form_draft_sections = []
        self.training_canvas = None
        self.training_canvas_window_map = {}
        self.training_canvas_row_layout = []
        self.training_canvas_flat_rows = []
        self.training_canvas_content_height = 0
        self.training_canvas_after_id = None
        self.training_note_reflow_after_id = None
        self.training_canvas_last_render_key = None
        self.detail_scroll_after_id = None
        self.follow_scroll_restore_after_id = None
        self.follow_search_scope = "board"
        self.follow_show_all = False
        self.follow_include_done = False
        self.follow_board_min_height = 180
        self.follow_board_max_height = 520
        self.follow_board_height = self.follow_board_min_height
        self.follow_board_scroll_enabled = False
        self.follow_detail_pending_id = None
        self.follow_form_render_signature = None
        self.follow_history_render_signature = None
        self.setup_training_form_render_signature = None
        self.rendered_section = None
        self.page_active = True
        self.debug_background_jobs = False
        self.task_section_hosts = {}
        self.task_section_widget_cache = {}
        self.task_section_state_cache = {}
        self.task_section_widget_names = [
            "follow_wrap",
            "follow_top_card",
            "search_entry",
            "show_all_button",
            "include_done_switch",
            "follow_board_card",
            "follow_canvas",
            "follow_scrollbar",
            "detail_form",
            "follow_header_canvas",
            "follow_scope_label",
            "detail_card",
            "table_card",
            "follow_canvas_wrap",
            "detail_hint",
            "merchant_name_entry",
            "phone_entry",
            "tracking_number_entry",
            "tracking_number_row",
            "track_ups_button_row",
            "track_ups_button",
            "problem_entry",
            "handoff_from_entry",
            "deadline_picker_button",
            "deadline_value_hint",
            "handoff_button_wrap",
            "status_buttons",
            "note_box",
            "follow_save_button",
            "follow_update_button",
            "follow_delete_button",
            "history_box",
            "training_merchant_label",
            "training_date_label",
            "training_stage_badge",
            "start_training_button",
            "tab_wrap",
            "checklist_tabs",
            "training_sections_wrap",
            "training_canvas",
            "training_list_frame",
            "action_row",
            "complete_tab_button",
            "follow_complete_training_button",
            "view_training_info_button",
        ]
        self.task_section_state_names = [
            "active_task",
            "selected_status",
            "selected_handoff_to",
            "selected_handoff_targets",
            "confirmed_deadline_date",
            "confirmed_deadline_time",
            "pending_deadline_date",
            "pending_deadline_time",
            "follow_search_scope",
            "follow_search_pending_query",
            "follow_search_last_applied_query",
            "follow_layout_mode",
            "follow_layout_pending_size",
            "follow_layout_applied_size",
            "follow_canvas_last_render_size",
            "follow_board_render_signature",
            "follow_canvas_row_meta",
            "follow_canvas_active_task_id",
            "follow_visible_range",
            "training_visible_range",
            "follow_board_height",
            "follow_board_scroll_enabled",
            "canvas_row_hits",
            "follow_tasks",
            "filtered_follow_tasks",
            "follow_detail_pending_id",
            "follow_form_render_signature",
            "follow_history_render_signature",
            "setup_training_form_render_signature",
            "is_training_started",
            "completed_tabs",
            "current_training_tab",
            "training_form_draft_sections",
            "training_note_values",
            "training_result_vars",
            "training_note_entries",
            "training_canvas_window_map",
            "training_canvas_row_layout",
            "training_canvas_flat_rows",
            "training_canvas_content_height",
            "training_canvas_last_render_key",
        ]
        self.current_task_section = (
            initial_section if initial_section in {"follow", "setup_training"} else "follow"
        )
        self.pending_focus_task_id = int(initial_task_id) if initial_task_id not in (None, "") else None

        if self.pending_focus_task_id:
            self.follow_show_all = True

        self.build_ui()
        self.bind("<Map>", self._on_page_map, add="+")
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

    def _debug_job(self, label, message):
        if not getattr(self, "debug_background_jobs", False):
            return
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        section = self.rendered_section or self.current_task_section or "unknown"
        print(f"[{timestamp}] [ProcessPage:{section}] {label} | {message}")

    def is_page_active_and_visible(self, require_visible=True):
        if not getattr(self, "page_active", False):
            return False
        if not self.winfo_exists():
            return False
        if not require_visible:
            return True
        try:
            return bool(self.winfo_ismapped())
        except Exception:
            return False

    def _can_run_page_job(self, label, require_visible=True):
        exists = False
        visible = False
        try:
            exists = bool(self.winfo_exists())
        except Exception:
            exists = False
        active = bool(getattr(self, "page_active", False))
        if exists:
            try:
                visible = bool(self.winfo_ismapped())
            except Exception:
                visible = False

        allowed = exists and active and (visible if require_visible else True)
        if not allowed:
            self._debug_job(
                label,
                f"skip exists={exists} active={active} visible={visible} require_visible={require_visible}",
            )
        return allowed

    def _cancel_after_slot(self, slot_name, label):
        after_id = getattr(self, slot_name, None)
        if not after_id:
            return False
        try:
            self.after_cancel(after_id)
            self._debug_job(label, f"cancel id={after_id}")
        except Exception as exc:
            self._debug_job(label, f"cancel_failed id={after_id} error={exc}")
        setattr(self, slot_name, None)
        return True

    def _schedule_after_slot(self, slot_name, delay_ms, callback, label, require_visible=True):
        self._cancel_after_slot(slot_name, label)
        job_ref = {}

        def _wrapped():
            scheduled_id = job_ref.get("id")
            if getattr(self, slot_name, None) != scheduled_id:
                self._debug_job(label, f"skip_stale id={scheduled_id} current={getattr(self, slot_name, None)}")
                return
            setattr(self, slot_name, None)
            self._debug_job(label, f"callback id={scheduled_id}")
            if not self._can_run_page_job(label, require_visible=require_visible):
                return
            callback()

        job_ref["id"] = self.after(delay_ms, _wrapped)
        setattr(self, slot_name, job_ref["id"])
        self._debug_job(label, f"schedule id={job_ref['id']} delay_ms={delay_ms}")
        return job_ref["id"]

    def _cancel_follow_action_state_refresh(self, action_key):
        after_id = self.follow_action_after_ids.get(action_key)
        if not after_id:
            self.follow_action_after_ids[action_key] = None
            return False
        try:
            self.after_cancel(after_id)
            self._debug_job(f"follow_action:{action_key}", f"cancel id={after_id}")
        except Exception as exc:
            self._debug_job(f"follow_action:{action_key}", f"cancel_failed id={after_id} error={exc}")
        self.follow_action_after_ids[action_key] = None
        return True

    def _cancel_process_jobs(self, include_poll=True):
        if include_poll:
            self._cancel_after_slot("follow_poll_after_id", "follow_poll")
        self._cancel_after_slot("follow_layout_after_id", "follow_layout")
        self._cancel_after_slot("follow_canvas_redraw_after_id", "follow_canvas_redraw")
        self._cancel_after_slot("follow_search_after_id", "follow_search")
        self._cancel_after_slot("training_canvas_after_id", "training_canvas_refresh")
        self._cancel_after_slot("training_note_reflow_after_id", "training_note_reflow")
        self._cancel_after_slot("detail_scroll_after_id", "detail_scroll")
        self._cancel_after_slot("follow_scroll_restore_after_id", "follow_scroll_restore")
        for action_key in list(self.follow_action_after_ids.keys()):
            self._cancel_follow_action_state_refresh(action_key)

    def schedule_detail_scroll_update(self, delay_ms=1):
        if not hasattr(self, "update_detail_scrollregion"):
            return
        self._schedule_after_slot(
            "detail_scroll_after_id",
            max(1, int(delay_ms)),
            self.update_detail_scrollregion,
            "detail_scroll",
            require_visible=True,
        )

    def schedule_follow_search_apply(self, delay_ms=None):
        if not hasattr(self, "search_entry") or self.search_entry is None:
            return
        try:
            if not self.search_entry.winfo_exists():
                return
            self.follow_search_pending_query = self.search_entry.get().strip().lower()
        except Exception:
            return

        self._schedule_after_slot(
            "follow_search_after_id",
            max(1, int(delay_ms or self.follow_search_debounce_ms)),
            self._flush_follow_search_apply,
            "follow_search",
            require_visible=True,
        )

    def _flush_follow_search_apply(self):
        if not self._can_run_page_job("follow_search_flush", require_visible=True):
            return
        if not hasattr(self, "search_entry") or self.search_entry is None or not self.search_entry.winfo_exists():
            return

        current_query = self.search_entry.get().strip().lower()
        if current_query != getattr(self, "follow_search_pending_query", ""):
            self.follow_search_pending_query = current_query
            self.schedule_follow_search_apply(delay_ms=120)
            return

        if current_query == self.follow_search_last_applied_query:
            return

        self.apply_follow_search()

    def schedule_follow_scroll_restore(self, canvas, target_yview):
        def _restore():
            try:
                if canvas.winfo_exists():
                    canvas.yview_moveto(target_yview)
            except Exception as exc:
                self._debug_job("follow_scroll_restore", f"restore_failed error={exc}")

        self._schedule_after_slot(
            "follow_scroll_restore_after_id",
            1,
            _restore,
            "follow_scroll_restore",
            require_visible=True,
        )

    def destroy(self):
        self.on_page_hide()
        self.follow_action_after_ids = {}
        super().destroy()

    def _copy_task_section_state_value(self, value):
        try:
            return deepcopy(value)
        except Exception:
            return value

    def _get_task_section_host(self, section_key):
        host = self.task_section_hosts.get(section_key)
        if host is not None and host.winfo_exists():
            return host

        host = ctk.CTkFrame(self.body_card, fg_color="transparent")
        host.grid(row=0, column=0, sticky="nsew")
        host.grid_columnconfigure(0, weight=1)
        host.grid_rowconfigure(0, weight=1)
        host.grid_remove()
        self.task_section_hosts[section_key] = host
        return host

    def _hide_task_section_hosts(self):
        for host in list(self.task_section_hosts.values()):
            if host is None:
                continue
            try:
                if host.winfo_exists():
                    host.grid_remove()
            except Exception:
                continue

    def _cache_task_section_context(self, section_key):
        if section_key not in {"follow", "setup_training"}:
            return

        host = self.task_section_hosts.get(section_key)
        if host is None or not host.winfo_exists():
            return

        self.task_section_widget_cache[section_key] = {
            name: getattr(self, name, None)
            for name in self.task_section_widget_names
        }
        self.task_section_state_cache[section_key] = {
            name: self._copy_task_section_state_value(getattr(self, name, None))
            for name in self.task_section_state_names
        }

    def _restore_task_section_context(self, section_key):
        for name, value in self.task_section_widget_cache.get(section_key, {}).items():
            setattr(self, name, value)
        for name, value in self.task_section_state_cache.get(section_key, {}).items():
            setattr(self, name, self._copy_task_section_state_value(value))

    def _has_cached_task_section(self, section_key):
        host = self.task_section_hosts.get(section_key)
        return (
            section_key in self.task_section_widget_cache
            and host is not None
            and host.winfo_exists()
        )

    def render_section(self, section_key):
        self._debug_job("render_section", f"switch_to={section_key}")
        previous_section = self.rendered_section
        if previous_section in {"follow", "setup_training"}:
            self._cache_task_section_context(previous_section)
        self._cancel_process_jobs(include_poll=True)
        self.active_scroll_target = None
        self.rendered_section = section_key
        section_map = {
            "report": ("Report", "Khu vuc nay se build function report task."),
            "follow": ("Follow", "Task Follow UI giu nguyen layout cu, chi doi data flow sang store."),
            "setup_training": ("Setup / Training", "Khu vuc nay se build function setup va training task."),
        }
        title, subtitle = section_map.get(section_key, ("Task", "Task function will be built here."))

        if section_key in {"follow", "setup_training"}:
            self.current_task_section = section_key

        if section_key in {"follow", "setup_training"}:
            self.header_card.grid_remove()
            self.bind_follow_mousewheel()
        else:
            self.unbind_follow_mousewheel()
            self.header_card.grid()
            self.title_label.configure(text=title)
            self.subtitle_label.configure(text=subtitle)

        host_widgets = {
            host
            for host in self.task_section_hosts.values()
            if host is not None and host.winfo_exists()
        }
        for widget in self.body_card.winfo_children():
            if widget in host_widgets:
                widget.grid_remove()
                continue
            widget.destroy()

        if section_key in {"follow", "setup_training"}:
            host = self._get_task_section_host(section_key)
            self._hide_task_section_hosts()
            host.grid()
            if self._has_cached_task_section(section_key):
                self._restore_task_section_context(section_key)
                self.update_follow_filter_controls()
                self.update_follow_scope_hint()
                self.update_follow_form_mode()
                self.refresh_follow_action_button_states()
                self.refresh_follow_tasks(keep_selection=True, force=False)
                self.schedule_follow_layout_refresh(delay_ms=1)
                self.schedule_detail_scroll_update()
                if (
                    self.follow_poll_after_id is None
                    and self.follow_controller.should_poll_follow_events()
                ):
                    self.poll_follow_store_events()
            else:
                self.selected_status = self.get_default_task_status()
                self.render_follow_ui(host=host)
                self._cache_task_section_context(section_key)
            return

        report_page = TaskReportPage(
            self.body_card,
            title=title,
            text_dark=self.TEXT_DARK,
            text_muted=self.TEXT_MUTED,
            panel_bg=self.BG_PANEL,
            panel_inner=self.BG_PANEL_INNER,
            border=self.BORDER,
            border_soft=self.BORDER_SOFT,
        )
        report_page.grid(row=0, column=0, sticky="nsew", pady=(0, 4))

    def on_page_resume(self, initial_section=None, initial_task_id=None):
        target_section = initial_section or self.rendered_section or self.initial_section or "report"
        already_visible = False
        try:
            already_visible = bool(self.winfo_exists()) and bool(self.winfo_ismapped())
        except Exception:
            already_visible = False

        if (
            self.page_active
            and already_visible
            and initial_task_id in (None, "")
            and target_section == self.rendered_section
        ):
            self._debug_job("page_resume", f"noop section={target_section} task_id={initial_task_id}")
            return

        self.page_active = True
        self._debug_job("page_resume", f"section={initial_section} task_id={initial_task_id}")

        if initial_task_id not in (None, ""):
            try:
                self.pending_focus_task_id = int(initial_task_id)
                self.follow_show_all = True
            except Exception:
                self.pending_focus_task_id = None

        if target_section != self.rendered_section:
            self.render_section(target_section)
            return

        if target_section in {"follow", "setup_training"}:
            self.bind_follow_mousewheel()
            self.follow_layout_applied_size = (0, 0)
            self.refresh_follow_tasks(keep_selection=True, force=False)
            self.schedule_follow_layout_refresh(delay_ms=1)
            self.schedule_detail_scroll_update()
            if (
                self.follow_poll_after_id is None
                and self.follow_controller.should_poll_follow_events()
            ):
                self.poll_follow_store_events()
            if self.pending_focus_task_id is not None:
                self.refresh_follow_tasks(keep_selection=True, force=True)

    def on_page_hide(self):
        self.page_active = False
        self._debug_job("page_hide", "sleep")
        self.close_deadline_popup()
        self.unbind_follow_mousewheel()
        self._cancel_process_jobs(include_poll=True)

    def _on_page_map(self, event=None):
        if event is not None and getattr(event, "widget", None) is not self:
            return
        if not self.page_active:
            return
        if self.rendered_section not in {"follow", "setup_training"}:
            return
        if not hasattr(self, "follow_wrap") or self.follow_wrap is None or not self.follow_wrap.winfo_exists():
            return

        try:
            current_size = (
                int(self.follow_wrap.winfo_width()),
                int(self.follow_wrap.winfo_height()),
            )
        except Exception:
            current_size = (0, 0)

        if current_size[0] > 1 and current_size[1] > 1 and current_size == self.follow_layout_applied_size:
            self._debug_job("page_map", f"skip_same_size section={self.rendered_section} size={current_size}")
            return

        self._debug_job("page_map", f"visible section={self.rendered_section}")
        if current_size[0] > 1 and current_size[1] > 1:
            self.follow_layout_pending_size = current_size
        self.follow_layout_applied_size = (0, 0)
        self.schedule_follow_layout_refresh(delay_ms=1)
        self.schedule_detail_scroll_update()
        if (
            self.follow_poll_after_id is None
            and self.follow_controller.should_poll_follow_events()
        ):
            self.poll_follow_store_events()

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

    def render_handoff_buttons(self):
        self.ui_handler.render_handoff_buttons()

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
        self._cancel_follow_action_state_refresh(action_key)

        if action_key in self.follow_action_inflight:
            self.follow_action_after_ids[action_key] = None
            self._debug_job(f"follow_action:{action_key}", "skip_schedule inflight")
            return

        remaining_ms = int(
            max(0.0, self.follow_action_ready_at.get(action_key, 0.0) - time.monotonic()) * 1000
        )
        if remaining_ms <= 0:
            self.follow_action_after_ids[action_key] = None
            self._debug_job(f"follow_action:{action_key}", "cooldown_complete immediate")
            self.update_follow_form_mode()
            return

        job_ref = {}

        def _wrapped():
            scheduled_id = job_ref.get("id")
            if self.follow_action_after_ids.get(action_key) != scheduled_id:
                self._debug_job(
                    f"follow_action:{action_key}",
                    f"skip_stale id={scheduled_id} current={self.follow_action_after_ids.get(action_key)}",
                )
                return
            self.follow_action_after_ids[action_key] = None
            self._debug_job(f"follow_action:{action_key}", f"callback id={scheduled_id}")
            if not self._can_run_page_job(f"follow_action:{action_key}", require_visible=False):
                return
            self.update_follow_form_mode()

        job_ref["id"] = self.after(remaining_ms, _wrapped)
        self.follow_action_after_ids[action_key] = job_ref["id"]
        self._debug_job(
            f"follow_action:{action_key}",
            f"schedule id={job_ref['id']} delay_ms={remaining_ms}",
        )

    def _start_follow_action(self, action_key):
        if self._follow_action_is_locked(action_key):
            return False

        self.follow_action_inflight.add(action_key)
        self.follow_action_ready_at[action_key] = time.monotonic() + (
            self.follow_action_cooldown_ms / 1000.0
        )
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
        if getattr(self, "deadline_target_button", None) is None and hasattr(self, "deadline_picker_button"):
            self.deadline_target_button = self.deadline_picker_button
            self.deadline_target_hint = getattr(self, "deadline_value_hint", None)
        self.ui_handler.toggle_deadline_popup()

    def open_deadline_popup(self):
        target_button = getattr(self, "deadline_target_button", None) or getattr(
            self, "deadline_picker_button", None
        )
        if not hasattr(self, "detail_form") or target_button is None:
            return

        popup_parent = self.detail_form
        try:
            popup_button = getattr(self, "popup_deadline_picker_button", None)
            if popup_button is not None and target_button == popup_button:
                popup_parent = self.training_popup if self.training_popup is not None else self.detail_form
        except Exception:
            popup_parent = self.detail_form

        if self.pending_deadline_date and self.is_valid_deadline_date(self.pending_deadline_date):
            pass
        elif self.confirmed_deadline_date:
            self.pending_deadline_date = self.confirmed_deadline_date
            self.pending_deadline_time = self.confirmed_deadline_time
        else:
            self.pending_deadline_date = ""
            self.pending_deadline_time = self.deadline_time_slots[0] if self.deadline_time_slots else ""

        if self.pending_deadline_date:
            try:
                dt = datetime.strptime(self.pending_deadline_date, "%d-%m-%Y")
                self.deadline_popup_month = dt.replace(day=1)
            except Exception:
                self.deadline_popup_month = datetime.now().replace(day=1)
        else:
            self.deadline_popup_month = datetime.now().replace(day=1)

        colors = {
            "INPUT_BORDER": self.INPUT_BORDER,
            "BTN_DARK": self.BTN_DARK,
            "BTN_DARK_HOVER": self.BTN_DARK_HOVER,
            "TEXT_LIGHT": self.TEXT_LIGHT,
            "TEXT_DARK": self.TEXT_DARK,
            "INPUT_BG": self.INPUT_BG,
            "BTN_ACTIVE": self.BTN_ACTIVE,
            "BTN_ACTIVE_HOVER": self.BTN_ACTIVE_HOVER,
        }
        callbacks = {
            "on_prev_month": lambda: self.shift_deadline_popup_month(-1),
            "on_next_month": lambda: self.shift_deadline_popup_month(1),
            "on_cancel": self.close_deadline_popup,
            "on_confirm": self.confirm_deadline_popup,
        }
        widgets = self.layout.build_deadline_popup(
            popup_parent,
            target_button,
            colors,
            callbacks,
            self.deadline_time_slots,
        )

        self.deadline_popup_frame = widgets["popup_frame"]
        self.deadline_month_label = widgets["month_label"]
        self.deadline_calendar_canvas = widgets["calendar_canvas"]
        self.deadline_popup_time_combo = widgets["time_combo"]

        if self.pending_deadline_time:
            self.deadline_popup_time_combo.set(self.pending_deadline_time)

        self.deadline_calendar_canvas.bind("<Button-1>", self.on_deadline_calendar_click)
        self.redraw_deadline_calendar()

    def close_deadline_popup(self):
        self.ui_handler.close_deadline_popup()
        self.deadline_target_button = None
        self.deadline_target_hint = None

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
        target_button = getattr(self, "deadline_target_button", None)
        popup_target_button = getattr(self, "popup_deadline_picker_button", None)
        is_popup_target = target_button is not None and popup_target_button is not None and target_button == popup_target_button
        if target_button is not None and target_button == getattr(self, "popup_deadline_picker_button", None):
            self.update_popup_deadline_button_text()
        else:
            self.update_deadline_button_text()
        self.close_deadline_popup()

        if self.get_confirmed_deadline_signature() != previous_signature:
            if is_popup_target:
                deadline_date, deadline_time, deadline_period = self.get_confirmed_deadline_parts()
                if self.current_username and deadline_date and deadline_time and deadline_period in {"AM", "PM"}:
                    self.store.load_handoff_options(
                        self.current_username,
                        task_date=deadline_date,
                        task_time=deadline_time,
                        task_period=deadline_period,
                    )
                    if self.follow_poll_after_id is None:
                        self.poll_follow_store_events()
            else:
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
                self.deadline_value_hint.configure(text="")
        else:
            self.deadline_picker_button.configure(text="Choose Date & Time")
            if hasattr(self, "deadline_value_hint"):
                self.deadline_value_hint.configure(text="")

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

    def is_setup_training_section(self):
        return self.current_task_section == "setup_training"

    def bind_follow_mousewheel(self):
        root = self.winfo_toplevel()
        if self.follow_mousewheel_bind_id is None and root is not None:
            self.follow_mousewheel_bind_id = root.bind("<MouseWheel>", self.on_global_mousewheel, add="+")
            self._debug_job("follow_mousewheel", f"bind_mousewheel id={self.follow_mousewheel_bind_id}")
        if self.follow_click_bind_id is None and root is not None:
            self.follow_click_bind_id = root.bind("<Button-1>", self.on_global_click, add="+")
            self._debug_job("follow_mousewheel", f"bind_click id={self.follow_click_bind_id}")

    def unbind_follow_mousewheel(self):
        root = self.winfo_toplevel()
        if self.follow_mousewheel_bind_id is not None and root is not None:
            try:
                root.unbind("<MouseWheel>", self.follow_mousewheel_bind_id)
                self._debug_job("follow_mousewheel", f"unbind_mousewheel id={self.follow_mousewheel_bind_id}")
            except Exception:
                pass
            self.follow_mousewheel_bind_id = None
        if self.follow_click_bind_id is not None and root is not None:
            try:
                root.unbind("<Button-1>", self.follow_click_bind_id)
                self._debug_job("follow_mousewheel", f"unbind_click id={self.follow_click_bind_id}")
            except Exception:
                pass
            self.follow_click_bind_id = None

    def on_global_click(self, event=None):
        if self.deadline_popup_frame is None or not self.deadline_popup_frame.winfo_exists():
            return
        widget = (
            event.widget
            if event is not None
            else self.winfo_containing(self.winfo_pointerx(), self.winfo_pointery())
        )
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

    def get_follow_board_visible_range(self):
        if self.is_setup_training_section():
            return tuple(getattr(self, "training_visible_range", (0, 100)) or (0, 100))
        return tuple(getattr(self, "follow_visible_range", (0, 100)) or (0, 100))

    def set_follow_board_visible_range(self, visible_range):
        start, end = visible_range or (0, 0)
        try:
            start = max(0, int(start))
        except Exception:
            start = 0
        try:
            end = max(start, int(end))
        except Exception:
            end = start
        normalized_range = (start, end)
        if self.is_setup_training_section():
            self.training_visible_range = normalized_range
        else:
            self.follow_visible_range = normalized_range
        return normalized_range

    def reset_follow_board_visible_range(self):
        return self.set_follow_board_visible_range((0, 100))

    def on_follow_canvas_scrollbar(self, *args):
        if hasattr(self, "follow_canvas") and self.follow_canvas is not None:
            self.follow_canvas.yview(*args)
        self.follow_controller.on_follow_board_view_changed()

    def on_follow_canvas_yscroll(self, first, last):
        if hasattr(self, "follow_scrollbar") and self.follow_scrollbar is not None:
            self.follow_scrollbar.set(first, last)
        self.follow_controller.on_follow_board_view_changed()

    def on_global_mousewheel(self, event):
        target = getattr(self, "active_scroll_target", None)
        if target == "detail" and hasattr(self, "detail_canvas"):
            self.detail_canvas.yview_scroll(-int(event.delta / 120), "units")
        elif target == "training_canvas" and getattr(self, "training_canvas", None) is not None:
            try:
                parent_canvas = getattr(self.detail_form, "_parent_canvas", None)
                if parent_canvas is not None:
                    parent_canvas.yview_scroll(-int(event.delta / 120), "units")
                else:
                    self.training_canvas.yview_scroll(-int(event.delta / 120), "units")
            except Exception:
                pass
        elif (
            target == "board"
            and hasattr(self, "follow_canvas")
            and getattr(self, "follow_board_scroll_enabled", False)
        ):
            self.follow_canvas.yview_scroll(-int(event.delta / 120), "units")
            self.follow_controller.on_follow_board_view_changed()

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
        if not self._can_run_page_job("detail_scrollregion", require_visible=True):
            return
        if hasattr(self, "detail_canvas"):
            bbox = self.detail_canvas.bbox("all")
            if bbox is not None:
                self.detail_canvas.configure(scrollregion=bbox)

    def request_notification_refresh(self, force=True, duration_ms=15000):
        parent = self.master
        while parent is not None:
            try:
                if hasattr(parent, "enable_notification_fast_polling") and hasattr(parent, "refresh_notification_count"):
                    parent.enable_notification_fast_polling(duration_ms)
                    parent.refresh_notification_count(force=force)
                    return True
                if hasattr(parent, "enable_notification_fast_polling") and hasattr(parent, "refresh_notification_items"):
                    parent.enable_notification_fast_polling(duration_ms)
                    parent.refresh_notification_items(force=force)
                    return True
                parent = parent.master
            except Exception:
                break
        return False

    def on_follow_wrap_configure(self, _event=None):
        self.ui_handler.on_follow_wrap_configure(_event)

    def schedule_follow_layout_refresh(self, width=None, height=None, delay_ms=24):
        self.follow_layout_pending_size = (width, height)
        if not self.page_active:
            self._debug_job("follow_layout", "skip_schedule inactive")
            return
        self._schedule_after_slot(
            "follow_layout_after_id",
            max(1, int(delay_ms)),
            self._flush_follow_layout_refresh,
            "follow_layout",
            require_visible=True,
        )

    def _flush_follow_layout_refresh(self):
        if not self._can_run_page_job("follow_layout_flush", require_visible=True):
            return
        if not hasattr(self, "follow_wrap") or not self.follow_wrap.winfo_exists():
            return

        pending_width, pending_height = self.follow_layout_pending_size or (None, None)
        width = pending_width or self.follow_wrap.winfo_width()
        height = pending_height or self.follow_wrap.winfo_height()
        if width <= 1 or height <= 1:
            return

        new_size = (int(width), int(height))
        if new_size == self.follow_layout_applied_size:
            return

        self.follow_layout_applied_size = new_size
        self.refresh_follow_layout()
        if (
            self.rendered_section in {"follow", "setup_training"}
            and self.follow_poll_after_id is None
            and self.follow_controller.should_poll_follow_events()
        ):
            self.poll_follow_store_events()
        if hasattr(self, "update_detail_scrollregion"):
            self.schedule_detail_scroll_update()
    def schedule_follow_canvas_redraw(self, delay_ms=1, for_resize=False, force=False):
        if not hasattr(self, "follow_canvas") or not self.page_active:
            if not self.page_active:
                self._debug_job("follow_canvas_redraw", "skip_schedule inactive")
            return

        if force:
            self.follow_canvas_force_redraw = True

        if for_resize and not force:
            try:
                current_size = (
                    int(self.follow_canvas.winfo_width()),
                    int(self.follow_canvas.winfo_height()),
                )
            except Exception:
                current_size = (0, 0)
            last_size = getattr(self, "follow_canvas_last_render_size", (0, 0))
            if current_size == last_size:
                self._debug_job("follow_canvas_redraw", f"skip_resize size={current_size}")
                return
            delay_ms = max(delay_ms, 60)

        self._schedule_after_slot(
            "follow_canvas_redraw_after_id",
            max(1, int(delay_ms)),
            self._flush_follow_canvas_redraw,
            "follow_canvas_redraw",
            require_visible=True,
        )

    def _flush_follow_canvas_redraw(self):
        if not self._can_run_page_job("follow_canvas_redraw_flush", require_visible=True):
            return
        if not hasattr(self, "follow_canvas") or not self.follow_canvas.winfo_exists():
            return
        force_redraw = bool(getattr(self, "follow_canvas_force_redraw", False))
        self.follow_canvas_force_redraw = False
        self.redraw_follow_canvas(force=force_redraw)

    def set_entry_value(self, entry, value):
        entry.delete(0, "end")
        if value:
            entry.insert(0, value)

    # Setup / Training delegates

    def get_training_stage_key(self, task=None):
        return self.setup_training_controller.get_training_stage_key(task)

    def get_training_template_sections(self, stage_key=None):
        return self.setup_training_controller.get_training_template_sections(stage_key)

    def merge_training_form_with_template(self, saved_sections, stage_key=None):
        return self.setup_training_controller.merge_training_form_with_template(saved_sections, stage_key)

    def update_training_info_card(self, task):
        return self.setup_training_controller.update_training_info_card(task)

    def render_setup_training_sections(self, saved_sections):
        return self.setup_training_controller.render_setup_training_sections(saved_sections)

    def get_current_section_key(self):
        return self.setup_training_controller.get_current_section_key()

    def redraw_training_canvas(self):
        return self.setup_training_controller.redraw_training_canvas()

    def schedule_training_canvas_refresh(self):
        return self.setup_training_controller.schedule_training_canvas_refresh()

    def on_training_canvas_configure(self, _event=None):
        return self.setup_training_controller.on_training_canvas_configure(_event)

    def on_training_canvas_yview(self, *args):
        return self.setup_training_controller.on_training_canvas_yview(*args)

    def on_training_canvas_click(self, event):
        return self.setup_training_controller.on_training_canvas_click(event)

    def refresh_visible_training_widgets(self):
        return self.setup_training_controller.refresh_visible_training_widgets()

    def _get_training_sections_source(self):
        return self.setup_training_controller._get_training_sections_source()

    def collect_training_form_sections(self, source_sections=None):
        return self.setup_training_controller.collect_training_form_sections(source_sections)

    def _sync_training_form_draft(self):
        return self.setup_training_controller._sync_training_form_draft()

    def collect_setup_training_payload(self, complete_first=False, complete_second=False, from_popup=False):
        return self.setup_training_controller.collect_setup_training_payload(
            complete_first=complete_first,
            complete_second=complete_second,
            from_popup=from_popup,
        )

    def open_setup_training_from_follow(self):
        return self.setup_training_controller.open_setup_training_from_follow()

    def on_complete_training_stage(self):
        return self.setup_training_controller.on_complete_training_stage()

    def open_training_completion_popup(self, action_type="update"):
        return self.setup_training_controller.open_training_completion_popup(action_type)

    def close_training_completion_popup(self):
        return self.setup_training_controller.close_training_completion_popup()

    def select_popup_handoff(self, target):
        return self.setup_training_controller.select_popup_handoff(target)

    def toggle_popup_deadline(self):
        return self.setup_training_controller.toggle_popup_deadline()

    def update_popup_deadline_button_text(self):
        return self.setup_training_controller.update_popup_deadline_button_text()

    def confirm_training_save(self, action_type):
        return self.setup_training_controller.confirm_training_save(action_type)

    def on_start_training(self):
        return self.setup_training_controller.on_start_training()

    def _refresh_tab_lock_state(self):
        return self.setup_training_controller._refresh_tab_lock_state()

    def on_training_tab_change(self, value):
        return self.setup_training_controller.on_training_tab_change(value)

    def _switch_training_section(self, value):
        return self.setup_training_controller._switch_training_section(value)

    def on_complete_current_tab(self):
        return self.setup_training_controller.on_complete_current_tab()

    def _all_items_checked_in_section(self, section_idx):
        return self.setup_training_controller._all_items_checked_in_section(section_idx)

    def _update_complete_button_state(self):
        return self.setup_training_controller._update_complete_button_state()

    def _autosave_completed_tabs(self):
        return self.setup_training_controller._autosave_completed_tabs()

    def on_view_training_info(self):
        return self.setup_training_controller.on_view_training_info()

    def _set_sections_read_only(self):
        return self.setup_training_controller._set_sections_read_only()

    # Follow delegates

    def render_follow_ui(self, host=None):
        return self.follow_controller.render_follow_ui(parent_host=host)

    def select_status(self, status_name):
        return self.follow_controller.select_status(status_name)

    def update_follow_form_mode(self):
        return self.follow_controller.update_follow_form_mode()

    def load_follow_bootstrap(self):
        return self.follow_controller.load_follow_bootstrap()

    def poll_follow_store_events(self):
        return self.follow_controller.poll_follow_store_events()

    def handle_follow_store_event(self, event):
        return self.follow_controller.handle_follow_store_event(event)

    def get_handoff_option_by_display_name(self, display_name):
        return self.follow_controller.get_handoff_option_by_display_name(display_name)

    def refresh_follow_tasks(self, search_text="", keep_selection=False, force=False):
        return self.follow_controller.refresh_follow_tasks(
            search_text=search_text,
            keep_selection=keep_selection,
            force=force,
        )

    def on_follow_refresh_manual(self):
        return self.follow_controller.on_follow_refresh_manual()

    def load_task_detail(self, task_id):
        return self.follow_controller.load_task_detail(task_id)

    def collect_follow_form_payload(self):
        return self.follow_controller.collect_follow_form_payload()

    def apply_follow_search(self):
        return self.follow_controller.apply_follow_search()

    def update_follow_scope_hint(self):
        return self.follow_controller.update_follow_scope_hint()

    def update_follow_filter_controls(self):
        return self.follow_controller.update_follow_filter_controls()

    def toggle_follow_show_all(self):
        return self.follow_controller.toggle_follow_show_all()

    def on_follow_include_done_toggle(self):
        return self.follow_controller.on_follow_include_done_toggle()

    def toggle_follow_include_done(self):
        return self.follow_controller.toggle_follow_include_done()

    def clear_follow_search(self):
        return self.follow_controller.clear_follow_search()

    def get_task_module_label(self):
        return self.follow_controller.get_task_module_label()

    def get_task_detail_title(self):
        return self.follow_controller.get_task_detail_title()

    def get_default_task_status(self):
        return self.follow_controller.get_default_task_status()

    def get_default_detail_hint(self):
        return self.follow_controller.get_default_detail_hint()

    def get_no_match_detail_hint(self):
        return self.follow_controller.get_no_match_detail_hint()

    def get_new_task_hint(self):
        return self.follow_controller.get_new_task_hint()

    def get_empty_board_text(self, show_all=False, include_done=False, has_search=False):
        return self.follow_controller.get_empty_board_text(
            show_all=show_all,
            include_done=include_done,
            has_search=has_search,
        )

    def get_section_filtered_tasks(self, query=""):
        return self.follow_controller.get_section_filtered_tasks(query)

    def redraw_follow_canvas(self, force=False):
        return self.follow_controller.redraw_follow_canvas(force=force)

    def update_follow_board_height(self, content_height):
        return self.follow_controller.update_follow_board_height(content_height)

    def get_task_row_theme(self, task, index):
        return self.follow_controller.get_task_row_theme(task, index)

    def on_follow_canvas_click(self, event):
        return self.follow_controller.on_follow_canvas_click(event)

    def load_task_into_form(self, task):
        return self.follow_controller.load_task_into_form(task)

    def clear_follow_form(self):
        return self.follow_controller.clear_follow_form()

    def start_new_task(self):
        return self.follow_controller.start_new_task()

    def open_quick_create_task_popup(self):
        return self.follow_controller.open_quick_create_task_popup()

    def _confirm_quick_create_task(self, merchant_raw_text):
        return self.follow_controller._confirm_quick_create_task(merchant_raw_text)

    def refresh_follow_layout(self):
        return self.follow_controller.refresh_follow_layout()

    def render_history(self, history_items):
        return self.follow_controller.render_history(history_items)

    def on_follow_save(self):
        return self.follow_controller.on_follow_save()

    def on_follow_update(self):
        return self.follow_controller.on_follow_update()

    def on_follow_delete(self):
        return self.follow_controller.on_follow_delete()
