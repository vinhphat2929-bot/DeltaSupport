import tkinter as tk
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk


class TaskSetupTrainingController:
    TAB_ORDER = ["I. SET UP", "II. HƯỚNG DẪN", "III. THEO DÕI"]

    def __init__(self, page):
        self.page = page

    def get_training_stage_key(self, task=None):
        page = self.page
        return page.logic.get_training_stage_key((task or page.active_task or {}).get("status", ""))

    def get_training_template_sections(self, stage_key=None):
        page = self.page
        return page.logic.get_training_template_sections(stage_key or self.get_training_stage_key())

    def merge_training_form_with_template(self, saved_sections, stage_key=None):
        page = self.page
        templates = self.get_training_template_sections(stage_key)
        return page.logic.merge_training_form_with_template(saved_sections, templates)

    def update_training_info_card(self, task):
        page = self.page
        if not page.is_setup_training_section():
            return

        current_task = task or {}
        merchant_label = str(current_task.get("merchant_name", "")).strip() or str(current_task.get("merchant_raw", "")).strip()
        zip_code = str(current_task.get("zip_code", "")).strip()
        if zip_code and zip_code not in merchant_label:
            merchant_label = f"{merchant_label}  {zip_code}".strip()
        if hasattr(page, "training_merchant_label") and page.training_merchant_label:
            page.training_merchant_label.configure(text=merchant_label or "-")

        deadline_date = str(current_task.get("deadline_date", "")).strip()
        deadline_time = str(current_task.get("deadline_time", "")).strip()
        deadline_period = str(current_task.get("deadline_period", "")).strip()
        if deadline_date and deadline_time and deadline_period:
            date_label = f"Ngay hen: {deadline_date}  {deadline_time} {deadline_period}"
        elif deadline_date:
            date_label = f"Ngay hen: {deadline_date}"
        else:
            date_label = "Ngay hen: -"
        if hasattr(page, "training_date_label") and page.training_date_label:
            page.training_date_label.configure(text=date_label)

        is_second = self.get_training_stage_key(current_task) == "second"
        stage_text = "2nd Training" if is_second else "1st Setup & Training"
        stage_color = "#0ea5a3" if is_second else "#9333ea"
        if hasattr(page, "training_stage_badge") and page.training_stage_badge:
            page.training_stage_badge.configure(text=stage_text, fg_color=stage_color)

        if hasattr(page, "follow_complete_training_button"):
            page.follow_complete_training_button.configure(text="Complete 2nd Training" if is_second else "Complete 1st Training")

    def build_setup_training_form(self, colors, titles):
        page = self.page
        form_callbacks = {
            "on_canvas_yview": self.on_training_canvas_yview,
            "on_update": page.on_follow_update,
            "on_complete_training": self.on_complete_training_stage,
            "on_handoff_change": page.select_handoff,
            "on_deadline_click": page.toggle_deadline_popup,
            "on_tab_change": self.on_training_tab_change,
            "on_start_training": self.on_start_training,
            "on_complete_tab": self.on_complete_current_tab,
            "on_view_training_info": self.on_view_training_info,
        }
        form_widgets = page.layout.build_setup_training_detail_form(page.detail_form, colors, form_callbacks, titles)
        page.detail_hint = form_widgets["detail_hint"]
        page.training_merchant_label = form_widgets["training_merchant_label"]
        page.training_date_label = form_widgets.get("training_date_label")
        page.training_stage_badge = form_widgets["training_stage_badge"]
        page.start_training_button = form_widgets["start_training_button"]
        page.tab_wrap = form_widgets["tab_wrap"]
        page.checklist_tabs = form_widgets["checklist_tabs"]
        page.training_sections_wrap = form_widgets["training_sections_wrap"]
        page.training_canvas = form_widgets["training_canvas"]
        page.training_list_frame = form_widgets["training_list_frame"]
        page.action_row = form_widgets["action_row"]
        page.follow_update_button = form_widgets["follow_update_button"]
        page.complete_tab_button = form_widgets["complete_tab_button"]
        page.follow_complete_training_button = form_widgets["follow_complete_training_button"]
        page.view_training_info_button = form_widgets["view_training_info_button"]
        page.history_box = form_widgets["history_box"]
        page.is_training_started = False
        page.completed_tabs = set()
        if page.training_canvas is not None:
            page.training_canvas.bind("<Configure>", self.on_training_canvas_configure)
            page.training_canvas.bind("<Button-1>", self.on_training_canvas_click)
            page.training_canvas.bind(
                "<MouseWheel>",
                lambda e: self.on_training_canvas_yview("scroll", -1 * (e.delta // 120), "units"),
            )

    def load_task_into_form(self, task):
        page = self.page
        page.active_task = task
        page.detail_hint.configure(
            text=(
                f"Dang xem {page.get_task_module_label().lower()}: {task['merchant_name']} | "
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
        page.set_selected_handoffs(target_names)
        page.is_training_started = False
        page.completed_tabs = set()
        page.training_form_draft_sections = list(task.get("training_form") or [])
        self.update_training_info_card(task)
        self.render_setup_training_sections(page.training_form_draft_sections)
        page.render_history(task["history"])
        page.update_follow_form_mode()
        page.after_idle(page.update_detail_scrollregion)

    def clear_form(self):
        page = self.page
        page.active_task = None
        page.detail_hint.configure(text=page.get_no_match_detail_hint())
        page.set_selected_handoffs(["Tech Team"])
        page.training_form_draft_sections = []
        page.completed_tabs = set()
        self.update_training_info_card({})
        self.render_setup_training_sections([])
        page.render_history([])
        page.update_follow_form_mode()
        page.after_idle(page.update_detail_scrollregion)

    def render_setup_training_sections(self, saved_sections):
        page = self.page
        if getattr(page, "training_note_entries", None):
            for row_key, note_entry in list(page.training_note_entries.items()):
                try:
                    page.training_note_values[row_key] = note_entry.get().strip()
                except Exception:
                    pass

        if not hasattr(page, "training_list_frame") or page.training_list_frame is None:
            return

        page.training_result_vars = {}
        page.training_note_entries = {}
        page.training_canvas_flat_rows = []

        for item in list(page.training_canvas_window_map.values()):
            try:
                item["widget"].destroy()
            except Exception:
                pass
        page.training_canvas_window_map = {}

        sections = self.merge_training_form_with_template(saved_sections, self.get_training_stage_key())
        current_section_key = self.get_current_section_key()
        visible_sections = [
            section for section in sections if section.get("section_key") == current_section_key
        ]

        for section in visible_sections:
            page.training_canvas_flat_rows.append(
                {
                    "kind": "banner",
                    "section_key": section.get("section_key", ""),
                    "title": section.get("title", ""),
                    "subtitle": section.get("subtitle", ""),
                }
            )
            page.training_canvas_flat_rows.append(
                {
                    "kind": "columns",
                    "section_key": section.get("section_key", ""),
                }
            )
            for row in section.get("rows", []):
                row_entry = {
                    "kind": row.get("kind", "normal"),
                    "section_key": section.get("section_key", ""),
                    "step": row.get("step", ""),
                    "label": row.get("label", ""),
                    "result": row.get("result", ""),
                    "note": row.get("note", ""),
                }
                page.training_canvas_flat_rows.append(row_entry)
                if row_entry["kind"] == "normal":
                    row_key = (
                        row_entry["section_key"],
                        str(row_entry["step"]),
                        str(row_entry["label"]),
                    )
                    page.training_result_vars[row_key] = tk.StringVar(
                        value=str(row_entry["result"]).strip().upper()
                    )

        self.redraw_training_canvas()
        self.schedule_training_canvas_refresh()
        page.after_idle(self.refresh_visible_training_widgets)

    def get_current_section_key(self):
        stage_key = self.get_training_stage_key()
        if stage_key == "second":
            return "second_training"

        page = self.page
        tab = getattr(page, "current_training_tab", "I. SET UP")
        if tab == "I. SET UP":
            return "devices"
        if tab == "II. HƯỚNG DẪN":
            return "pos"
        if tab == "III. THEO DÕI":
            return "first_training"
        return "devices"

    def redraw_training_canvas(self):
        page = self.page
        canvas = getattr(page, "training_canvas", None)
        if canvas is None:
            return

        section_key = self.get_current_section_key()
        filtered_rows = [row for row in page.training_canvas_flat_rows if row.get("section_key") == section_key]
        content_height, layout = page.renderer.redraw_training_canvas(
            canvas=canvas,
            flat_rows=filtered_rows,
            training_note_entries=page.training_note_entries,
            training_note_values=page.training_note_values,
            canvas_width=max(720, canvas.winfo_width()),
            banner_bg=page.TRAINING_BANNER_BG,
            subheader_bg=page.TRAINING_SUBHEADER_BG,
            group_bg=page.TRAINING_GROUP_BG,
        )
        page.training_canvas_row_layout = layout
        page.training_canvas_content_height = content_height
        try:
            canvas.configure(height=max(240, content_height))
        except Exception:
            pass

    def schedule_training_canvas_refresh(self):
        page = self.page
        if page.training_canvas_after_id:
            try:
                page.after_cancel(page.training_canvas_after_id)
            except Exception:
                pass
        page.training_canvas_after_id = page.after(16, self.refresh_visible_training_widgets)

    def on_training_canvas_configure(self, _event=None):
        self.redraw_training_canvas()
        self.schedule_training_canvas_refresh()

    def on_training_canvas_yview(self, *args):
        return

    def on_training_canvas_click(self, event):
        page = self.page
        canvas = getattr(page, "training_canvas", None)
        if canvas is None:
            return
        cx = canvas.canvasx(event.x)
        cy = canvas.canvasy(event.y)
        for row in page.training_canvas_row_layout:
            if row.get("kind") != "normal":
                continue
            hit = row.get("result_hit")
            if not hit:
                continue
            x1, y1, x2, y2 = hit
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                cur = str(row.get("result", "")).strip().upper()
                new_value = "DONE" if cur == "" else ("X" if cur == "DONE" else "")
                row["result"] = new_value
                row_key = (row.get("section_key", ""), row.get("step", ""), row.get("label", ""))
                result_var = page.training_result_vars.get(row_key)
                if result_var is not None:
                    try:
                        result_var.set(new_value)
                    except Exception:
                        pass
                for flat_row in page.training_canvas_flat_rows:
                    if (
                        flat_row.get("kind") == "normal"
                        and flat_row.get("section_key") == row.get("section_key")
                        and flat_row.get("step") == row.get("step")
                        and flat_row.get("label") == row.get("label")
                    ):
                        flat_row["result"] = new_value
                        break
                self.redraw_training_canvas()
                self.schedule_training_canvas_refresh()
                return

    def refresh_visible_training_widgets(self):
        page = self.page
        page.training_canvas_after_id = None
        canvas = getattr(page, "training_canvas", None)
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

        for row in page.training_canvas_row_layout:
            if row.get("kind") != "normal":
                continue
            row_top = row.get("y", 0)
            row_bottom = row_top + row.get("height", 0)
            row_key = (row.get("section_key", ""), row.get("step", ""), row.get("label", ""))
            if row_bottom < top_y - 80 or row_top > bottom_y + 80:
                continue

            visible_keys.add(row_key)
            result_var = page.training_result_vars.get(row_key)
            if result_var is None:
                result_var = tk.StringVar(value=str(row.get("result", "")).strip())
                page.training_result_vars[row_key] = result_var

            result_item = page.training_canvas_window_map.get((row_key, "result"))
            if result_item is None:
                current_val = str(result_var.get()).strip().upper()

                def make_toggle(rv, row_identity):
                    def _toggle():
                        cur = str(rv.get()).strip().upper()
                        if cur == "":
                            rv.set("DONE")
                        elif cur == "DONE":
                            rv.set("X")
                        else:
                            rv.set("")
                        for flat_row in page.training_canvas_flat_rows:
                            if (
                                flat_row.get("kind") == "normal"
                                and flat_row.get("section_key") == row_identity[0]
                                and str(flat_row.get("step", "")) == str(row_identity[1])
                                and str(flat_row.get("label", "")) == str(row_identity[2])
                            ):
                                flat_row["result"] = str(rv.get()).strip().upper()
                                break
                        btn_widget = _toggle._btn
                        new_val = str(rv.get()).strip().upper()
                        if new_val == "DONE":
                            btn_widget.configure(fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff", text="DONE")
                        elif new_val == "X":
                            btn_widget.configure(fg_color="#f59e0b", hover_color="#d97706", text_color="#ffffff", text="X")
                        else:
                            btn_widget.configure(fg_color=page.INPUT_BG, hover_color="#f0e8d8", text_color=page.TEXT_MUTED, text="-")
                    return _toggle

                toggle_fn = make_toggle(result_var, row_key)
                if current_val == "DONE":
                    btn_fg, btn_hover, btn_tc, btn_txt = "#ef4444", "#dc2626", "#ffffff", "DONE"
                elif current_val == "X":
                    btn_fg, btn_hover, btn_tc, btn_txt = "#f59e0b", "#d97706", "#ffffff", "X"
                else:
                    btn_fg, btn_hover, btn_tc, btn_txt = page.INPUT_BG, "#f0e8d8", page.TEXT_MUTED, "-"

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
                page.training_canvas_window_map[(row_key, "result")] = {"widget": btn, "window_id": window_id}
            else:
                canvas.coords(result_item["window_id"], result_x, row_top + (row.get("height", 0) / 2))

            note_item = page.training_canvas_window_map.get((row_key, "note"))
            if note_item is None:
                entry = ctk.CTkEntry(
                    canvas,
                    height=26,
                    fg_color=page.INPUT_BG,
                    border_color=page.INPUT_BORDER,
                    text_color=page.TEXT_DARK,
                    placeholder_text="Add note...",
                )
                existing_note = str(page.training_note_values.get(row_key, row.get("note", ""))).strip()
                if existing_note:
                    entry.insert(0, existing_note)
                entry.bind(
                    "<KeyRelease>",
                    lambda _event, rk=row_key, widget=entry: page.training_note_values.__setitem__(rk, widget.get().strip()),
                )
                entry.bind(
                    "<FocusOut>",
                    lambda _event, rk=row_key, widget=entry: page.training_note_values.__setitem__(rk, widget.get().strip()),
                )
                window_id = canvas.create_window(
                    note_x,
                    row_top + (row.get("height", 0) / 2),
                    window=entry,
                    anchor="w",
                    width=note_w - 16,
                    height=26,
                )
                page.training_note_entries[row_key] = entry
                page.training_canvas_window_map[(row_key, "note")] = {"widget": entry, "window_id": window_id}
            else:
                canvas.coords(note_item["window_id"], note_x, row_top + (row.get("height", 0) / 2))
                canvas.itemconfigure(note_item["window_id"], width=note_w - 16)

        for item_key in list(page.training_canvas_window_map.keys()):
            row_key = item_key[0]
            if row_key not in visible_keys:
                item = page.training_canvas_window_map.pop(item_key, None)
                if item:
                    if item_key[1] == "note":
                        try:
                            page.training_note_values[row_key] = item["widget"].get().strip()
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
                        page.training_note_entries.pop(row_key, None)

    def _get_training_sections_source(self):
        page = self.page
        draft_sections = getattr(page, "training_form_draft_sections", None)
        if draft_sections:
            return draft_sections
        if page.active_task:
            return page.active_task.get("training_form") or []
        return []

    def collect_training_form_sections(self, source_sections=None):
        page = self.page
        saved_sections = source_sections if source_sections is not None else self._get_training_sections_source()
        sections = self.merge_training_form_with_template(saved_sections, self.get_training_stage_key())
        collected_sections = []
        for section in sections:
            collected_rows = []
            for row in section.get("rows", []):
                row_key = (section["section_key"], row["step"], row["label"])
                result_value = page.training_result_vars.get(row_key).get().strip() if row_key in page.training_result_vars else str(row.get("result", "")).strip()
                note_entry = page.training_note_entries.get(row_key)
                if note_entry is not None:
                    note_value = note_entry.get().strip()
                else:
                    note_value = str(page.training_note_values.get(row_key, "")).strip()
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

    def _sync_training_form_draft(self):
        page = self.page
        page.training_form_draft_sections = self.collect_training_form_sections(
            source_sections=self._get_training_sections_source()
        )
        return page.training_form_draft_sections

    def collect_setup_training_payload(self, complete_first=False, complete_second=False, from_popup=False):
        page = self.page
        self._sync_training_form_draft()
        deadline_date, deadline_time, deadline_period = page.get_confirmed_deadline_parts()
        if from_popup:
            note_val = page.popup_note_box.get("1.0", "end") if hasattr(page, "popup_note_box") else ""
            handoffs = [page.selected_handoff_to] if getattr(page, "selected_handoff_to", "") else []
        else:
            note_val = page.note_box.get("1.0", "end") if hasattr(page, "note_box") else ""
            handoffs = getattr(page, "selected_handoff_targets", [])

        form_data = {
            "handoff_targets": handoffs,
            "handoff_options": page.handoff_options,
            "note": note_val,
            "training_form": list(page.training_form_draft_sections),
            "training_completed_tabs": list(getattr(page, "completed_tabs", set())),
            "deadline_date": deadline_date,
            "deadline_time": deadline_time,
            "deadline_period": deadline_period,
        }
        return page.service.build_training_payload(page.active_task, form_data, complete_first=complete_first, complete_second=complete_second)

    def open_setup_training_from_follow(self):
        return self.page.ui_handler.open_setup_training_from_follow()

    def on_complete_training_stage(self):
        page = self.page
        if not page.active_task or not page.active_task.get("task_id"):
            messagebox.showwarning(page.get_task_module_label(), "Hay chon task can hoan tat training.")
            return
        self._sync_training_form_draft()
        self.open_training_completion_popup(action_type="complete")

    def open_training_completion_popup(self, action_type="update"):
        page = self.page
        if page.training_popup:
            try:
                page.training_popup.destroy()
            except Exception:
                pass
            page.training_popup = None

        colors = getattr(page, "colors", None) or {
            "TEXT_DARK": page.TEXT_DARK,
            "TEXT_MUTED": page.TEXT_MUTED,
            "INPUT_BG": page.INPUT_BG,
            "INPUT_BORDER": page.INPUT_BORDER,
            "BTN_ACTIVE": page.BTN_ACTIVE,
            "BTN_ACTIVE_HOVER": page.BTN_ACTIVE_HOVER,
            "BTN_DARK": page.BTN_DARK,
            "BTN_DARK_HOVER": page.BTN_DARK_HOVER,
            "TEXT_LIGHT": page.TEXT_LIGHT,
            "BTN_INACTIVE": page.BTN_INACTIVE,
        }
        callbacks = {
            "on_popup_deadline_click": self.toggle_popup_deadline,
            "on_popup_cancel": self.close_training_completion_popup,
            "on_popup_confirm": lambda: self.confirm_training_save(action_type),
        }
        w = page.layout.build_training_completion_popup(page.detail_form, colors, callbacks, page.deadline_time_slots)
        page.training_popup = w["popup_window"]
        page.popup_deadline_picker_button = w["popup_deadline_picker_button"]
        page.popup_deadline_value_hint = w["popup_deadline_value_hint"]
        page.popup_handoff_button_wrap = w["popup_handoff_button_wrap"]
        page.popup_note_box = w["popup_note_box"]
        page.popup_handoff_buttons = page.layout.render_handoff_buttons(
            page.popup_handoff_button_wrap,
            [o["display_name"] for o in page.handoff_options],
            [page.selected_handoff_to],
            self.select_popup_handoff,
            colors,
        )
        page.pending_deadline_date = ""
        page.pending_deadline_time = page.deadline_time_slots[0] if page.deadline_time_slots else ""
        self.update_popup_deadline_button_text()

    def close_training_completion_popup(self):
        page = self.page
        if page.training_popup:
            try:
                page.training_popup.destroy()
            except Exception:
                pass
            page.training_popup = None

    def select_popup_handoff(self, target):
        page = self.page
        page.selected_handoff_to = target
        for name, button in page.popup_handoff_buttons.items():
            if name == target:
                button.configure(font=("Segoe UI", 11, "bold"), fg_color=page.BTN_ACTIVE)
            else:
                button.configure(font=("Segoe UI", 11), fg_color=page.BTN_INACTIVE)

    def toggle_popup_deadline(self):
        page = self.page
        page.deadline_target_button = page.popup_deadline_picker_button
        page.deadline_target_hint = page.popup_deadline_value_hint
        page.toggle_deadline_popup()
        if page.deadline_popup_frame:
            page.deadline_popup_frame.lift()
            if page.training_popup:
                page.deadline_popup_frame.master.lift()

    def update_popup_deadline_button_text(self):
        page = self.page
        if hasattr(page, "popup_deadline_picker_button") and page.popup_deadline_picker_button.winfo_exists():
            if page.pending_deadline_date and page.pending_deadline_time:
                page.popup_deadline_picker_button.configure(text=f"{page.pending_deadline_date} {page.pending_deadline_time}")
            else:
                page.popup_deadline_picker_button.configure(text="Choose Date & Time")
            if hasattr(page, "popup_deadline_value_hint") and page.popup_deadline_value_hint.winfo_exists():
                page.popup_deadline_value_hint.configure(text="")

    def confirm_training_save(self, action_type):
        page = self.page
        if action_type == "complete":
            stage_key = page.logic.get_training_stage_key(page.active_task.get("status"))
            is_second = stage_key == "second"
            payload, error_message = self.collect_setup_training_payload(
                complete_first=not is_second,
                complete_second=is_second,
                from_popup=True,
            )
        else:
            payload, error_message = self.collect_setup_training_payload(complete_first=False, from_popup=True)

        if error_message:
            messagebox.showwarning("Training Save", error_message)
            return
        if not page._start_follow_action("update"):
            messagebox.showwarning("Training Save", "Action dang duoc xu ly. Vui long doi vai giay roi bam lai.")
            return
        page.store.update_item(
            page.active_task["task_id"],
            payload,
            actor_display_name=page.current_display_name,
            action_by=page.current_username,
        )
        self.close_training_completion_popup()

    def on_start_training(self):
        page = self.page
        if not page.active_task:
            return
        page.is_training_started = True
        saved = page.active_task.get("training_completed_tabs", [])
        page.completed_tabs = set(saved) if isinstance(saved, list) else set()
        page.training_form_draft_sections = list(page.active_task.get("training_form") or [])
        self.render_setup_training_sections(page.training_form_draft_sections)
        page.update_follow_form_mode()
        self._refresh_tab_lock_state()
        page.after_idle(page.update_detail_scrollregion)

    def _refresh_tab_lock_state(self):
        self._update_complete_button_state()

    def on_training_tab_change(self, value):
        page = self.page
        completed = getattr(page, "completed_tabs", set())
        if value not in self.TAB_ORDER:
            self._switch_training_section(value)
            return
        idx = self.TAB_ORDER.index(value)
        if idx > 0:
            prev_tab = self.TAB_ORDER[idx - 1]
            if prev_tab not in completed:
                messagebox.showwarning("Tab Locked", f"Ban can hoan thanh muc '{prev_tab}' truoc khi chuyen sang '{value}'.")
                last_completed_idx = -1
                for i, t in enumerate(self.TAB_ORDER):
                    if t in completed:
                        last_completed_idx = i
                revert_to = self.TAB_ORDER[min(last_completed_idx + 1, len(self.TAB_ORDER) - 1)]
                if hasattr(page, "checklist_tabs"):
                    page.checklist_tabs.set(revert_to)
                return
        self._switch_training_section(value)

    def _switch_training_section(self, value):
        page = self.page
        if not hasattr(page, "training_sections_wrap"):
            return
        self._sync_training_form_draft()
        page.current_training_tab = value
        self.render_setup_training_sections(page.training_form_draft_sections)
        page.after_idle(page.update_detail_scrollregion)

    def on_complete_current_tab(self):
        page = self.page
        if not hasattr(page, "checklist_tabs"):
            return
        current_tab = page.checklist_tabs.get()
        if current_tab not in self.TAB_ORDER:
            return
        current_idx = self.TAB_ORDER.index(current_tab)
        if not self._all_items_checked_in_section(current_idx):
            messagebox.showwarning("Checklist chua hoan thanh", f"Vui long tich day du tat ca cac muc trong '{current_tab}' truoc khi hoan thanh.")
            return
        completed = getattr(page, "completed_tabs", set())
        completed.add(current_tab)
        page.completed_tabs = completed
        self._sync_training_form_draft()
        if current_idx + 1 < len(self.TAB_ORDER):
            next_tab = self.TAB_ORDER[current_idx + 1]
            page.checklist_tabs.set(next_tab)
            self._switch_training_section(next_tab)
        self._update_complete_button_state()

    def _all_items_checked_in_section(self, section_idx):
        page = self.page
        section_map = {0: "devices", 1: "pos", 2: "first_training"}
        section_key = section_map.get(section_idx)
        if not section_key:
            return True
        has_rows = False
        for row_key, result_var in page.training_result_vars.items():
            if not isinstance(row_key, tuple) or len(row_key) < 3:
                continue
            if str(row_key[0]).strip() != section_key:
                continue
            has_rows = True
            try:
                if str(result_var.get()).strip().upper() not in {"DONE", "X"}:
                    return False
            except Exception:
                return False
        return has_rows

    def _update_complete_button_state(self):
        page = self.page
        if not hasattr(page, "follow_complete_training_button"):
            return
        if hasattr(page, "complete_tab_button"):
            tab_to_label = {
                "I. SET UP": "Complete Set I",
                "II. HƯỚNG DẪN": "Complete Set II",
                "III. THEO DÕI": "Complete Set III",
            }
            current_tab = getattr(page, "current_training_tab", None)
            if not current_tab and hasattr(page, "checklist_tabs"):
                try:
                    current_tab = page.checklist_tabs.get()
                except Exception:
                    current_tab = None
            page.complete_tab_button.configure(text=tab_to_label.get(current_tab, "Complete Set"))
        completed = getattr(page, "completed_tabs", set())
        stage_val = str((page.active_task or {}).get("status", "")).strip().upper()
        if stage_val == "2ND TRAINING":
            can_complete = getattr(page, "is_training_started", False)
        else:
            can_complete = all(t in completed for t in self.TAB_ORDER)
        if can_complete:
            page.follow_complete_training_button.configure(state="normal", fg_color=page.BTN_ACTIVE, hover_color=page.BTN_ACTIVE_HOVER)
        else:
            page.follow_complete_training_button.configure(state="disabled", fg_color="#b8aba0", hover_color="#b8aba0")

    def _autosave_completed_tabs(self):
        page = self.page
        if not page.active_task or not page.active_task.get("task_id"):
            return
        payload, err = self.collect_setup_training_payload(complete_first=False, complete_second=False, from_popup=False)
        if err or not payload:
            return
        if not page._start_follow_action("update"):
            return
        page.store.update_item(
            page.active_task["task_id"],
            payload,
            actor_display_name=page.current_display_name,
            action_by=page.current_username,
        )

    def on_view_training_info(self):
        page = self.page
        if not page.active_task:
            return
        page.is_training_started = True
        saved = page.active_task.get("training_completed_tabs", [])
        page.completed_tabs = set(saved) if isinstance(saved, list) else set()
        page.training_form_draft_sections = list(page.active_task.get("training_form") or [])
        self.render_setup_training_sections(page.training_form_draft_sections)
        page.update_follow_form_mode()
        self._set_sections_read_only()
        page.after_idle(page.update_detail_scrollregion)

    def _set_sections_read_only(self):
        page = self.page
        if not hasattr(page, "training_sections_wrap"):
            return
        for child in page.training_sections_wrap.winfo_descendants():
            try:
                child.configure(state="disabled")
            except Exception:
                pass
