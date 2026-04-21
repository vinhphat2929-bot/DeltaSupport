import re
from datetime import datetime, timedelta
import calendar
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

class ProcessUIHandler:
    def __init__(self, page):
        self.page = page
        self.deadline_calendar_hits = []

    def apply_follow_search(self):
        query = self.page.search_entry.get().strip().lower()
        self.page.filtered_follow_tasks = self.page.get_section_filtered_tasks(query)
        self.page.redraw_follow_canvas()

        if not self.page.filtered_follow_tasks:
            self.page.clear_follow_form()
            return

        if self.page.active_task:
            active_task_id = self.page.active_task.get("task_id")
            for task in self.page.filtered_follow_tasks:
                if task.get("task_id") == active_task_id:
                    return

        if self.page.filtered_follow_tasks:
            self.page.load_task_detail(self.page.filtered_follow_tasks[0].get("task_id"))

    def clear_follow_search(self):
        self.page.search_entry.delete(0, "end")
        self.apply_follow_search()

    def toggle_show_all_tasks(self):
        self.page.follow_show_all = not self.page.follow_show_all
        if not self.page.follow_show_all:
            self.page.follow_include_done = False
        self.page.update_follow_filter_controls()
        self.page.refresh_follow_tasks(keep_selection=False)

    def on_phone_input(self, _event=None):
        digits = re.sub(r"\D", "", self.page.phone_entry.get())[:10]
        formatted = self.page.logic.format_phone(digits)
        self.page.phone_entry.delete(0, "end")
        self.page.phone_entry.insert(0, formatted)

    def set_selected_handoffs(self, handoff_names):
        normalized_names = []
        for name in handoff_names or []:
            target_name = str(name or "").strip()
            if target_name and target_name not in normalized_names:
                normalized_names.append(target_name)

        if "Tech Team" in normalized_names and len(normalized_names) > 1:
            normalized_names = [name for name in normalized_names if name != "Tech Team"]

        if not normalized_names and "Tech Team" in self.page.handoff_buttons:
            normalized_names = ["Tech Team"]
        elif not normalized_names and self.page.handoff_buttons:
            normalized_names = [next(iter(self.page.handoff_buttons))]

        self.page.selected_handoff_targets = normalized_names
        self.page.selected_handoff_to = ", ".join(normalized_names) if normalized_names else "Tech Team"

        for name, button in self.page.handoff_buttons.items():
            if name in self.page.selected_handoff_targets:
                button.configure(
                    fg_color=self.page.BTN_ACTIVE,
                    hover_color=self.page.BTN_ACTIVE_HOVER,
                    text_color=self.page.TEXT_DARK,
                )
            else:
                button.configure(
                    fg_color=self.page.BTN_IDLE,
                    hover_color=self.page.BTN_IDLE_HOVER,
                    text_color=self.page.TEXT_LIGHT,
                )

    def toggle_handoff(self, name):
        target_name = str(name or "").strip()
        if not target_name or target_name not in self.page.handoff_buttons:
            return

        current_targets = list(self.page.selected_handoff_targets or [])
        if target_name == "Tech Team":
            self.set_selected_handoffs(["Tech Team"])
            return

        current_targets = [n for n in current_targets if n != "Tech Team"]
        if target_name in current_targets:
            current_targets = [n for n in current_targets if n != target_name]
        else:
            current_targets.append(target_name)

        if not current_targets:
            current_targets = ["Tech Team"]

        self.set_selected_handoffs(current_targets)

    def select_handoff(self, name):
        self.set_selected_handoffs([name])

    def toggle_deadline_popup(self):
        if self.page.deadline_popup_frame is not None and self.page.deadline_popup_frame.winfo_exists():
            self.close_deadline_popup()
            return
        self.page.open_deadline_popup()

    def close_deadline_popup(self):
        popup = getattr(self.page, "deadline_popup_frame", None)
        if popup is not None and popup.winfo_exists():
            popup.destroy()
        self.page.deadline_popup_frame = None
        self.page.deadline_calendar_canvas = None
        self.deadline_calendar_hits = []

    def shift_deadline_popup_month(self, month_delta):
        current = self.page.deadline_popup_month
        total_month = (current.year * 12 + current.month - 1) + month_delta
        year = total_month // 12
        month = total_month % 12 + 1
        self.page.deadline_popup_month = current.replace(year=year, month=month, day=1)
        self.redraw_deadline_calendar()

    def redraw_deadline_calendar(self):
        canvas = getattr(self.page, "deadline_calendar_canvas", None)
        if canvas is None:
            return

        canvas.delete("all")
        self.deadline_calendar_hits = []

        month_start = self.page.deadline_popup_month
        self.page.deadline_month_label.configure(text=month_start.strftime("%B %Y"))
        day_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        cell_w = 36
        cell_h = 28
        start_x = 8
        start_y = 22
        radius = 10

        for idx, label in enumerate(day_headers):
            x = start_x + idx * cell_w + cell_w / 2
            canvas.create_text(x, 10, text=label, fill=self.page.TEXT_MUTED, font=("Segoe UI", 9, "bold"))

        month_rows = calendar.monthcalendar(month_start.year, month_start.month)
        today = datetime.now().date()
        selected_date = None
        if self.page.pending_deadline_date and self.page.logic.is_valid_deadline_date(self.page.pending_deadline_date):
            selected_date = datetime.strptime(self.page.pending_deadline_date, "%d-%m-%Y").date()

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
                text_color = self.page.TEXT_DARK

                if current_date == today:
                    fill = "#fef3c7"
                    outline = "#e6b450"
                if selected_date and current_date == selected_date:
                    fill = self.page.BTN_ACTIVE
                    outline = self.page.BTN_ACTIVE
                    text_color = self.page.TEXT_DARK

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
                self.page.pending_deadline_date = date_text
                self.redraw_deadline_calendar()
                return

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
            x1, y1
        ]
        return canvas.create_polygon(points, smooth=True, fill=fill, outline=outline)

    def set_active_scroll_target(self, target):
        self.page.active_scroll_target = target

    def clear_active_scroll_target(self, target):
        if getattr(self.page, "active_scroll_target", None) == target:
            self.page.active_scroll_target = None

    def on_follow_wrap_configure(self, event):
        event_width = getattr(event, "width", None)
        event_height = getattr(event, "height", None)
        self.page.schedule_follow_layout_refresh(width=event_width, height=event_height)

    def open_setup_training_from_follow(self):
        if not self.page.active_task or not self.page.active_task.get("task_id"):
            messagebox.showwarning("Task Follow", "Hay chon task Setup / Training truoc.")
            return

        if str(self.page.active_task.get("status", "")).strip().upper() != "SET UP & TRAINING":
            messagebox.showwarning("Task Follow", "Chi task status SET UP & TRAINING moi mo duoc 1st training.")
            return

        self.page.pending_focus_task_id = self.page.active_task.get("task_id")
        self.page.follow_show_all = True
        self.page.render_section("setup_training")

    def render_handoff_buttons(self):
        if not hasattr(self.page, "handoff_button_wrap") or not self.page.handoff_button_wrap.winfo_exists():
            return

        for child in self.page.handoff_button_wrap.winfo_children():
            child.destroy()
        
        colors = {
            "BTN_ACTIVE": self.page.BTN_ACTIVE,
            "BTN_INACTIVE": self.page.BTN_IDLE,
            "TEXT_DARK": self.page.TEXT_DARK,
        }
        
        display_names = [str(opt.get("display_name", "")).strip() for opt in self.page.handoff_options if str(opt.get("display_name", "")).strip()]
        
        self.page.handoff_buttons = self.page.layout.render_handoff_buttons(
            self.page.handoff_button_wrap,
            display_names,
            self.page.selected_handoff_targets,
            self.page.toggle_handoff,
            colors
        )
