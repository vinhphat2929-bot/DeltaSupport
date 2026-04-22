from datetime import datetime
import math
from tkinter import messagebox
from urllib.parse import quote_plus
import webbrowser

import customtkinter as ctk

from pages.process.layout import SETUP_BOARD_COMPACT_WIDTH


class TaskFollowController:
    def __init__(self, page):
        self.page = page

    def _get_effective_view_flags(self):
        page = self.page
        return bool(page.follow_show_all), bool(page.follow_include_done)

    def _is_setup_training_item(self, item):
        page = self.page
        status_text = str((item or {}).get("status", "")).strip().upper()
        if status_text in {"SET UP & TRAINING", "2ND TRAINING"}:
            return True
        if status_text != "DONE" or not page.follow_include_done:
            return False
        if (item or {}).get("has_training_form") or (item or {}).get("training_form"):
            return True
        return bool(str((item or {}).get("training_started_at", "")).strip())

    def _filter_items_for_current_section(self, items):
        page = self.page
        if not page.is_setup_training_section():
            return list(items or [])
        return [item for item in (items or []) if self._is_setup_training_item(item)]

    def _build_history_signature(self, history_items):
        normalized_items = history_items or []
        return tuple(
            (
                item.get("log_id"),
                item.get("time"),
                item.get("action_type"),
                item.get("note"),
                item.get("handoff_to"),
            )
            for item in normalized_items
        )

    def _build_follow_form_signature(self, task):
        current_task = task or {}
        history_items = current_task.get("history") or []
        return (
            current_task.get("task_id"),
            current_task.get("updated_at"),
            current_task.get("merchant_raw"),
            current_task.get("phone"),
            current_task.get("tracking_number"),
            current_task.get("problem"),
            current_task.get("handoff_from"),
            tuple(current_task.get("handoff_to_display_names") or []),
            current_task.get("handoff_to"),
            current_task.get("status"),
            current_task.get("deadline_date"),
            current_task.get("deadline_time"),
            current_task.get("deadline_period"),
            current_task.get("note"),
            self._build_history_signature(history_items),
        )

    def _get_history_canvas(self):
        page = self.page
        history_box = getattr(page, "history_box", None)
        if history_box is None:
            return None
        return getattr(history_box, "_parent_canvas", None)

    def _capture_history_scroll_fraction(self):
        scroll_canvas = self._get_history_canvas()
        if scroll_canvas is None:
            return 0.0
        try:
            return float(scroll_canvas.yview()[0])
        except Exception:
            return 0.0

    def _restore_history_scroll_fraction(self, fraction):
        scroll_canvas = self._get_history_canvas()
        if scroll_canvas is None:
            return
        try:
            scroll_canvas.update_idletasks()
            scroll_canvas.yview_moveto(max(0.0, min(1.0, float(fraction or 0.0))))
        except Exception:
            return

    def _ensure_history_box_cache(self):
        page = self.page
        history_box = getattr(page, "history_box", None)
        if history_box is None:
            return None

        if not hasattr(history_box, "_history_entry_cache"):
            history_box._history_entry_cache = {}
        if not hasattr(history_box, "_history_entry_order"):
            history_box._history_entry_order = []
        if not hasattr(history_box, "_history_empty_label"):
            history_box._history_empty_label = None
        if not hasattr(history_box, "_history_owner_task_id"):
            history_box._history_owner_task_id = None
        return history_box

    def _build_grouped_history_entries(self, history_items):
        grouped_history_items = []
        index = 0
        normalized_items = history_items or []

        while index < len(normalized_items):
            item = normalized_items[index] or {}
            action_type = str(item.get("action_type", "")).strip().upper()
            log_id = item.get("log_id")
            base_entry_id = f"log:{log_id}" if log_id not in (None, "") else f"row:{index}"

            if action_type == "ASSIGN":
                grouped_entry = {
                    "entry_id": f"assign:{log_id}" if log_id not in (None, "") else f"assign:{index}",
                    "user": item.get("user", ""),
                    "time": item.get("time", ""),
                    "assign_note": item.get("note", ""),
                    "note": "",
                }
                if index + 1 < len(normalized_items):
                    next_item = normalized_items[index + 1] or {}
                    next_action_type = str(next_item.get("action_type", "")).strip().upper()
                    if (
                        next_action_type != "ASSIGN"
                        and str(next_item.get("user", "")).strip() == str(item.get("user", "")).strip()
                        and str(next_item.get("time", "")).strip() == str(item.get("time", "")).strip()
                    ):
                        grouped_entry["note"] = next_item.get("note", "")
                        next_log_id = next_item.get("log_id")
                        if next_log_id not in (None, ""):
                            grouped_entry["entry_id"] = f"{grouped_entry['entry_id']}:{next_log_id}"
                        index += 1
                grouped_history_items.append(grouped_entry)
            else:
                grouped_history_items.append(
                    {
                        "entry_id": base_entry_id,
                        "user": item.get("user", ""),
                        "time": item.get("time", ""),
                        "assign_note": "",
                        "note": item.get("note", ""),
                    }
                )
            index += 1

        for entry in grouped_history_items:
            entry["content_signature"] = (
                str(entry.get("user", "")).strip(),
                str(entry.get("time", "")).strip(),
                str(entry.get("assign_note", "")).strip(),
                str(entry.get("note", "")).strip(),
            )
        return grouped_history_items

    def _create_history_card(self, parent):
        page = self.page
        card = ctk.CTkFrame(
            parent,
            fg_color="#fffaf3",
            corner_radius=12,
            border_width=1,
            border_color="#e6cfab",
        )

        header = ctk.CTkFrame(card, fg_color="transparent")
        user_label = ctk.CTkLabel(
            header,
            text="",
            font=("Segoe UI", 12, "bold"),
            text_color=page.TEXT_DARK,
            anchor="w",
            justify="left",
        )
        time_label = ctk.CTkLabel(
            header,
            text="",
            font=("Segoe UI", 10),
            text_color=page.TEXT_MUTED,
            anchor="w",
            justify="left",
        )

        assign_wrap = ctk.CTkFrame(
            card,
            fg_color="#fff1d6",
            corner_radius=8,
            border_width=1,
            border_color="#d6a24a",
        )
        assign_label = ctk.CTkLabel(
            assign_wrap,
            text="",
            font=("Segoe UI", 11, "bold"),
            text_color="#8a4b00",
            justify="left",
            anchor="w",
        )

        note_label = ctk.CTkLabel(
            card,
            text="",
            font=("Segoe UI", 12),
            text_color=page.TEXT_MUTED,
            justify="left",
            anchor="w",
        )

        header.pack(fill="x", padx=12, pady=(10, 4))
        user_label.pack(anchor="w")
        time_label.pack(anchor="w", pady=(2, 0))
        assign_label.pack(fill="x", anchor="w", padx=10, pady=(8, 8))

        card._history_widgets = {
            "header": header,
            "user_label": user_label,
            "time_label": time_label,
            "assign_wrap": assign_wrap,
            "assign_label": assign_label,
            "note_label": note_label,
            "content_signature": None,
        }
        return card

    def _update_history_card(self, card, item, note_wraplength, meta_wraplength):
        widgets = getattr(card, "_history_widgets", {})
        content_signature = item.get("content_signature")
        if widgets.get("content_signature") == content_signature:
            widgets["assign_label"].configure(wraplength=meta_wraplength)
            widgets["note_label"].configure(wraplength=note_wraplength)
            return

        widgets["user_label"].configure(text=str(item.get("user", "")).strip() or "-")
        widgets["time_label"].configure(text=str(item.get("time", "")).strip())

        assign_wrap = widgets["assign_wrap"]
        assign_label = widgets["assign_label"]
        assign_note = str(item.get("assign_note", "")).strip()
        assign_wrap.pack_forget()
        if assign_note:
            assign_label.configure(
                text=assign_note,
                wraplength=meta_wraplength,
            )
            assign_wrap.pack(fill="x", padx=10, pady=(0, 6))

        note_label = widgets["note_label"]
        note_text = str(item.get("note", "")).strip()
        note_label.pack_forget()
        if note_text:
            note_label.configure(
                text=note_text,
                wraplength=note_wraplength,
            )
            note_label.pack(fill="x", anchor="w", padx=12, pady=(0, 10))

        widgets["content_signature"] = content_signature

    def _build_follow_board_signature(self, tasks, canvas_width, canvas_height, is_training, active_task_id, visible_range):
        return (
            "setup_training" if is_training else "follow",
            int(canvas_width or 0),
            int(canvas_height or 0),
            active_task_id,
            tuple(visible_range or (0, 0)),
            tuple(
                (
                    task.get("task_id"),
                    task.get("updated_at"),
                    bool(task.get("is_saving")),
                )
                for task in (tasks or [])
            ),
        )

    def _get_board_row_metrics(self, is_training):
        row_height = 46 if is_training else 44
        row_gap = 6
        return {
            "row_height": row_height,
            "row_gap": row_gap,
            "row_stride": row_height + row_gap,
            "first_row_y": 8,
            "bottom_padding": 30,
        }

    def _get_current_board_visible_range(self):
        return tuple(self.page.get_follow_board_visible_range() or (0, 100))

    def _set_current_board_visible_range(self, visible_range):
        return self.page.set_follow_board_visible_range(visible_range)

    def _calculate_board_content_bottom(self, tasks_count, first_row_y, row_stride, bottom_padding):
        return first_row_y + (max(0, int(tasks_count)) * row_stride) + bottom_padding

    def _calculate_visible_task_range(
        self,
        canvas,
        tasks_count,
        first_row_y,
        row_stride,
        total_scroll_height,
        buffer_rows=10,
    ):
        if tasks_count <= 0:
            return (0, 0)

        try:
            top_frac, bottom_frac = canvas.yview()
        except Exception:
            top_frac, bottom_frac = 0.0, 1.0

        total_scroll_height = max(1.0, float(total_scroll_height or 0.0))
        top_y = float(top_frac or 0.0) * total_scroll_height
        bottom_y = float(bottom_frac or 1.0) * total_scroll_height
        safe_row_stride = max(1, int(row_stride or 1))
        buffer_rows = max(0, int(buffer_rows or 0))

        first_idx = math.floor((top_y - first_row_y) / safe_row_stride) - buffer_rows
        last_idx = math.ceil((bottom_y - first_row_y) / safe_row_stride) + buffer_rows

        first_idx = max(0, min(tasks_count, first_idx))
        last_idx = max(first_idx, min(tasks_count, last_idx))

        if last_idx <= first_idx:
            first_idx = max(0, min(tasks_count - 1, first_idx))
            last_idx = min(tasks_count, first_idx + 1)

        return (first_idx, last_idx)

    def _reset_board_scroll_position(self):
        page = self.page
        page.reset_follow_board_visible_range()
        page.follow_board_suppress_selection_scroll = True
        page.follow_board_render_signature = None
        canvas = getattr(page, "follow_canvas", None)
        if canvas is None:
            return
        try:
            if canvas.winfo_exists():
                canvas.yview_moveto(0.0)
        except Exception:
            return

    def _scroll_to_task_index(self, task_index):
        page = self.page
        canvas = getattr(page, "follow_canvas", None)
        tasks = page.filtered_follow_tasks or []
        if canvas is None or task_index is None or task_index < 0 or task_index >= len(tasks):
            return False

        metrics = self._get_board_row_metrics(page.is_setup_training_section())
        row_height = metrics["row_height"]
        row_stride = metrics["row_stride"]
        first_row_y = metrics["first_row_y"]
        content_bottom = self._calculate_board_content_bottom(
            len(tasks),
            first_row_y,
            row_stride,
            metrics["bottom_padding"],
        )

        try:
            visible_height = max(1, int(canvas.winfo_height()))
        except Exception:
            visible_height = 1

        total_scroll_height = max(content_bottom, visible_height)
        try:
            top_frac, bottom_frac = canvas.yview()
        except Exception:
            top_frac, bottom_frac = 0.0, 1.0

        viewport_top = float(top_frac or 0.0) * total_scroll_height
        viewport_bottom = float(bottom_frac or 1.0) * total_scroll_height
        row_top = first_row_y + (task_index * row_stride)
        row_bottom = row_top + row_height

        if row_top >= viewport_top and row_bottom <= viewport_bottom:
            return False

        if row_top < viewport_top:
            target_top = row_top
        else:
            target_top = row_bottom - visible_height

        max_scroll_top = max(0, total_scroll_height - visible_height)
        target_top = max(0, min(max_scroll_top, target_top))
        target_yview = 0.0 if total_scroll_height <= 0 else (target_top / total_scroll_height)

        try:
            canvas.yview_moveto(target_yview)
        except Exception:
            return False

        self.on_follow_board_view_changed(force=True)
        return True

    def _ensure_task_visible(self, task_id):
        page = self.page
        if task_id in (None, ""):
            return False
        if getattr(page, "follow_board_suppress_selection_scroll", False):
            return False

        task_index = next(
            (
                index
                for index, task in enumerate(page.filtered_follow_tasks or [])
                if task.get("task_id") == task_id
            ),
            None,
        )
        if task_index is None:
            return False

        return self._scroll_to_task_index(task_index)

    def on_follow_board_view_changed(self, force=False):
        page = self.page
        canvas = getattr(page, "follow_canvas", None)
        if canvas is None or not page.page_active:
            return
        try:
            if not canvas.winfo_exists():
                return
        except Exception:
            return
        if not page._can_run_page_job("follow_board_view_change", require_visible=True):
            return

        metrics = self._get_board_row_metrics(page.is_setup_training_section())
        try:
            visible_height = max(1, int(canvas.winfo_height()))
        except Exception:
            visible_height = 1

        total_scroll_height = max(
            self._calculate_board_content_bottom(
                len(page.filtered_follow_tasks or []),
                metrics["first_row_y"],
                metrics["row_stride"],
                metrics["bottom_padding"],
            ),
            visible_height,
        )
        next_range = self._calculate_visible_task_range(
            canvas,
            len(page.filtered_follow_tasks or []),
            metrics["first_row_y"],
            metrics["row_stride"],
            total_scroll_height,
            buffer_rows=getattr(page, "follow_board_virtual_buffer_rows", 10),
        )
        current_range = self._get_current_board_visible_range()
        if not force and next_range == current_range:
            return

        self._set_current_board_visible_range(next_range)
        if force:
            page.follow_board_render_signature = None
        page.schedule_follow_canvas_redraw(delay_ms=1, force=force)

    def _clear_row_active_items(self, canvas, row_meta):
        for item_id in list(row_meta.get("active_item_ids", [])):
            try:
                canvas.delete(item_id)
            except Exception:
                pass
        row_meta["active_item_ids"] = []

    def _set_row_active_state(self, canvas, row_meta, is_active):
        if canvas is None or row_meta is None:
            return

        self._clear_row_active_items(canvas, row_meta)
        if not is_active:
            return

        x1 = row_meta["x1"]
        y1 = row_meta["y1"]
        x2 = row_meta["x2"]
        y2 = row_meta["y2"]
        marker_x1 = row_meta["marker_x1"]
        marker_x2 = row_meta["marker_x2"]

        outline_id = self.page.renderer.draw_round_rect(
            canvas,
            x1 - 1,
            y1 - 1,
            x2 + 1,
            y2 + 1,
            12,
            "",
            "#5b3d1d",
            width=2,
        )
        marker_id = canvas.create_rectangle(
            marker_x1,
            y1 + 6,
            marker_x2,
            y2 - 6,
            fill="#5b3d1d",
            outline="",
        )
        row_meta["active_item_ids"] = [outline_id, marker_id]

    def update_follow_canvas_active_task(self, next_task_id):
        page = self.page
        canvas = getattr(page, "follow_canvas", None)
        row_meta_map = getattr(page, "follow_canvas_row_meta", {}) or {}
        previous_task_id = getattr(page, "follow_canvas_active_task_id", None)

        page.follow_canvas_active_task_id = next_task_id
        if previous_task_id == next_task_id:
            if next_task_id is not None:
                self._ensure_task_visible(next_task_id)
            return

        if canvas is None or not row_meta_map:
            page.follow_board_render_signature = None
            page.schedule_follow_canvas_redraw(delay_ms=1, force=True)
            return

        if previous_task_id in row_meta_map:
            self._set_row_active_state(canvas, row_meta_map.get(previous_task_id), False)
        if next_task_id in row_meta_map:
            self._set_row_active_state(canvas, row_meta_map.get(next_task_id), True)
        elif next_task_id is not None:
            if not self._ensure_task_visible(next_task_id):
                page.follow_board_render_signature = None
                page.schedule_follow_canvas_redraw(delay_ms=1, force=True)

    def render_follow_ui(self, parent_host=None):
        page = self.page
        host = parent_host or getattr(page, "body_card", None)
        if host is None or not host.winfo_exists():
            return

        for child in host.winfo_children():
            child.destroy()

        colors = {
            "BG_PANEL_INNER": page.BG_PANEL_INNER,
            "BORDER_SOFT": page.BORDER_SOFT,
            "TEXT_DARK": page.TEXT_DARK,
            "TEXT_MUTED": page.TEXT_MUTED,
            "INPUT_BG": page.INPUT_BG,
            "INPUT_BORDER": page.INPUT_BORDER,
            "BTN_ACTIVE": page.BTN_ACTIVE,
            "BTN_ACTIVE_HOVER": page.BTN_ACTIVE_HOVER,
            "BTN_IDLE": page.BTN_IDLE,
            "BTN_IDLE_HOVER": page.BTN_IDLE_HOVER,
            "BTN_DARK": page.BTN_DARK,
            "BTN_DARK_HOVER": page.BTN_DARK_HOVER,
            "TEXT_LIGHT": page.TEXT_LIGHT,
            "BTN_INACTIVE": page.BTN_INACTIVE,
            "TRAINING_CANVAS_BG": page.TRAINING_CANVAS_BG,
        }
        page.colors = colors

        callbacks = {
            "on_search": page.apply_follow_search,
            "on_clear": page.clear_follow_search,
            "on_create": page.start_new_task,
            "on_toggle_show_all": page.toggle_follow_show_all,
            "on_toggle_include_done": page.toggle_follow_include_done,
        }

        layout_widgets = page.layout.build_main_layout(host, colors, callbacks)
        page.follow_wrap = layout_widgets["follow_wrap"]
        page.follow_top_card = layout_widgets["follow_top_card"]
        page.search_entry = layout_widgets["search_entry"]
        page.show_all_button = layout_widgets["show_all_button"]
        page.include_done_switch = layout_widgets.get("include_done_switch")
        page.follow_board_card = layout_widgets["follow_board_card"]
        page.follow_canvas = layout_widgets["follow_canvas"]
        page.follow_scrollbar = layout_widgets["follow_scrollbar"]
        page.detail_form = layout_widgets["detail_form"]
        page.follow_header_canvas = layout_widgets["follow_header_canvas"]
        page.follow_scope_label = layout_widgets["follow_scope_label"]
        page.detail_card = layout_widgets["detail_card"]
        page.table_card = layout_widgets["table_card"]
        page.follow_canvas_wrap = layout_widgets["follow_canvas_wrap"]
        page.follow_layout_mode = None
        page.follow_layout_pending_size = None
        page.follow_layout_applied_size = (0, 0)
        page.follow_canvas_last_render_size = (0, 0)
        page.follow_canvas_force_redraw = False
        page.follow_board_render_signature = None
        page.follow_canvas_row_meta = {}
        page.follow_canvas_active_task_id = None
        page.reset_follow_board_visible_range()

        if page.follow_scrollbar is not None:
            page.follow_scrollbar.configure(command=page.on_follow_canvas_scrollbar)
        page.follow_canvas.configure(yscrollcommand=page.on_follow_canvas_yscroll)

        page.follow_wrap.bind("<Configure>", page.on_follow_wrap_configure)
        page.follow_canvas.bind(
            "<Configure>",
            lambda _event: page.schedule_follow_canvas_redraw(delay_ms=60, for_resize=True),
        )
        page.search_entry.bind("<KeyRelease>", lambda _e: page.schedule_follow_search_apply())

        def _enter_board(_event=None):
            page.set_active_scroll_target("board")

        def _leave_board(_event=None):
            page.clear_active_scroll_target("board")

        page.follow_canvas.bind("<Enter>", _enter_board)
        page.follow_canvas.bind("<Leave>", _leave_board)
        page.follow_header_canvas.bind("<Enter>", _enter_board)
        page.follow_header_canvas.bind("<Leave>", _leave_board)
        page.follow_canvas_wrap.bind("<Enter>", _enter_board)
        page.follow_canvas_wrap.bind("<Leave>", _leave_board)
        page.follow_canvas.bind("<Button-1>", page.on_follow_canvas_click)

        titles = {
            "detail_title": page.get_task_detail_title(),
            "detail_hint": page.get_default_detail_hint(),
        }

        if page.is_setup_training_section():
            page.setup_training_controller.build_setup_training_form(colors, titles)
        else:
            form_callbacks = {
                "on_deadline_click": page.toggle_deadline_popup,
                "on_status_change": page.select_status,
                "on_track_ups": self.on_track_ups,
                "on_save": page.on_follow_save,
                "on_update": page.on_follow_update,
                "on_delete": page.on_follow_delete,
            }
            form_widgets = page.layout.build_follow_detail_form(page.detail_form, colors, form_callbacks, titles)

            page.detail_hint = form_widgets["detail_hint"]
            page.merchant_name_entry = form_widgets["merchant_name_entry"]
            page.phone_entry = form_widgets["phone_entry"]
            page.tracking_number_entry = form_widgets["tracking_number_entry"]
            page.tracking_number_row = form_widgets["tracking_number_row"]
            page.track_ups_button_row = form_widgets["track_ups_button_row"]
            page.track_ups_button = form_widgets["track_ups_button"]
            page.problem_entry = form_widgets["problem_entry"]
            page.handoff_from_entry = form_widgets["handoff_from_entry"]
            page.deadline_picker_button = form_widgets["deadline_picker_button"]
            page.deadline_value_hint = form_widgets["deadline_value_hint"]
            page.handoff_button_wrap = form_widgets["handoff_button_wrap"]
            page.status_buttons = form_widgets["status_buttons"]
            page.note_box = form_widgets["note_box"]
            page.follow_save_button = form_widgets["follow_save_button"]
            page.follow_update_button = form_widgets["follow_update_button"]
            page.follow_delete_button = form_widgets["follow_delete_button"]
            page.history_box = form_widgets["history_box"]
            page._tracking_controls_visible = None

            page.phone_entry.bind("<KeyRelease>", page.on_phone_input)
            page.tracking_number_entry.bind(
                "<KeyRelease>",
                lambda _e: self.update_tracking_controls(refresh_visibility=False),
            )
            page.selected_status = page.get_default_task_status()
            self.select_status(page.selected_status)
            page.update_deadline_button_text()

        page.render_handoff_buttons()
        page.select_handoff(page.selected_handoff_to)

        if not page.is_setup_training_section():
            page.handoff_from_entry.configure(state="normal")
            page.set_entry_value(page.handoff_from_entry, page.current_display_name)
            page.handoff_from_entry.configure(state="disabled")
            self.update_follow_form_mode()
        else:
            page.refresh_follow_action_button_states()

        page.refresh_follow_action_button_states()
        self.load_follow_bootstrap()
        page.schedule_follow_layout_refresh()

    def select_status(self, status_name):
        page = self.page
        page.selected_status = status_name

        for name, button in page.status_buttons.items():
            if name == status_name:
                meta = page.logic.status_meta.get(name, {"bg": page.BTN_ACTIVE, "text": page.TEXT_DARK})
                button.configure(
                    fg_color=meta["bg"],
                    hover_color=meta["bg"],
                    text_color=meta["text"],
                )
            else:
                button.configure(
                    fg_color=page.BTN_IDLE,
                    hover_color=page.BTN_IDLE_HOVER,
                    text_color=page.TEXT_LIGHT,
                )
        self.update_tracking_controls()

    def _configure_follow_action_buttons(self):
        page = self.page
        is_edit_mode = bool(page.active_task and page.active_task.get("task_id"))

        if hasattr(page, "follow_save_button"):
            if is_edit_mode or page._follow_action_is_locked("save"):
                page.follow_save_button.configure(
                    state="disabled",
                    fg_color="#d9c7aa",
                    hover_color="#d9c7aa",
                    text_color="#8f7a62",
                )
            else:
                page.follow_save_button.configure(
                    state="normal",
                    fg_color=page.BTN_ACTIVE,
                    hover_color=page.BTN_ACTIVE_HOVER,
                    text_color=page.TEXT_DARK,
                )

        if hasattr(page, "follow_update_button"):
            if is_edit_mode and not page._follow_action_is_locked("update"):
                page.follow_update_button.configure(
                    state="normal",
                    fg_color=page.BTN_DARK,
                    hover_color=page.BTN_DARK_HOVER,
                    text_color=page.TEXT_LIGHT,
                )
            else:
                page.follow_update_button.configure(
                    state="disabled",
                    fg_color="#b8aba0",
                    hover_color="#b8aba0",
                    text_color="#f4eee7",
                )

        if hasattr(page, "follow_delete_button"):
            if is_edit_mode and not page.follow_action_inflight and not page._follow_action_is_locked("delete"):
                page.follow_delete_button.configure(
                    state="normal",
                    fg_color="#9f2d2d",
                    hover_color="#ba3a3a",
                    text_color="#fff7f0",
                )
            else:
                page.follow_delete_button.configure(
                    state="disabled",
                    fg_color="#d6b3b3",
                    hover_color="#d6b3b3",
                    text_color="#f5e9e9",
                )

    def update_tracking_controls(self, refresh_visibility=True):
        page = self.page
        if not hasattr(page, "tracking_number_entry") or not hasattr(page, "track_ups_button_row"):
            return

        is_tracking_status = str(getattr(page, "selected_status", "")).strip().upper() == "SHIP OUT"
        tracking_number = page.tracking_number_entry.get().strip().upper()
        visibility_changed = False

        if refresh_visibility:
            previous_visibility = getattr(page, "_tracking_controls_visible", None)
            if previous_visibility != is_tracking_status:
                visibility_changed = True
                if hasattr(page, "tracking_number_row"):
                    if is_tracking_status:
                        page.tracking_number_row.grid()
                    else:
                        page.tracking_number_row.grid_remove()

                if is_tracking_status:
                    page.track_ups_button_row.grid()
                else:
                    page.track_ups_button_row.grid_remove()

                page._tracking_controls_visible = is_tracking_status

        if hasattr(page, "track_ups_button"):
            is_enabled = bool(is_tracking_status and tracking_number)
            page.track_ups_button.configure(
                state="normal" if is_enabled else "disabled",
                fg_color="#8b5e1a" if is_enabled else "#d7c4a2",
                hover_color="#a06c1e" if is_enabled else "#d7c4a2",
                text_color="#fff7e8" if is_enabled else "#8f7a62",
            )

        self._configure_follow_action_buttons()
        if is_tracking_status and not tracking_number:
            if hasattr(page, "follow_save_button"):
                page.follow_save_button.configure(
                    state="disabled",
                    fg_color="#d9c7aa",
                    hover_color="#d9c7aa",
                    text_color="#8f7a62",
                )
            if hasattr(page, "follow_update_button"):
                page.follow_update_button.configure(
                    state="disabled",
                    fg_color="#b8aba0",
                    hover_color="#b8aba0",
                    text_color="#f4eee7",
                )

        if visibility_changed and hasattr(page, "update_detail_scrollregion"):
            page.schedule_detail_scroll_update()

    def get_ups_tracking_url(self, tracking_number):
        normalized = str(tracking_number or "").strip().upper()
        if not normalized:
            return ""
        return f"https://www.ups.com/track?loc=en_US&tracknum={quote_plus(normalized)}"

    def on_track_ups(self):
        page = self.page
        if not hasattr(page, "tracking_number_entry"):
            return

        tracking_number = page.tracking_number_entry.get().strip().upper()
        if not tracking_number:
            messagebox.showwarning("UPS Tracking", "Hay nhap tracking number truoc.")
            return

        tracking_url = self.get_ups_tracking_url(tracking_number)
        if not tracking_url:
            messagebox.showwarning("UPS Tracking", "Tracking number khong hop le.")
            return

        webbrowser.open(tracking_url, new=2)

    def update_follow_form_mode(self):
        page = self.page
        is_edit_mode = bool(page.active_task and page.active_task.get("task_id"))

        if page.is_setup_training_section():
            started = getattr(page, "is_training_started", False)
            task_status = str((page.active_task or {}).get("status", "")).strip().upper()
            is_done_task = task_status == "DONE"
            is_second_stage = task_status == "2ND TRAINING"
            has_saved_training_info = page.setup_training_controller._task_has_saved_training_info(page.active_task)

            if hasattr(page, "start_training_button") and page.start_training_button is not None:
                page.start_training_button.configure(
                    text="▶  Start 2nd Training" if is_second_stage else "▶  Start 1st Training"
                )

            if started:
                if hasattr(page, "start_training_button"):
                    page.start_training_button.master.grid_remove()
                if hasattr(page, "tab_wrap"):
                    if is_second_stage:
                        page.tab_wrap.grid_remove()
                    else:
                        page.tab_wrap.grid()
                if hasattr(page, "training_sections_wrap"):
                    page.training_sections_wrap.grid()
                if is_done_task:
                    if hasattr(page, "action_row"):
                        page.action_row.grid_remove()
                else:
                    if hasattr(page, "action_row"):
                        page.action_row.grid()
            else:
                if hasattr(page, "start_training_button"):
                    start_wrap = page.start_training_button.master
                    start_wrap.grid()
                    page.start_training_button.pack_forget()
                    if hasattr(page, "view_training_info_button"):
                        page.view_training_info_button.pack_forget()
                    if is_done_task:
                        if hasattr(page, "view_training_info_button"):
                            page.view_training_info_button.pack(side="left", pady=6)
                    else:
                        page.start_training_button.pack(side="left", padx=(0, 8), pady=6)
                        if hasattr(page, "view_training_info_button") and has_saved_training_info:
                            page.view_training_info_button.pack(side="left", pady=6)
                if hasattr(page, "tab_wrap"):
                    page.tab_wrap.grid_remove()
                if hasattr(page, "training_sections_wrap"):
                    page.training_sections_wrap.grid_remove()
                if hasattr(page, "action_row"):
                    page.action_row.grid_remove()

            if hasattr(page, "complete_tab_button") and page.complete_tab_button is not None:
                page.complete_tab_button.pack_forget()
                page.complete_tab_button.pack(side="left", padx=(0, 6))
            if hasattr(page, "follow_complete_training_button") and page.follow_complete_training_button is not None:
                page.follow_complete_training_button.pack_forget()
                if not is_second_stage:
                    page.follow_complete_training_button.pack(side="left")

            if hasattr(page, "follow_update_button"):
                is_locked = page._follow_action_is_locked("update") or not is_edit_mode
                page.follow_update_button.configure(
                    state="disabled" if is_locked else "normal",
                    fg_color="#b8aba0" if is_locked else page.BTN_DARK,
                    hover_color="#b8aba0" if is_locked else page.BTN_DARK_HOVER,
                    text_color="#f4eee7" if is_locked else page.TEXT_LIGHT,
                )
            if hasattr(page, "follow_complete_training_button"):
                stage_val = str((page.active_task or {}).get("status", "")).strip().upper()
                is_second_stage = stage_val == "2ND TRAINING"
                btn_text = "Complete 2nd Training" if is_second_stage else "Complete 1st Training"
                can_complete = (
                    is_edit_mode
                    and stage_val in {"SET UP & TRAINING", "2ND TRAINING"}
                    and not page._follow_action_is_locked("update")
                )
                page.follow_complete_training_button.configure(
                    text=btn_text,
                    state="normal" if can_complete else "disabled",
                    fg_color=page.BTN_ACTIVE if can_complete else "#d9c7aa",
                    hover_color=page.BTN_ACTIVE_HOVER if can_complete else "#d9c7aa",
                    text_color=page.TEXT_DARK if can_complete else "#8f7a62",
                )
            page.refresh_follow_action_button_states()
            return

        self._configure_follow_action_buttons()
        self.update_tracking_controls(refresh_visibility=False)
        page.refresh_follow_action_button_states()

    def load_follow_bootstrap(self):
        page = self.page
        if not page._can_run_page_job("follow_bootstrap", require_visible=False):
            return
        page._debug_job("follow_bootstrap", "resume jobs")
        page.follow_show_all, page.follow_include_done = self._get_effective_view_flags()
        self.update_follow_filter_controls()
        page.store.set_view(show_all=page.follow_show_all, include_done=page.follow_include_done)
        page.store.load_handoff_options(page.current_username, task_date="")
        self.refresh_follow_tasks()
        if page.follow_poll_after_id is None:
            self.poll_follow_store_events()

    def sync_follow_view_from_store(self, keep_selection=False):
        page = self.page
        if not hasattr(page, "search_entry"):
            return
        try:
            current_task_id = page.active_task.get("task_id") if page.active_task else None
            applied_query = str(getattr(page.store, "search_text", "")).strip().lower()
            try:
                page.follow_search_pending_query = page.search_entry.get().strip().lower()
            except Exception:
                page.follow_search_pending_query = applied_query
            page.follow_search_last_applied_query = applied_query
            current_items = self._filter_items_for_current_section(page.store.filter_local(applied_query))
            page.follow_tasks = list(current_items)
            page.filtered_follow_tasks = list(current_items)
            page.follow_search_scope = str(getattr(page.store, "search_scope", "board")).strip() or "board"
            self.update_follow_scope_hint()
            self.redraw_follow_canvas()

            if not page.filtered_follow_tasks:
                self.clear_follow_form()
                return

            if keep_selection and current_task_id is not None:
                current_item = next(
                    (task for task in page.filtered_follow_tasks if task.get("task_id") == current_task_id),
                    None,
                )
                if current_item:
                    if (
                        page.is_setup_training_section()
                        and getattr(page, "is_training_started", False)
                        and not page.follow_action_inflight
                    ):
                        return
                    page.load_task_into_form(page.store.get_by_id(current_task_id) or current_item)
                    return

            if page.active_task:
                active_task_id = page.active_task.get("task_id")
                if any(task.get("task_id") == active_task_id for task in page.filtered_follow_tasks):
                    return

            self.clear_follow_form()
        finally:
            page.follow_board_suppress_selection_scroll = False

    def _has_pending_follow_poll_work(self):
        page = self.page
        if page.pending_focus_task_id is not None:
            return True
        if page.follow_detail_pending_id is not None:
            return True
        if bool(page.follow_action_inflight):
            return True
        if bool(getattr(page.store, "is_loading", False)):
            return True
        if bool(getattr(page.store, "_handoff_loading_keys", set())):
            return True
        try:
            return not page.store.event_queue.empty()
        except Exception:
            return False

    def should_poll_follow_events(self):
        page = self.page
        if page.rendered_section not in {"follow", "setup_training"}:
            return False
        return self._has_pending_follow_poll_work()

    def poll_follow_store_events(self):
        page = self.page
        if not self.should_poll_follow_events():
            page._debug_job("follow_poll", f"stop section={page.rendered_section}")
            return
        if not page._can_run_page_job("follow_poll", require_visible=True):
            return

        events = page.store.drain_events()
        page._debug_job("follow_poll", f"drain={len(events)}")
        for event in events:
            self.handle_follow_store_event(event)

        if not self.should_poll_follow_events():
            page._debug_job("follow_poll", "idle_stop")
            return

        delay_ms = 180 if events or self._has_pending_follow_poll_work() else 700
        page._schedule_after_slot(
            "follow_poll_after_id",
            delay_ms,
            self.poll_follow_store_events,
            "follow_poll",
            require_visible=True,
        )

    def handle_follow_store_event(self, event):
        page = self.page
        if page.rendered_section not in {"follow", "setup_training"}:
            page._debug_job("follow_event", f"drop section={page.rendered_section} event={event.get('type')}")
            return
        event_type = event.get("type")

        if event_type == "tasks_loaded":
            page._finish_follow_action("refresh")
            page.follow_search_scope = str(event.get("search_scope", "board")).strip() or "board"
            self.sync_follow_view_from_store(keep_selection=True)
            if page.pending_focus_task_id:
                target_task_id = page.pending_focus_task_id
                page.pending_focus_task_id = None
                self.load_task_detail(target_task_id)
            return

        if event_type == "tasks_loading":
            return

        if event_type == "tasks_load_failed":
            page._finish_follow_action("refresh")
            page.follow_tasks = []
            page.filtered_follow_tasks = []
            page.follow_search_scope = "board"
            self.update_follow_scope_hint()
            self.redraw_follow_canvas()
            self.clear_follow_form()
            messagebox.showerror(self.get_task_module_label(), event.get("message", "Khong load duoc task."))
            return

        if event_type == "handoff_options_loaded":
            page.current_display_name = (
                str(event.get("current_display_name", "")).strip()
                or page.current_full_name
                or page.current_username
            )
            page.handoff_options = event.get("options", []) or page.handoff_options
            page.render_handoff_buttons()

            if hasattr(page, "handoff_from_entry") and page.handoff_from_entry is not None:
                page.handoff_from_entry.configure(state="normal")
                page.set_entry_value(page.handoff_from_entry, page.current_display_name)
                page.handoff_from_entry.configure(state="disabled")

            if (
                hasattr(page, "popup_handoff_button_wrap")
                and page.popup_handoff_button_wrap is not None
                and page.popup_handoff_button_wrap.winfo_exists()
            ):
                popup_option_names = [o["display_name"] for o in page.handoff_options]
                if not popup_option_names:
                    popup_option_names = ["Tech Team"]
                if str(getattr(page, "selected_handoff_to", "")).strip() not in popup_option_names:
                    page.selected_handoff_to = popup_option_names[0]
                for child in page.popup_handoff_button_wrap.winfo_children():
                    child.destroy()
                popup_colors = getattr(page, "colors", None) or {
                    "BTN_ACTIVE": page.BTN_ACTIVE,
                    "BTN_INACTIVE": page.BTN_IDLE,
                    "TEXT_DARK": page.TEXT_DARK,
                }
                page.popup_handoff_buttons = page.layout.render_handoff_buttons(
                    page.popup_handoff_button_wrap,
                    popup_option_names,
                    [page.selected_handoff_to] if getattr(page, "selected_handoff_to", "") else [popup_option_names[0]],
                    page.select_popup_handoff,
                    popup_colors,
                )
            return

        if event_type == "task_detail_loaded":
            item = event.get("item") or {}
            page.follow_detail_pending_id = None
            if item:
                if (
                    page.is_setup_training_section()
                    and getattr(page, "is_training_started", False)
                    and page.active_task
                    and item.get("task_id") == page.active_task.get("task_id")
                    and not page.follow_action_inflight
                ):
                    return
                page.load_task_into_form(item)
            return

        if event_type == "task_detail_failed":
            page.follow_detail_pending_id = None
            messagebox.showerror(self.get_task_module_label(), event.get("message", "Khong load duoc task detail."))
            return

        if event_type in {"task_upserted", "task_removed"}:
            self.sync_follow_view_from_store(keep_selection=True)
            return

        if event_type == "task_save_failed":
            page._finish_follow_action("save")
            page._finish_follow_action("update")
            messagebox.showerror(self.get_task_module_label(), event.get("message", "Khong luu duoc task."))
            self.sync_follow_view_from_store(keep_selection=True)
            rollback_item = event.get("rollback_item")
            if rollback_item and event.get("action") == "update":
                page.load_task_into_form(rollback_item)
            return

        if event_type == "task_save_succeeded":
            page._finish_follow_action("save")
            page._finish_follow_action("update")
            if bool(event.get("notification_relevant")):
                page.request_notification_refresh(force=True, duration_ms=20000)
            messagebox.showinfo(self.get_task_module_label(), event.get("message", "Da luu task thanh cong."))
            return

        if event_type == "task_delete_failed":
            page._finish_follow_action("delete")
            messagebox.showerror(self.get_task_module_label(), event.get("message", "Khong xoa duoc task."))
            return

        if event_type == "task_delete_succeeded":
            deleted_task_id = event.get("item_id")
            page._finish_follow_action("delete")
            if page.active_task and page.active_task.get("task_id") == deleted_task_id:
                self.clear_follow_form()
            if bool(event.get("notification_relevant")):
                page.request_notification_refresh(force=True, duration_ms=20000)
            messagebox.showinfo(self.get_task_module_label(), event.get("message", "Da xoa task thanh cong."))
            return

    def get_handoff_option_by_display_name(self, display_name):
        page = self.page
        target = str(display_name or "").strip()
        for option in page.handoff_options:
            if str(option.get("display_name", "")).strip() == target:
                return option
        return None

    def refresh_follow_tasks(self, search_text=None, keep_selection=False, force=False):
        page = self.page
        if not page._can_run_page_job("follow_tasks_refresh", require_visible=False):
            return
        if not page.current_username:
            page.follow_tasks = []
            page.filtered_follow_tasks = []
            page.follow_search_scope = "board"
            self.update_follow_scope_hint()
            self.redraw_follow_canvas()
            self.clear_follow_form()
            return

        effective_search_text = (
            str(search_text).strip().lower()
            if search_text is not None
            else str(getattr(page, "follow_search_last_applied_query", "") or "").strip().lower()
        )
        if hasattr(page, "search_entry") and page.search_entry is not None:
            current_entry_query = page.search_entry.get().strip().lower()
            if search_text is not None and current_entry_query != effective_search_text:
                page.set_entry_value(page.search_entry, effective_search_text)
            page.follow_search_pending_query = page.search_entry.get().strip().lower()
        else:
            page.follow_search_pending_query = effective_search_text
        page.follow_search_last_applied_query = effective_search_text

        previous_view_signature = (
            bool(getattr(page.store, "show_all", False)),
            bool(getattr(page.store, "include_done", False)),
            str(getattr(page.store, "search_text", "")).strip().lower(),
        )
        page.follow_show_all, page.follow_include_done = self._get_effective_view_flags()
        self.update_follow_filter_controls()
        page.store.set_view(
            show_all=page.follow_show_all,
            include_done=page.follow_include_done,
            search_text=effective_search_text,
        )
        next_view_signature = (
            bool(page.follow_show_all),
            bool(page.follow_include_done),
            effective_search_text,
        )
        if next_view_signature != previous_view_signature:
            self._reset_board_scroll_position()
        self.sync_follow_view_from_store(keep_selection=keep_selection)
        page._debug_job(
            "follow_tasks_refresh",
            (
                f"force={force} keep_selection={keep_selection} "
                f"show_all={page.follow_show_all} include_done={page.follow_include_done} "
                f"search='{effective_search_text}'"
            ),
        )
        page.store.load(page.current_username, force=force, background_if_stale=True)
        if page.follow_poll_after_id is None:
            self.poll_follow_store_events()

    def on_follow_refresh_manual(self):
        page = self.page
        if not page._start_follow_action("refresh"):
            return
        self.refresh_follow_tasks(keep_selection=True, force=True)

    def load_task_detail(self, task_id):
        page = self.page
        if not task_id:
            return

        active_task_id = page.active_task.get("task_id") if page.active_task else None
        same_active_task = active_task_id == task_id
        item = page.store.get_by_id(task_id)
        if item:
            if not same_active_task:
                page.load_task_into_form(item)
            if int(task_id) < 0:
                page.follow_detail_pending_id = None
                return
            if item.get("history"):
                page.follow_detail_pending_id = None
                return
        page.follow_detail_pending_id = task_id
        if page.follow_poll_after_id is None:
            self.poll_follow_store_events()
        page.store.ensure_detail(task_id, action_by=page.current_username)

    def collect_follow_form_payload(self):
        page = self.page
        deadline_date, deadline_time, deadline_period = page.get_confirmed_deadline_parts()
        form_data = {
            "merchant_name": page.merchant_name_entry.get(),
            "status": page.selected_status,
            "note": page.note_box.get("1.0", "end"),
            "tracking_number": page.tracking_number_entry.get(),
            "deadline_date": deadline_date,
            "deadline_time": deadline_time,
            "deadline_period": deadline_period,
            "handoff_targets": page.selected_handoff_targets,
            "handoff_options": page.handoff_options,
            "phone": page.phone_entry.get(),
            "problem": page.problem_entry.get(),
        }
        return page.service.build_follow_payload(form_data)

    def apply_follow_search(self):
        self.page.ui_handler.apply_follow_search()

    def update_follow_scope_hint(self):
        page = self.page
        if not hasattr(page, "follow_scope_label"):
            return

        prefix = "Setup / Training" if page.is_setup_training_section() else "Follow"
        if page.follow_search_scope == "show_all_with_done":
            hint_text = f"{prefix}: Show all mode | Co hien Done"
        elif page.follow_search_scope == "show_all_active_not_done":
            hint_text = f"{prefix}: Show all mode | Done hidden"
        else:
            hint_text = f"{prefix}: Board mode | Done hidden | Deadline in 3 days"
        page.follow_scope_label.configure(text=hint_text)

    def update_follow_filter_controls(self):
        page = self.page
        if hasattr(page, "show_all_button"):
            if page.follow_show_all:
                page.show_all_button.configure(
                    text="Show All: ON",
                    fg_color=page.BTN_ACTIVE,
                    hover_color=page.BTN_ACTIVE_HOVER,
                    text_color=page.TEXT_DARK,
                )
            else:
                page.show_all_button.configure(
                    text="Show All: OFF",
                    fg_color=page.BTN_DARK,
                    hover_color=page.BTN_DARK_HOVER,
                    text_color=page.TEXT_LIGHT,
                )

        if hasattr(page, "include_done_switch"):
            if page.follow_include_done:
                page.include_done_switch.select()
            else:
                page.include_done_switch.deselect()

    def toggle_follow_show_all(self):
        self.page.ui_handler.toggle_show_all_tasks()

    def on_follow_include_done_toggle(self):
        page = self.page
        page.follow_include_done = bool(page.include_done_switch.get())
        if page.follow_include_done and not page.follow_show_all:
            page.follow_show_all = True
        self.update_follow_filter_controls()
        self.refresh_follow_tasks(keep_selection=False)

    def toggle_follow_include_done(self):
        self.on_follow_include_done_toggle()

    def clear_follow_search(self):
        self.page.ui_handler.clear_follow_search()

    def get_task_module_label(self):
        page = self.page
        return "Task - Setup / Training" if page.is_setup_training_section() else "Task Follow"

    def get_task_detail_title(self):
        page = self.page
        return "Setup / Training Detail" if page.is_setup_training_section() else "Task Detail"

    def get_default_task_status(self):
        page = self.page
        return "SET UP & TRAINING" if page.is_setup_training_section() else "FOLLOW"

    def get_default_detail_hint(self):
        page = self.page
        if page.is_setup_training_section():
            return "Chon 1 task Setup / Training ben trai de xem giao dien chi tiet."
        return "Chon 1 task ben trai de xem giao dien chi tiet."

    def get_no_match_detail_hint(self):
        page = self.page
        if page.is_setup_training_section():
            return "Khong co task Setup / Training nao khop search."
        return "Khong co task nao khop search."

    def get_new_task_hint(self):
        page = self.page
        if page.is_setup_training_section():
            return (
                "Dang tao task Setup / Training moi. Neu muon tao moi thi bam Save. "
                "Neu dang sua task cu thi chon task ben trai roi bam Update."
            )
        return "Dang tao task moi. Neu muon tao moi thi bam Save. Neu dang sua task cu thi chon task ben trai roi bam Update."

    def get_empty_board_text(self, show_all=False, include_done=False, has_search=False):
        page = self.page
        if has_search:
            if page.is_setup_training_section():
                return "Khong tim thay task Setup / Training nao khop merchant search."
            return "Khong tim thay task nao khop merchant search trong board hien tai."
        if show_all and include_done:
            if page.is_setup_training_section():
                return "Khong co task Setup / Training nao khop bo loc Show all + Include Done."
            return "Khong co task nao khop bo loc Show all + Include Done."
        if show_all:
            if page.is_setup_training_section():
                return "Khong co task Setup / Training nao khop bo loc Show all."
            return "Khong co task nao khop bo loc Show all."
        if page.is_setup_training_section():
            return "Chua co task Setup / Training nao trong board hien tai."
        return "Chua co task nao trong board hien tai."

    def get_section_filtered_tasks(self, query=""):
        page = self.page
        effective_query = (
            query
            if query is not None
            else str(getattr(page, "follow_search_last_applied_query", "") or "").strip().lower()
        )
        items = page.store.filter_local(effective_query)
        if not page.is_setup_training_section():
            return items
        return [
            item
            for item in items
            if self._is_setup_training_item(item)
        ]

    def redraw_follow_canvas(self, force=False):
        page = self.page
        if not hasattr(page, "follow_canvas") or not hasattr(page, "follow_header_canvas"):
            return
        if not page._can_run_page_job("follow_canvas_render", require_visible=True):
            return

        canvas = page.follow_canvas
        header_canvas = page.follow_header_canvas
        try:
            page.follow_canvas_last_render_size = (
                int(canvas.winfo_width()),
                int(canvas.winfo_height()),
            )
        except Exception:
            page.follow_canvas_last_render_size = (0, 0)
        try:
            previous_yview = canvas.yview()[0]
        except Exception:
            previous_yview = 0.0
        try:
            previous_xview = header_canvas.xview()[0]
        except Exception:
            previous_xview = 0.0
        is_training = page.is_setup_training_section()
        row_metrics = self._get_board_row_metrics(is_training)
        row_height = row_metrics["row_height"]
        row_gap = row_metrics["row_gap"]
        row_stride = row_metrics["row_stride"]
        first_row_y = row_metrics["first_row_y"]
        content_padding = 12 if is_training else 46
        header_height = 0 if is_training else 62
        scrollbar_height = 18
        canvas_width = max(canvas.winfo_width(), 220 if is_training else 640)
        canvas_height = max(canvas.winfo_height(), 1)
        tasks = page.filtered_follow_tasks or []
        active_task_id = page.active_task.get("task_id") if page.active_task else None
        content_bottom = self._calculate_board_content_bottom(
            len(tasks),
            first_row_y,
            row_stride,
            row_metrics["bottom_padding"],
        )
        total_scroll_height = max(content_bottom, canvas_height)
        visible_range = self._calculate_visible_task_range(
            canvas,
            len(tasks),
            first_row_y,
            row_stride,
            total_scroll_height,
            buffer_rows=getattr(page, "follow_board_virtual_buffer_rows", 10),
        )
        self._set_current_board_visible_range(visible_range)
        render_signature = self._build_follow_board_signature(
            tasks,
            canvas_width,
            canvas_height,
            is_training,
            active_task_id,
            visible_range,
        )
        if not force and render_signature == getattr(page, "follow_board_render_signature", None):
            return

        page.follow_board_render_signature = render_signature
        canvas.delete("all")
        header_canvas.delete("all")
        page.canvas_row_hits = []

        if is_training:
            header_canvas.grid_remove()
        else:
            header_canvas.grid()

        if not is_training:
            header_ratios = [
                ("Merchant", 0.25),
                ("Phone", 0.13),
                ("Problem", 0.22),
                ("Assignee", 0.12),
                ("Deadline", 0.14),
                ("Status", 0.14),
            ]
            min_widths = {
                "Merchant": 155,
                "Phone": 105,
                "Problem": 145,
                "Assignee": 100,
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

            page.renderer.draw_round_rect(
                header_canvas,
                x,
                6,
                board_right,
                6 + row_height,
                14,
                page.CANVAS_HEADER,
                page.CANVAS_HEADER,
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
            header_canvas.xview_moveto(previous_xview)
            y = first_row_y
        else:
            x = 10
            y = first_row_y
            board_right = max(x + 172, canvas_width - 14)
            resolved_headers = []

        content_height = header_height + content_padding
        if tasks:
            content_height += len(tasks) * row_height + max(0, len(tasks) - 1) * row_gap
        self.update_follow_board_height(content_height + scrollbar_height)

        if not tasks:
            empty_text = self.get_empty_board_text()
            if page.follow_show_all and page.follow_include_done:
                empty_text = self.get_empty_board_text(show_all=True, include_done=True)
            elif page.follow_show_all:
                empty_text = self.get_empty_board_text(show_all=True)
            elif page.search_entry.get().strip():
                empty_text = self.get_empty_board_text(has_search=True)
            canvas.create_text(
                x + 16,
                y + 24,
                text=empty_text,
                anchor="w",
                fill=page.TEXT_MUTED,
                font=("Segoe UI", 12),
            )
            canvas.configure(scrollregion=(0, 0, board_right + 10, y + 70))
            header_canvas.configure(scrollregion=(0, 0, board_right + 10, row_height + 14))
            page.follow_board_scroll_enabled = False

        page.follow_canvas_row_meta = {}
        page.follow_canvas_active_task_id = active_task_id
        visible_start, visible_end = visible_range
        visible_tasks = tasks[visible_start:visible_end]
        for index, task in enumerate(visible_tasks, start=visible_start):
            row_top = y + (index * row_stride)
            row_bottom = row_top + row_height
            is_active = task.get("task_id") == active_task_id
            if is_training:
                row_fill, row_text = self.get_task_row_theme(task, index)
                border_color = "#e5d0ad"
            else:
                row_fill, row_text = self.get_task_row_theme(task, index)
                border_color = "#e5d0ad"
            border_width = 1

            page.renderer.draw_round_rect(
                canvas,
                x,
                row_top,
                board_right,
                row_bottom,
                12,
                row_fill,
                border_color,
                width=border_width,
            )

            if is_training:
                stage_val = str(task.get("status", "")).strip().upper()
                stage_text = "Done" if stage_val == "DONE" else ("2nd" if stage_val == "2ND TRAINING" else "1st")
                stage_color = "#7c3aed" if stage_val == "SET UP & TRAINING" else ("#0f766e" if stage_val == "2ND TRAINING" else "#dc2626")
                assignee_text = str(task.get("handoff_to", "")).strip() or "Tech Team"
                merchant_label = str(task.get("merchant_raw", "")).strip()
                zip_code = str(task.get("zip_code", "")).strip()
                if zip_code and zip_code not in merchant_label:
                    merchant_label = f"{merchant_label} {zip_code}".strip()
                canvas.create_rectangle(x + 8, row_top + 8, x + 11, row_bottom - 8, fill=stage_color, outline="")
                canvas.create_text(
                    x + 18,
                    row_top + 13,
                    text=merchant_label,
                    anchor="w",
                    width=max(72, board_right - x - 28),
                    fill=row_text,
                    font=("Segoe UI", 10, "bold"),
                )
                deadline_text = str(task.get("deadline", "")).strip()
                deadline_text = f"Due: {deadline_text}" if deadline_text else "Due: -"
                badge_width = 40 if stage_text == "Done" else 34
                badge_x2 = board_right - 10
                badge_x1 = badge_x2 - badge_width
                assignee_width = min(92, max(52, (len(assignee_text) * 6) + 18))
                assignee_x2 = board_right - 10
                assignee_x1 = assignee_x2 - assignee_width
                assignee_y1 = row_top + 6
                assignee_y2 = assignee_y1 + 14
                canvas.create_text(
                    x + 18,
                    row_top + 32,
                    text=deadline_text,
                    anchor="w",
                    width=max(44, assignee_x1 - x - 24),
                    fill=row_text,
                    font=("Segoe UI", 8),
                )
                page.renderer.draw_round_rect(
                    canvas,
                    assignee_x1,
                    assignee_y1,
                    assignee_x2,
                    assignee_y2,
                    6,
                    "#f4ead8",
                    "#d8b57b",
                )
                canvas.create_text(
                    (assignee_x1 + assignee_x2) / 2,
                    (assignee_y1 + assignee_y2) / 2,
                    text=assignee_text,
                    fill="#6b4f35",
                    font=("Segoe UI", 7, "bold"),
                    width=max(24, assignee_width - 8),
                )
                badge_y1 = row_top + 24
                badge_y2 = row_top + 38
                page.renderer.draw_round_rect(canvas, badge_x1, badge_y1, badge_x2, badge_y2, 7, stage_color, stage_color)
                canvas.create_text(
                    (badge_x1 + badge_x2) / 2,
                    (badge_y1 + badge_y2) / 2,
                    text=stage_text,
                    fill="#ffffff",
                    font=("Segoe UI", 8, "bold"),
                )
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

                status_meta = page.logic.status_meta.get(task["status"], {"bg": page.BTN_ACTIVE, "text": page.TEXT_DARK})
                pill_x1 = current_x + 8
                pill_y1 = row_top + 9
                pill_x2 = board_right - 8
                pill_y2 = row_bottom - 9
                page.renderer.draw_round_rect(canvas, pill_x1, pill_y1, pill_x2, pill_y2, 12, status_meta["bg"], status_meta["bg"])
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

            row_meta = {
                "task_id": task.get("task_id"),
                "x1": x,
                "y1": row_top,
                "x2": board_right,
                "y2": row_bottom,
                "marker_x1": x + 4,
                "marker_x2": x + 8,
                "active_item_ids": [],
            }
            page.follow_canvas_row_meta[task.get("task_id")] = row_meta
            if is_active:
                self._set_row_active_state(canvas, row_meta, True)
            page.canvas_row_hits.append((row_top, row_bottom, task))

        try:
            visible_height = max(1, canvas.winfo_height())
        except Exception:
            visible_height = 1

        page.follow_board_scroll_enabled = content_bottom > (visible_height + 4)
        canvas.configure(scrollregion=(0, 0, board_right + 10, max(content_bottom, visible_height)))
        target_yview = previous_yview if tasks else 0.0
        page.schedule_follow_scroll_restore(canvas, target_yview)
        header_canvas.xview_moveto(previous_xview)

    def update_follow_board_height(self, content_height):
        page = self.page
        if not hasattr(page, "follow_canvas_wrap"):
            return

        # Keep the board area expanded to the available space; the canvas scrollbar
        # handles overflow so we do not need to shrink the list area to content height.
        target_height = max(
            page.follow_board_min_height,
            int(page.follow_board_max_height),
        )
        if target_height != page.follow_board_height:
            page.follow_board_height = target_height
            page.follow_canvas_wrap.configure(height=page.follow_board_height)

    def get_task_row_theme(self, task, index):
        page = self.page
        try:
            now = datetime.now()
            deadline_date = datetime.strptime(task["deadline_date"], "%d-%m-%Y").date()

            deadline_time = str(task.get("deadline_time", "")).strip()
            deadline_period = str(task.get("deadline_period", "")).strip().upper()
            deadline_dt = None
            if deadline_time and deadline_period in {"AM", "PM"}:
                try:
                    deadline_dt = datetime.strptime(
                        f"{task['deadline_date']} {deadline_time} {deadline_period}",
                        "%d-%m-%Y %I:%M %p",
                    )
                except Exception:
                    deadline_dt = None

            if deadline_dt is not None:
                if deadline_dt < now:
                    return page.CANVAS_PAST_DUE, page.CANVAS_PAST_DUE_TEXT
            elif deadline_date < now.date():
                return page.CANVAS_PAST_DUE, page.CANVAS_PAST_DUE_TEXT

            days_left = (deadline_date - now.date()).days
            if days_left == 0:
                return page.CANVAS_TODAY, page.CANVAS_TODAY_TEXT
            if days_left == 1:
                return page.CANVAS_TOMORROW, page.CANVAS_TOMORROW_TEXT
            if days_left == 2:
                return page.CANVAS_DAY_AFTER, page.CANVAS_DAY_AFTER_TEXT
        except Exception:
            pass
        return (page.CANVAS_ROW if index % 2 == 0 else page.CANVAS_ROW_ALT), page.TEXT_DARK

    def on_follow_canvas_click(self, event):
        page = self.page
        if not page.canvas_row_hits:
            return

        canvas_y = page.follow_canvas.canvasy(event.y)
        for row_top, row_bottom, task in page.canvas_row_hits:
            if row_top <= canvas_y <= row_bottom:
                self.load_task_detail(task.get("task_id"))
                return

    def load_task_into_form(self, task):
        page = self.page
        if page.is_setup_training_section():
            page.setup_training_controller.load_task_into_form(task)
            return

        render_signature = self._build_follow_form_signature(task)
        if render_signature == getattr(page, "follow_form_render_signature", None):
            page.active_task = task
            self.update_follow_canvas_active_task(task.get("task_id"))
            return

        page.active_task = task
        page.follow_form_render_signature = render_signature
        page.detail_hint.configure(text="")
        page.set_entry_value(page.merchant_name_entry, task["merchant_raw"])
        page.set_entry_value(page.phone_entry, task["phone"])
        page.set_entry_value(page.tracking_number_entry, task.get("tracking_number", ""))
        page.set_entry_value(page.problem_entry, task["problem"])
        page.handoff_from_entry.configure(state="normal")
        page.set_entry_value(page.handoff_from_entry, task["handoff_from"])
        page.handoff_from_entry.configure(state="disabled")

        target_names = task.get("handoff_to_display_names") or []
        if not target_names and task.get("handoff_to"):
            target_names = [
                part.strip()
                for part in str(task.get("handoff_to", "")).split(",")
                if part.strip()
            ]
        page.set_selected_handoffs(target_names)
        self.select_status(task["status"])

        page.confirmed_deadline_date = task["deadline_date"]
        page.confirmed_deadline_time = ""
        if task.get("deadline_time") and task.get("deadline_period"):
            page.confirmed_deadline_time = f"{task['deadline_time']} {task['deadline_period']}"
        page.update_deadline_button_text()
        if page.current_username and task.get("deadline_date"):
            page.store.load_handoff_options(
                page.current_username,
                task_date=task["deadline_date"],
                task_time=task.get("deadline_time", ""),
                task_period=task.get("deadline_period", ""),
            )

        if hasattr(page, "note_box") and page.note_box is not None:
            page.note_box.delete("1.0", "end")
            page.note_box.insert("1.0", task["note"])

        self.render_history(task["history"])
        self.update_tracking_controls()
        self.update_follow_form_mode()
        self.update_follow_canvas_active_task(task.get("task_id"))
        page.schedule_detail_scroll_update()

    def clear_follow_form(self):
        page = self.page
        previous_task_id = page.active_task.get("task_id") if page.active_task else None
        if page.is_setup_training_section():
            page.setup_training_controller.clear_form()
            return

        page.active_task = None
        page.follow_form_render_signature = None
        page.follow_history_render_signature = None
        page.detail_hint.configure(text=self.get_no_match_detail_hint())
        for entry in [page.merchant_name_entry, page.phone_entry, page.tracking_number_entry, page.problem_entry]:
            page.set_entry_value(entry, "")
        page.confirmed_deadline_date = ""
        page.confirmed_deadline_time = ""
        page.pending_deadline_date = ""
        page.pending_deadline_time = page.deadline_time_slots[0] if page.deadline_time_slots else ""
        page.update_deadline_button_text()
        page.handoff_from_entry.configure(state="normal")
        page.set_entry_value(page.handoff_from_entry, page.current_display_name)
        page.handoff_from_entry.configure(state="disabled")
        page.note_box.delete("1.0", "end")
        page.set_selected_handoffs(["Tech Team"])
        self.select_status(self.get_default_task_status())
        self.render_history([])
        self.update_tracking_controls()
        self.update_follow_form_mode()
        if previous_task_id is not None:
            self.update_follow_canvas_active_task(None)
        page.schedule_detail_scroll_update()

    def start_new_task(self):
        page = self.page
        if page.is_setup_training_section():
            self.open_quick_create_task_popup()
            return
        page.active_task = None
        self.clear_follow_form()
        page.detail_hint.configure(text=self.get_new_task_hint())

    def open_quick_create_task_popup(self):
        page = self.page
        popup = ctk.CTkToplevel(page.detail_form)
        popup.title("Tao task Setup & Training")
        popup.geometry("420x260")
        popup.resizable(False, False)
        popup.configure(fg_color="#fbf5ec")
        popup.attributes("-topmost", True)
        popup.transient(page.detail_form)
        popup.update_idletasks()
        px = page.detail_form.winfo_rootx() + page.detail_form.winfo_width() // 2 - 210
        py = page.detail_form.winfo_rooty() + page.detail_form.winfo_height() // 2 - 130
        popup.geometry(f"+{px}+{py}")
        frame = ctk.CTkFrame(popup, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=20)
        ctk.CTkLabel(
            frame,
            text="Merchant Name & Zipcode",
            font=("Segoe UI", 13, "bold"),
            text_color=page.TEXT_DARK,
        ).pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(
            frame,
            text="Vi du: DIAMOND NAILS 12345",
            font=("Segoe UI", 10),
            text_color=page.TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 8))
        entry = ctk.CTkEntry(
            frame,
            width=360,
            height=40,
            placeholder_text="MERCHANT NAME ZIPCODE",
            fg_color=page.INPUT_BG,
            border_color=page.INPUT_BORDER,
            text_color=page.TEXT_DARK,
            font=("Segoe UI", 13),
        )
        entry.pack(anchor="w", pady=(0, 16))
        entry.focus()
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(anchor="w")

        def on_cancel():
            popup.destroy()

        def on_create():
            raw = entry.get().strip()
            if not raw:
                messagebox.showwarning("Create Task", "Vui long nhap ten tiem va zipcode.")
                return
            popup.destroy()
            self._confirm_quick_create_task(raw)

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=100,
            height=36,
            corner_radius=10,
            fg_color=page.BTN_DARK,
            hover_color=page.BTN_DARK_HOVER,
            text_color=page.TEXT_LIGHT,
            font=("Segoe UI", 12, "bold"),
            command=on_cancel,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_row,
            text="Create",
            width=120,
            height=36,
            corner_radius=10,
            fg_color="#0f766e",
            hover_color="#115e59",
            text_color="#ffffff",
            font=("Segoe UI", 12, "bold"),
            command=on_create,
        ).pack(side="left")
        entry.bind("<Return>", lambda _e: on_create())

    def _confirm_quick_create_task(self, merchant_raw_text):
        page = self.page
        now = datetime.now()
        payload = {
            "action_by_username": page.current_username,
            "merchant_raw_text": merchant_raw_text,
            "phone": "",
            "tracking_number": "",
            "problem_summary": "Setup + 1st Training",
            "handoff_to_type": "TEAM",
            "handoff_to_username": "",
            "handoff_to_display_name": "Tech Team",
            "handoff_to_usernames": [],
            "handoff_to_display_names": ["Tech Team"],
            "status": "SET UP & TRAINING",
            "deadline_date": now.strftime("%d-%m-%Y"),
            "deadline_time": now.strftime("%I:%M"),
            "deadline_period": now.strftime("%p"),
            "note": "",
            "training_form": [],
            "training_completed_tabs": [],
            "training_started_at": "",
        }
        temp_id = page.store.create_item(
            payload,
            actor_display_name=page.current_display_name,
            action_by=page.current_username,
        )
        self.sync_follow_view_from_store(keep_selection=True)
        self.load_task_detail(temp_id)

    def refresh_follow_layout(self):
        page = self.page
        if not page._can_run_page_job("follow_layout_render", require_visible=True):
            return
        if not hasattr(page, "follow_wrap") or not page.follow_wrap.winfo_exists():
            return
        width = page.follow_wrap.winfo_width()
        height = page.follow_wrap.winfo_height()
        if width <= 1 or height <= 1:
            return

        new_mode = "split"
        page.follow_board_max_height = max(page.follow_board_min_height, height - 110)
        compact_side_width = 180

        page.follow_layout_mode = new_mode
        if page.is_setup_training_section():
            page.follow_wrap.grid_columnconfigure(0, weight=0, minsize=SETUP_BOARD_COMPACT_WIDTH)
            page.follow_wrap.grid_columnconfigure(1, weight=1, minsize=0)
            page.follow_wrap.grid_rowconfigure(1, weight=1, minsize=0)
            page.follow_wrap.grid_rowconfigure(2, weight=0, minsize=0)
            page.table_card.grid_configure(row=1, column=0, padx=(16, 8), pady=(0, 16), sticky="nsw")
            page.detail_card.grid_configure(row=1, column=1, padx=(8, 16), pady=(0, 16), sticky="nsew")
            page.table_card.configure(width=SETUP_BOARD_COMPACT_WIDTH)
            page.detail_card.configure(width=1)
        else:
            page.follow_wrap.grid_columnconfigure(0, weight=85, minsize=0)
            page.follow_wrap.grid_columnconfigure(1, weight=15, minsize=0)
            page.follow_wrap.grid_rowconfigure(1, weight=1, minsize=0)
            page.follow_wrap.grid_rowconfigure(2, weight=0, minsize=0)
            page.table_card.grid_configure(row=1, column=0, padx=(16, 8), pady=(0, 16), sticky="nsew")
            page.detail_card.grid_configure(row=1, column=1, padx=(8, 16), pady=(0, 16), sticky="nsew")
            page.detail_card.configure(width=compact_side_width)

    def render_history(self, history_items):
        page = self.page
        history_box = self._ensure_history_box_cache()
        if history_box is None:
            return

        grouped_history_items = self._build_grouped_history_entries(history_items)
        history_box.update_idletasks()
        available_width = max(history_box.winfo_width(), 280)
        card_width = max(240, available_width - 28)
        note_wraplength = max(210, card_width - 34)
        meta_wraplength = max(180, card_width - 34)
        history_signature = (
            tuple(
                (
                    item.get("entry_id"),
                    item.get("content_signature"),
                )
                for item in grouped_history_items
            ),
            available_width,
        )
        if history_signature == getattr(page, "follow_history_render_signature", None):
            return

        page.follow_history_render_signature = history_signature
        current_task_id = page.active_task.get("task_id") if page.active_task else None
        previous_task_id = getattr(history_box, "_history_owner_task_id", None)
        scroll_fraction = 0.0 if current_task_id != previous_task_id else self._capture_history_scroll_fraction()
        history_box._history_owner_task_id = current_task_id

        entry_cache = getattr(history_box, "_history_entry_cache", {})
        desired_entry_ids = [item.get("entry_id") for item in grouped_history_items]
        desired_entry_id_set = set(desired_entry_ids)

        for entry_id in list(entry_cache.keys()):
            if entry_id in desired_entry_id_set:
                continue
            card = entry_cache.pop(entry_id, None)
            if card is not None:
                try:
                    card.destroy()
                except Exception:
                    pass

        empty_label = getattr(history_box, "_history_empty_label", None)
        if not grouped_history_items:
            for card in entry_cache.values():
                try:
                    card.pack_forget()
                except Exception:
                    pass
            entry_cache.clear()
            if empty_label is None or not empty_label.winfo_exists():
                empty_label = ctk.CTkLabel(
                    history_box,
                    text="Chua co history.",
                    font=("Segoe UI", 12),
                    text_color=page.TEXT_MUTED,
                )
                history_box._history_empty_label = empty_label
            empty_label.pack(anchor="w", padx=8, pady=8)
            history_box._history_entry_order = []
            self._restore_history_scroll_fraction(0.0)
            return

        if empty_label is not None and empty_label.winfo_exists():
            empty_label.pack_forget()

        ordered_cards = []
        for item in grouped_history_items:
            entry_id = item.get("entry_id")
            card = entry_cache.get(entry_id)
            if card is None or not card.winfo_exists():
                card = self._create_history_card(history_box)
                entry_cache[entry_id] = card
            self._update_history_card(
                card,
                item,
                note_wraplength=note_wraplength,
                meta_wraplength=meta_wraplength,
            )
            ordered_cards.append(card)

        for card in ordered_cards:
            try:
                card.pack_forget()
            except Exception:
                pass
            card.pack(fill="x", padx=8, pady=6)

        history_box._history_entry_cache = entry_cache
        history_box._history_entry_order = desired_entry_ids

        page.schedule_detail_scroll_update()
        self._restore_history_scroll_fraction(scroll_fraction)

    def on_follow_save(self):
        page = self.page
        if page.is_setup_training_section():
            messagebox.showinfo(
                self.get_task_module_label(),
                "Task Setup / Training duoc tao tu Task Follow. Vui long mo tu task goc.",
            )
            return
        if page.active_task and page.active_task.get("task_id"):
            messagebox.showwarning(
                self.get_task_module_label(),
                "Task nay dang o che do update. Neu ban muon sua status/note thi bam Update, khong dung Save.",
            )
            return

        payload, error_message = self.collect_follow_form_payload()
        if error_message:
            messagebox.showwarning(self.get_task_module_label(), error_message)
            return

        if not page._start_follow_action("save"):
            return

        temp_id = page.store.create_item(
            payload,
            actor_display_name=page.current_display_name,
            action_by=page.current_username,
        )
        self.sync_follow_view_from_store(keep_selection=True)
        self.load_task_detail(temp_id)

    def on_follow_update(self):
        page = self.page
        if not page.active_task or not page.active_task.get("task_id"):
            messagebox.showwarning(self.get_task_module_label(), "Hay chon task can update.")
            return

        if page.is_setup_training_section():
            page.open_training_completion_popup(action_type="update")
            return

        payload, error_message = self.collect_follow_form_payload()
        if error_message:
            messagebox.showwarning(self.get_task_module_label(), error_message)
            return

        if not page._start_follow_action("update"):
            return

        page.store.update_item(
            page.active_task["task_id"],
            payload,
            actor_display_name=page.current_display_name,
            action_by=page.current_username,
        )

    def on_follow_delete(self):
        page = self.page
        if not page.active_task or not page.active_task.get("task_id"):
            messagebox.showwarning(self.get_task_module_label(), "Hay chon task can xoa.")
            return

        if page.is_setup_training_section():
            messagebox.showinfo(self.get_task_module_label(), "Vui long xoa task tu Task Follow.")
            return

        confirm = messagebox.askyesno(
            self.get_task_module_label(),
            "Ban co chac muon xoa task nay khoi he thong khong?\nTask se bi xoa hoan toan khoi DB.",
        )
        if not confirm:
            return

        if not page._start_follow_action("delete"):
            return

        page.store.delete_item(
            page.active_task["task_id"],
            action_by=page.current_username,
        )
