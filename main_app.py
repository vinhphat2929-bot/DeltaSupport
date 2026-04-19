import os
import tkinter as tk
import customtkinter as ctk
from PIL import Image
from tkinter import messagebox
from datetime import datetime
import time

from pages.pos_page import POSPage
from pages.sql_page import SQLPage
from pages.link_data_page import LinkDataPage
from pages.process_page import ProcessPage
from pages.tech_schedule_page import TechSchedulePage
from pages.admin_approval_page import AdminApprovalPage
from pages.pin_verify_dialog import PinVerifyDialog
from pages.leave_summary_page import LeaveSummaryPage
from pages.leave_request_page import LeaveRequestPage
from pages.schedule_setup_page import ScheduleSetupPage

from services.auth_service import (
    get_pin_status_api,
    set_pin_api,
    verify_pin_api,
    change_pin_api,
    change_password_api,
    send_forgot_pin_otp_api,
    reset_pin_with_otp_api,
)
from stores.notification_store import NotificationStore

# =========================================================
# DELTA ASSISTANT - DARK EARTH THEME
# =========================================================

# ===== APP =====
BG_APP = "#181411"
BG_SURFACE = "#221c18"
BG_PANEL = "#2b231e"
BG_PANEL_2 = "#332923"

# ===== TOP BAR =====
TOPBAR_BG = "#2f2721"
TOPBAR_BORDER = "#8b6b4a"

# ===== CONTENT =====
CONTENT_BG = "#f3ede4"
CONTENT_INNER = "#fffaf3"
CONTENT_BORDER = "#6e5102"

# ===== BUTTON =====
BTN_ACTIVE = "#c58b42"
BTN_ACTIVE_HOVER = "#d49a50"
BTN_IDLE = "#4a3b32"
BTN_IDLE_HOVER = "#5a483d"
BTN_DANGER = "#a95a3a"
BTN_DANGER_HOVER = "#bc6947"

# ===== TEXT =====
TEXT_MAIN = "#f5efe6"
TEXT_SUB = "#cab9a6"
TEXT_DARK = "#2a221d"
TEXT_MUTED_DARK = "#705d4f"

# ===== INPUT =====
INPUT_BG = "#f7efe4"
INPUT_BORDER = "#8b6b4a"
INPUT_TEXT = "#2a221d"
INPUT_PLACEHOLDER = "#8d7867"


class MainAppPage(ctk.CTkFrame):
    def __init__(self, parent, on_logout, user=None):
        super().__init__(parent, fg_color=BG_APP)

        self.parent = parent
        self.on_logout = on_logout
        self.user = user or {}

        self.current_page = "POS"
        self.functions_started = False

        self.logo_image = None
        self.logo_image_compact = None
        self.lock_icon = None
        self.settings_icon = None
        self.logout_icon = None
        self.menu_open = False
        self.reflow_after_id = None
        self.header_compact_mode = False

        self.header_frame = None
        self.topbar_main = None
        self.body_frame = None
        self.left_box = None
        self.logo_wrap = None
        self.logo_label = None
        self.nav_frame = None
        self.overlay_menu_frame = None
        self.content_wrapper = None
        self.content_frame = None
        self.clock_outer = None
        self.right_info_box = None
        self.app_name_label = None
        self.version_label = None
        self.welcome_label = None
        self.notification_container = None
        self.notification_circle = None
        self.notification_label = None
        self.notification_badge = None
        self.notification_icon_label = None
        self.notification_unread_count = 0
        self.notification_last_unread_count = 0
        self.notification_popup = None
        self.notification_canvas = None
        self.notification_scrollbar = None
        self.notification_refresh_button = None
        self.notification_read_all_button = None
        self.notification_clear_all_button = None
        self.notification_row_hits = []
        self.notification_items = []
        self.notification_poll_after_id = None
        self.notification_refresh_after_id = None
        self.notification_refresh_interval_ms = 30000
        self.notification_fast_refresh_interval_ms = 8000
        self.notification_fast_window_ms = 90000
        self.notification_fast_poll_until = 0.0
        self.notification_action_cooldown_ms = 3000
        self.notification_action_ready_at = {}
        self.notification_action_inflight = set()
        self.notification_action_after_ids = {}
        self.startup_gate_after_id = None
        self.startup_gate_pending = True
        self.notification_store = NotificationStore()
        self.settings_container = None
        self.settings_circle = None
        self.settings_label = None
        self.lock_container = None
        self.lock_circle = None
        self.lock_label = None
        self.logout_container = None
        self.logout_circle = None
        self.logout_label = None

        self.clock_time_label = None
        self.clock_date_label = None
        self.lock_screen_overlay = None
        self.lock_screen_time_label = None
        self.lock_screen_date_label = None
        self.lock_screen_hint_label = None
        self.is_screen_locked = False

        self.nav_buttons = {}
        self.nav_button_order = []
        self.nav_button_widths = {}
        self.nav_widgets = []

        self.work_schedule_button = None
        self.work_schedule_dropdown = None
        self.work_schedule_dropdown_open = False
        self.task_button = None
        self.task_dropdown = None
        self.task_dropdown_open = False

        self.extra_menu_buttons = {}
        self.admin_manager_window = None

        self.old_password_entry = None
        self.new_password_entry = None
        self.confirm_new_password_entry = None

        self.tooltip_window = None

        self.notification_store.seed(
            items=self.user.get("notification_items", []) or [],
            unread_count=self.user.get("notification_unread_count", 0),
        )

        self.build_ui()
        self.update_clock()
        self.after(300, self.setup_click_outside)

        self.after(150, self.reflow_header_layout)
        self.after(200, self.show_welcome_page)
        self.after(220, self.poll_notification_store_events)
        self.after(350, self.start_notification_sync)
        self.startup_gate_after_id = self.after(2200, self.finish_initial_startup)

    # =========================================================
    # HELPERS
    # =========================================================
    def get_base_path(self):
        return os.path.dirname(os.path.abspath(__file__))

    def safe_load_icon(self, filename, size=(24, 24)):
        base_path = self.get_base_path()
        file_path = os.path.join(base_path, "data", filename)

        if not os.path.exists(file_path):
            return None

        try:
            return ctk.CTkImage(Image.open(file_path), size=size)
        except Exception:
            return None

    def safe_load_image_fit(self, filename, max_width, max_height):
        base_path = self.get_base_path()
        file_path = os.path.join(base_path, "data", filename)

        if not os.path.exists(file_path):
            return None

        try:
            image = Image.open(file_path)
            width, height = image.size
            if width <= 0 or height <= 0:
                return None

            scale = min(max_width / width, max_height / height)
            size = (max(1, int(width * scale)), max(1, int(height * scale)))
            return ctk.CTkImage(image, size=size)
        except Exception:
            return None

    def _bind_topbar_action(self, container, circle, icon_label, text_label, command, normal_fg, hover_fg):
        def apply_state(active):
            circle.configure(
                fg_color=hover_fg if active else normal_fg,
                border_color=BTN_ACTIVE if active else TOPBAR_BORDER,
            )
            text_label.configure(text_color=TEXT_MAIN if active else TEXT_SUB)
            container.configure(fg_color="#3a3028" if active else "transparent")

        def on_enter(event=None):
            apply_state(True)

        def on_leave(event=None):
            apply_state(False)

        def on_click(event=None):
            apply_state(True)
            self.after(120, lambda: apply_state(False))
            command()

        container.configure(corner_radius=16)

        for widget in (container, circle, icon_label, text_label):
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", on_click)

        apply_state(False)

    def set_notification_badge_count(self, count):
        try:
            count_value = max(0, int(count))
        except Exception:
            count_value = 0

        self.notification_unread_count = count_value
        if self.notification_badge is None:
            return

        if count_value <= 0:
            self.notification_badge.place_forget()
            return

        badge_text = str(count_value if count_value < 100 else "99+")
        self.notification_badge.configure(text=badge_text)
        self.notification_badge.place(relx=0.82, rely=0.18, anchor="center")

    def build_notification_items(self):
        items = self.notification_store.get_all() or self.user.get("notification_items", []) or []
        normalized = []
        for index, item in enumerate(items):
            normalized.append(
                {
                    "id": item.get("id", f"notif-{index}"),
                    "task_id": item.get("task_id"),
                    "title": str(item.get("title", "")).strip() or "New task assigned",
                    "meta": str(item.get("meta", "")).strip() or "Tap to open Task Follow",
                    "task_section": str(item.get("task_section", "follow")).strip() or "follow",
                    "is_read": bool(item.get("is_read")),
                }
            )
        return normalized

    def _notification_action_is_locked(self, action_key):
        if action_key in self.notification_action_inflight:
            return True
        return time.monotonic() < self.notification_action_ready_at.get(action_key, 0.0)

    def _sync_notification_action_button_states(self):
        button_specs = [
            (self.notification_refresh_button, "manual_refresh", True),
            (
                self.notification_read_all_button,
                "read_all",
                bool(self.notification_items) and self.notification_unread_count > 0,
            ),
            (
                self.notification_clear_all_button,
                "clear_all",
                bool(self.notification_items),
            ),
        ]
        for button, action_key, has_items in button_specs:
            if button is None or not button.winfo_exists():
                continue
            is_locked = self._notification_action_is_locked(action_key) or not has_items
            button.configure(
                state="disabled" if is_locked else "normal",
                fg_color="#6b5847" if is_locked else "#3b3027",
                hover_color="#6b5847" if is_locked else "#514136",
            )

    def _schedule_notification_action_state_refresh(self, action_key):
        existing_after_id = self.notification_action_after_ids.get(action_key)
        if existing_after_id:
            try:
                self.after_cancel(existing_after_id)
            except Exception:
                pass

        if action_key in self.notification_action_inflight:
            self.notification_action_after_ids[action_key] = None
            return

        remaining_ms = int(
            max(0.0, self.notification_action_ready_at.get(action_key, 0.0) - time.monotonic()) * 1000
        )
        if remaining_ms <= 0:
            self.notification_action_after_ids[action_key] = None
            self._sync_notification_action_button_states()
            return

        self.notification_action_after_ids[action_key] = self.after(
            remaining_ms,
            self._sync_notification_action_button_states,
        )

    def _start_notification_action(self, action_key):
        if self._notification_action_is_locked(action_key):
            return False

        self.notification_action_inflight.add(action_key)
        self.notification_action_ready_at[action_key] = time.monotonic() + (
            self.notification_action_cooldown_ms / 1000.0
        )
        self._schedule_notification_action_state_refresh(action_key)
        self._sync_notification_action_button_states()
        return True

    def _finish_notification_action(self, action_key):
        self.notification_action_inflight.discard(action_key)
        self._schedule_notification_action_state_refresh(action_key)
        self._sync_notification_action_button_states()

    def enable_notification_fast_polling(self, duration_ms=None):
        duration_value = self.notification_fast_window_ms if duration_ms is None else max(0, int(duration_ms))
        self.notification_fast_poll_until = max(
            self.notification_fast_poll_until,
            time.monotonic() + (duration_value / 1000.0),
        )

    def get_notification_refresh_interval_ms(self):
        if time.monotonic() < self.notification_fast_poll_until:
            return self.notification_fast_refresh_interval_ms
        return self.notification_refresh_interval_ms

    def start_notification_sync(self):
        self.enable_notification_fast_polling()
        self.refresh_notification_items(force=False)
        self.schedule_notification_refresh()

    def refresh_notification_items(self, force=False):
        username = str(self.user.get("username", "")).strip()
        if not username:
            return

        self.notification_store.load(
            username,
            force=force,
            background_if_stale=True,
        )

    def schedule_notification_refresh(self, delay_ms=None):
        target_delay_ms = self.get_notification_refresh_interval_ms() if delay_ms is None else delay_ms
        if self.notification_refresh_after_id:
            try:
                self.after_cancel(self.notification_refresh_after_id)
            except Exception:
                pass
            self.notification_refresh_after_id = None
        self.notification_refresh_after_id = self.after(
            target_delay_ms,
            lambda: self.refresh_notification_items(force=True),
        )

    def poll_notification_store_events(self):
        for event in self.notification_store.drain_events():
            self.handle_notification_store_event(event)
        self.notification_poll_after_id = self.after(180, self.poll_notification_store_events)

    def handle_notification_store_event(self, event):
        event_type = event.get("type")

        if event_type == "notifications_loading":
            return

        if event_type == "notifications_loaded":
            items = event.get("items", []) or []
            unread_count = event.get("unread_count", len(items))
            previous_unread_count = self.notification_last_unread_count
            self.notification_last_unread_count = unread_count
            self.user["notification_items"] = items
            self.user["notification_unread_count"] = unread_count
            self.notification_items = self.build_notification_items()
            self.set_notification_badge_count(unread_count)
            if self.notification_popup is not None and self.notification_popup.winfo_exists():
                self.redraw_notification_canvas()
                self._sync_notification_action_button_states()
            if event.get("source") == "network":
                if unread_count > previous_unread_count:
                    self.enable_notification_fast_polling()
                self.schedule_notification_refresh()
                self._finish_notification_action("manual_refresh")
            if event.get("source") in {"local-read-all", "local-read"}:
                self._finish_notification_action("read_all")
            return

        if event_type == "notifications_load_failed":
            self._finish_notification_action("manual_refresh")
            self.schedule_notification_refresh()
            return

        if event_type == "notifications_cleared":
            items = event.get("items", []) or []
            unread_count = event.get("unread_count", 0)
            self.notification_last_unread_count = unread_count
            self.user["notification_items"] = items
            self.user["notification_unread_count"] = unread_count
            self.notification_items = self.build_notification_items()
            self.set_notification_badge_count(unread_count)
            if self.notification_popup is not None and self.notification_popup.winfo_exists():
                self.redraw_notification_canvas()
                self._sync_notification_action_button_states()
            self._finish_notification_action("clear_all")
            return

        if event_type == "notifications_clear_failed":
            self._finish_notification_action("clear_all")
            messagebox.showerror("NOTICE", event.get("message", "Khong clear duoc notifications."))
            return

    def toggle_notification_popup(self):
        if self.notification_popup is not None and self.notification_popup.winfo_exists():
            self.hide_notification_popup()
            return
        self.show_notification_popup()

    def show_notification_popup(self):
        if self.notification_container is None or not self.notification_container.winfo_exists():
            return

        self.hide_top_menus(preserve_notification=True)
        self.enable_notification_fast_polling()
        self.refresh_notification_items()
        self.notification_items = self.build_notification_items()
        self.update_idletasks()

        popup_width = 360
        visible_count = max(1, min(4, len(self.notification_items)))
        canvas_height = 78 if not self.notification_items else min(280, visible_count * 70 + max(0, visible_count - 1) * 10 + 10)
        popup_height = canvas_height + 128

        notice_center_x = (
            self.notification_container.winfo_rootx()
            + (self.notification_container.winfo_width() // 2)
        )
        popup_x = max(12, notice_center_x - popup_width // 2)
        popup_y = self.notification_container.winfo_rooty() + self.notification_container.winfo_height() + 10

        host = self.winfo_toplevel()
        host.update_idletasks()
        host_x = host.winfo_rootx()
        host_y = host.winfo_rooty()
        local_popup_x = max(12, popup_x - host_x)
        local_popup_y = max(12, popup_y - host_y)

        popup = ctk.CTkFrame(
            host,
            bg_color="transparent",
            fg_color="#251d17",
            corner_radius=22,
            border_width=1,
            border_color="#b78a52",
            width=popup_width,
            height=popup_height,
        )
        popup.place(x=local_popup_x, y=local_popup_y)
        popup.lift()
        self.notification_popup = popup
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_columnconfigure(1, weight=0)
        popup.configure(height=popup_height)

        ctk.CTkLabel(
            popup,
            text="Notifications",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 4))

        self.notification_refresh_button = ctk.CTkButton(
            popup,
            text="↻",
            width=30,
            height=28,
            corner_radius=10,
            fg_color="#3b3027",
            hover_color="#514136",
            text_color=TEXT_MAIN,
            font=("Segoe UI Symbol", 14, "bold"),
            command=self.on_manual_notification_refresh,
        )
        self.notification_refresh_button.grid(row=0, column=1, sticky="e", padx=(0, 16), pady=(12, 4))
        self._sync_notification_action_button_states()

        ctk.CTkLabel(
            popup,
            text="Unread task updates",
            font=("Segoe UI", 10),
            text_color=TEXT_SUB,
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))

        canvas_wrap = ctk.CTkFrame(
            popup,
            bg_color="#251d17",
            fg_color="#1f1813",
            corner_radius=18,
            border_width=1,
            border_color="#6c5237",
        )
        canvas_wrap.grid(row=2, column=0, columnspan=2, padx=14, pady=(0, 14), sticky="nsew")
        canvas_wrap.grid_columnconfigure(0, weight=1)
        canvas_wrap.grid_rowconfigure(0, weight=1)

        self.notification_canvas = tk.Canvas(
            canvas_wrap,
            width=popup_width - 52,
            height=canvas_height,
            bg="#1f1813",
            highlightthickness=0,
            bd=0,
        )
        self.notification_canvas.grid(row=0, column=0, padx=(8, 0), pady=8, sticky="nsew")
        self.notification_scrollbar = ctk.CTkScrollbar(
            canvas_wrap,
            orientation="vertical",
            fg_color="#1f1813",
            button_color="#7b5b39",
            button_hover_color="#9a7348",
            command=self.notification_canvas.yview,
            width=12,
        )
        self.notification_scrollbar.grid(row=0, column=1, padx=(6, 8), pady=8, sticky="ns")
        self.notification_canvas.configure(yscrollcommand=self.notification_scrollbar.set)
        self.notification_canvas.bind("<Button-1>", self.on_notification_canvas_click)

        footer_row = ctk.CTkFrame(popup, fg_color="transparent")
        footer_row.grid(row=3, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))
        footer_row.grid_columnconfigure(0, weight=1)

        self.notification_read_all_button = ctk.CTkButton(
            footer_row,
            text="Read all",
            width=76,
            height=28,
            corner_radius=10,
            fg_color="#3b3027",
            hover_color="#514136",
            text_color=TEXT_MAIN,
            font=("Segoe UI", 10, "bold"),
            command=self.on_notification_read_all,
        )
        self.notification_read_all_button.grid(row=0, column=1, sticky="e", padx=(0, 8))

        self.notification_clear_all_button = ctk.CTkButton(
            footer_row,
            text="Clear all",
            width=80,
            height=28,
            corner_radius=10,
            fg_color="#3b3027",
            hover_color="#514136",
            text_color=TEXT_MAIN,
            font=("Segoe UI", 10, "bold"),
            command=self.on_notification_clear_all,
        )
        self.notification_clear_all_button.grid(row=0, column=2, sticky="e")

        self.redraw_notification_canvas()
        self._sync_notification_action_button_states()

    def hide_notification_popup(self):
        popup = self.notification_popup
        if popup is not None and popup.winfo_exists():
            popup.place_forget()
            popup.destroy()
        self.notification_popup = None
        self.notification_canvas = None
        self.notification_scrollbar = None
        self.notification_refresh_button = None
        self.notification_read_all_button = None
        self.notification_clear_all_button = None
        self.notification_row_hits = []

    def on_manual_notification_refresh(self):
        if not self._start_notification_action("manual_refresh"):
            return
        self.enable_notification_fast_polling()
        self.refresh_notification_items(force=True)

    def on_notification_read_all(self):
        if not self._start_notification_action("read_all"):
            return
        self.notification_store.mark_all_as_read(
            action_by=str(self.user.get("username", "")).strip(),
        )

    def on_notification_clear_all(self):
        if not self._start_notification_action("clear_all"):
            return
        self.notification_store.clear_all(
            action_by=str(self.user.get("username", "")).strip(),
        )

    def destroy(self):
        self.hide_notification_popup()
        try:
            self.notification_store.flush_pending_reads()
        except Exception:
            pass
        if self.notification_poll_after_id:
            try:
                self.after_cancel(self.notification_poll_after_id)
            except Exception:
                pass
            self.notification_poll_after_id = None
        if self.notification_refresh_after_id:
            try:
                self.after_cancel(self.notification_refresh_after_id)
            except Exception:
                pass
            self.notification_refresh_after_id = None
        for after_id in list(self.notification_action_after_ids.values()):
            if after_id:
                try:
                    self.after_cancel(after_id)
                except Exception:
                    pass
        self.notification_action_after_ids = {}
        if self.startup_gate_after_id:
            try:
                self.after_cancel(self.startup_gate_after_id)
            except Exception:
                pass
            self.startup_gate_after_id = None
        super().destroy()

    def redraw_notification_canvas(self):
        canvas = self.notification_canvas
        if canvas is None:
            return

        canvas.delete("all")
        self.notification_row_hits = []
        items = self.notification_items or []

        if not items:
            canvas.create_text(
                160,
                28,
                text="No new notifications.",
                fill=TEXT_SUB,
                font=("Segoe UI", 12, "bold"),
            )
            canvas.create_text(
                160,
                52,
                text="When there is a new task, it will show here.",
                fill=TEXT_SUB,
                font=("Segoe UI", 10),
            )
            canvas.configure(scrollregion=(0, 0, int(canvas.cget("width")), int(canvas.cget("height"))))
            return

        x1 = 8
        x2 = int(canvas.cget("width")) - 10
        row_height = 66
        gap = 10
        y = 8

        for item in items[:]:
            y1 = y
            y2 = y + row_height
            is_read = bool(item.get("is_read"))
            self.draw_round_rect(
                canvas,
                x1,
                y1,
                x2,
                y2,
                16,
                "#34291f" if not is_read else "#40362f",
                "#8a633b" if not is_read else "#5d4a3a",
            )
            if not is_read:
                canvas.create_oval(
                    x2 - 18,
                    y1 + 28,
                    x2 - 8,
                    y1 + 38,
                    fill=BTN_ACTIVE,
                    outline="",
                )
            canvas.create_text(
                x1 + 16,
                y1 + 20,
                text=item["title"],
                anchor="w",
                fill=TEXT_MAIN if not is_read else "#d8cec2",
                font=("Segoe UI", 10, "bold"),
                width=max(120, x2 - x1 - 44),
            )
            canvas.create_text(
                x1 + 16,
                y1 + 45,
                text=item["meta"],
                anchor="w",
                fill=TEXT_SUB if not is_read else "#a99a8a",
                font=("Segoe UI", 9),
                width=max(120, x2 - x1 - 44),
            )
            self.notification_row_hits.append((x1, y1, x2, y2, item))
            y += row_height + gap

        canvas.configure(scrollregion=(0, 0, int(canvas.cget("width")), y))

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

    def on_notification_canvas_click(self, event):
        for x1, y1, x2, y2, item in self.notification_row_hits:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.notification_store.mark_as_read(
                    item.get("id"),
                    action_by=str(self.user.get("username", "")).strip(),
                )
                self.hide_notification_popup()
                self.show_process_page(
                    item.get("task_section", "follow"),
                    initial_task_id=item.get("task_id"),
                )
                return

    def get_role(self):
        return str(self.user.get("role", "TS Junior")).strip()

    def get_role_key(self):
        return self.get_role().strip().lower()

    def get_department(self):
        return str(self.user.get("department", "")).strip()

    def get_department_key(self):
        return self.get_department().strip().lower()

    def is_technical_support_department(self):
        return self.get_department_key() == "technical support"

    def get_display_role(self):
        return self.get_role()

    def can_open_work_schedule_menu(self):
        role = self.get_role_key()
        return role in [
            "admin",
            "management",
            "hr",
            "leader",
            "manager",
            "ts leader",
            "sale leader",
            "cs leader",
            "mt leader",
        ]

    def can_access(self, page_name):
        role = self.get_role_key()
        is_ts_department = self.is_technical_support_department()

        all_staff_roles = [
            "ts leader",
            "ts senior",
            "ts junior",
            "ts probation",
            "sale leader",
            "sale staff",
            "sale admin",
            "hr",
            "accountant",
            "management",
            "admin",
            "cs leader",
            "cs staff",
            "mt leader",
            "mt staff",
            "leader",
            "manager",
            "tech",
            "techds",
            "sale",
        ]

        if page_name in {"POS", "Link / Data", "Task", "SQL"} and not is_ts_department:
            return False

        permission_map = {
            "POS": all_staff_roles,
            "Link / Data": all_staff_roles,
            "Task": all_staff_roles,
            "SQL": ["ts leader", "ts senior", "management", "admin"],
            "Work Schedule": all_staff_roles,
            "Monthly Leave Summary": [
                "admin",
                "management",
                "hr",
                "accountant",
                "leader",
                "manager",
                "ts leader",
                "sale leader",
            ],
            "Schedule Setup": [
                "admin",
                "management",
                "hr",
                "leader",
                "ts leader",
                "sale leader",
                "cs leader",
                "mt leader",
            ],
            "Create Leave Request": all_staff_roles,
            "Settings": all_staff_roles,
            "Admin Approval": ["admin", "management", "manager", "hr", "leader", "ts leader", "sale leader", "cs leader", "mt leader"],
        }

        allowed_roles = permission_map.get(page_name, ["admin"])
        return role in allowed_roles

    def show_access_denied(self, page_name=None):
        messagebox.showwarning(
            "Not Available",
            "This feature is not available.",
        )

    def clear_content_frame(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def update_function_visibility(self):
        if self.functions_started:
            if self.menu_toggle_btn is not None and not self.menu_toggle_btn.winfo_manager():
                self.menu_toggle_btn.pack(side="left", pady=0)
            if self.nav_frame is not None:
                self.nav_frame.grid()
        else:
            self.hide_top_menus()
            if self.menu_toggle_btn is not None and self.menu_toggle_btn.winfo_manager():
                self.menu_toggle_btn.pack_forget()
            if self.nav_frame is not None:
                self.nav_frame.grid_remove()

        if self.work_schedule_button is not None:
            if self.functions_started:
                self.work_schedule_button.configure(state="normal")
            else:
                self.work_schedule_button.configure(state="disabled")

        if self.task_button is not None:
            if self.functions_started:
                self.task_button.configure(state="normal")
            else:
                self.task_button.configure(state="disabled")

        self.after(50, self.reflow_header_layout)

    def start_function_experience(self):
        self.startup_gate_pending = False
        if self.startup_gate_after_id:
            try:
                self.after_cancel(self.startup_gate_after_id)
            except Exception:
                pass
            self.startup_gate_after_id = None
        self.functions_started = True
        self.update_function_visibility()
        self.show_welcome_page()

    def finish_initial_startup(self):
        self.startup_gate_after_id = None
        if not self.winfo_exists() or self.functions_started:
            return
        self.start_function_experience()

    def set_active_nav(self, active_name):
        self.current_page = active_name

        for page_name, button in self.nav_buttons.items():
            if page_name == active_name:
                button.configure(
                    fg_color=BTN_ACTIVE,
                    hover_color=BTN_ACTIVE_HOVER,
                    text_color=TEXT_DARK,
                    border_color=BTN_ACTIVE,
                )
            else:
                button.configure(
                    fg_color=BTN_IDLE,
                    hover_color=BTN_IDLE_HOVER,
                    text_color=TEXT_MAIN,
                    border_color=BTN_IDLE,
                )

        if self.work_schedule_button is not None:
            if active_name in [
                "Work Schedule",
                "Monthly Leave Summary",
                "Schedule Setup",
                "Create Leave Request",
            ]:
                self.work_schedule_button.configure(
                    fg_color=BTN_ACTIVE,
                    hover_color=BTN_ACTIVE_HOVER,
                    text_color=TEXT_DARK,
                    border_color=BTN_ACTIVE,
                )
            else:
                self.work_schedule_button.configure(
                    fg_color=BTN_IDLE,
                    hover_color=BTN_IDLE_HOVER,
                    text_color=TEXT_MAIN,
                    border_color=BTN_IDLE,
                )

        if self.task_button is not None:
            if active_name in ["Task", "Report", "Follow", "Setup / Training"]:
                self.task_button.configure(
                    fg_color=BTN_ACTIVE,
                    hover_color=BTN_ACTIVE_HOVER,
                    text_color=TEXT_DARK,
                    border_color=BTN_ACTIVE,
                )
            else:
                self.task_button.configure(
                    fg_color=BTN_IDLE,
                    hover_color=BTN_IDLE_HOVER,
                    text_color=TEXT_MAIN,
                    border_color=BTN_IDLE,
                )

    def create_section_title(self, parent, title, subtitle=""):
        if str(getattr(self, "current_page", "")).strip() == "Task":
            return

        title_label = ctk.CTkLabel(
            parent,
            text=title,
            font=("Segoe UI", 30, "bold"),
            text_color=TEXT_DARK,
        )
        title_label.pack(anchor="w", padx=28, pady=(22, 4))

        if subtitle:
            subtitle_label = ctk.CTkLabel(
                parent,
                text=subtitle,
                font=("Segoe UI", 13),
                text_color=TEXT_MUTED_DARK,
            )
            subtitle_label.pack(anchor="w", padx=30, pady=(0, 16))

    def update_clock(self):
        now = datetime.now()

        if self.clock_time_label:
            self.clock_time_label.configure(text=now.strftime("%I:%M %p"))
        if self.clock_date_label:
            self.clock_date_label.configure(text=now.strftime("%a %d/%m/%Y"))
        if self.lock_screen_time_label:
            self.lock_screen_time_label.configure(text=now.strftime("%I:%M %p"))
        if self.lock_screen_date_label:
            self.lock_screen_date_label.configure(text=now.strftime("%a %d/%m/%Y"))

        self.after(1000, self.update_clock)

    def create_fallback_text(self, parent, content):
        text_box = ctk.CTkTextbox(
            parent,
            font=("Segoe UI", 14),
            text_color=TEXT_DARK,
            fg_color=CONTENT_INNER,
            corner_radius=18,
            border_width=1,
            border_color=CONTENT_BORDER,
        )
        text_box.pack(fill="both", expand=True)
        text_box.insert("1.0", content)
        text_box.configure(state="disabled")

    def show_tooltip(self, widget, text):
        self.hide_tooltip()

        x = widget.winfo_rootx() + 10
        y = widget.winfo_rooty() - 36

        self.tooltip_window = ctk.CTkToplevel(self)
        self.tooltip_window.overrideredirect(True)
        self.tooltip_window.attributes("-topmost", True)
        self.tooltip_window.geometry(f"+{x}+{y}")

        tooltip_frame = ctk.CTkFrame(
            self.tooltip_window,
            fg_color="#221c18",
            corner_radius=10,
            border_width=1,
            border_color=TOPBAR_BORDER,
        )
        tooltip_frame.pack()

        tooltip_label = ctk.CTkLabel(
            tooltip_frame,
            text=text,
            font=("Segoe UI", 11),
            text_color=TEXT_MAIN,
            padx=10,
            pady=4,
        )
        tooltip_label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window is not None:
            try:
                self.tooltip_window.destroy()
            except Exception:
                pass
            self.tooltip_window = None

    def bind_tooltip(self, widget, text):
        return

    # =========================================================
    # BUILD UI
    # =========================================================
    def build_ui(self):
        self.logo_image = self.safe_load_image_fit("logo.png", 116, 78)
        if self.logo_image is None:
            self.logo_image = self.safe_load_image_fit("app.ico", 116, 78)
        if self.logo_image is None:
            self.logo_image = self.safe_load_image_fit("home.png", 116, 78)

        self.logo_image_compact = self.safe_load_image_fit("logo.png", 84, 52)
        if self.logo_image_compact is None:
            self.logo_image_compact = self.safe_load_image_fit("app.ico", 84, 52)
        if self.logo_image_compact is None:
            self.logo_image_compact = self.safe_load_image_fit("home.png", 84, 52)

        self.settings_icon = self.safe_load_icon("setting.png", (22, 22))
        self.lock_icon = self.safe_load_icon("lock.png", (22, 22))
        self.logout_icon = self.safe_load_icon("log-out.png", (24, 24))

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.build_header()
        self.build_body()
        self.update_function_visibility()

    def build_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 8))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.topbar_main = ctk.CTkFrame(
            self.header_frame,
            fg_color=TOPBAR_BG,
            corner_radius=20,
            border_width=1,
            border_color=TOPBAR_BORDER,
            height=84,
        )
        self.topbar_main.grid(row=0, column=0, sticky="ew")
        self.topbar_main.grid_propagate(False)

        self.topbar_main.grid_rowconfigure(0, weight=1)
        self.topbar_main.grid_columnconfigure(0, weight=0)
        self.topbar_main.grid_columnconfigure(1, weight=1)
        self.topbar_main.grid_columnconfigure(2, weight=0)

        self.topbar_main.bind("<Configure>", self.on_topbar_resize)

        # ===== LEFT BOX =====
        self.left_box = ctk.CTkFrame(self.topbar_main, fg_color="transparent", height=56)
        self.left_box.grid(row=0, column=0, sticky="w", padx=(14, 8), pady=(12, 12))
        self.left_box.grid_propagate(False)

        if self.logo_image:
            self.logo_wrap = ctk.CTkFrame(
                self.left_box,
                width=88,
                height=56,
                fg_color="transparent",
            )
            self.logo_wrap.pack(side="left", padx=(0, 10), pady=0)
            self.logo_wrap.pack_propagate(False)

            self.logo_label = ctk.CTkLabel(
                self.logo_wrap,
                text="",
                image=self.logo_image_compact or self.logo_image,
            )
            self.logo_label.place(relx=0.5, rely=0.5, anchor="center")

            self.logo_wrap.bind("<Button-1>", lambda e: self.show_welcome_page())
            self.logo_label.bind("<Button-1>", lambda e: self.show_welcome_page())

        self.menu_toggle_btn = ctk.CTkButton(
            self.left_box,
            text="☰",
            width=40,
            height=40,
            corner_radius=11,
            fg_color=BTN_IDLE,
            hover_color=BTN_IDLE_HOVER,
            text_color=TEXT_MAIN,
            font=("Segoe UI", 18, "bold"),
            command=self.toggle_expand_menu,
        )
        self.menu_toggle_btn.pack(side="left", pady=0)

        # ===== NAV =====
        self.nav_frame = ctk.CTkFrame(self.topbar_main, fg_color="transparent")
        self.nav_frame.grid(row=0, column=1, sticky="w", padx=(4, 10), pady=(10, 10))

        self.right_cluster = ctk.CTkFrame(self.topbar_main, fg_color="transparent")
        self.right_cluster.grid(row=0, column=2, sticky="e", padx=(4, 12), pady=(8, 8))

        nav_items = []
        if self.is_technical_support_department():
            ts_nav_items = [
                ("POS", self.show_pos_page, 82),
                ("SQL", self.show_sql_page, 82),
                ("Link / Data", self.show_link_data_page, 96),
                ("Task", self.show_process_page, 100),
            ]
            nav_items = [
                (name, command, btn_width)
                for name, command, btn_width in ts_nav_items
                if self.can_access(name)
            ]

        self.nav_buttons = {}
        self.nav_button_order = []
        self.nav_button_widths = {}
        self.nav_widgets = []

        for name, command, btn_width in nav_items:
            if name == "Task":
                continue
            btn = ctk.CTkButton(
                self.nav_frame,
                text=name,
                width=btn_width,
                height=36,
                corner_radius=12,
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_MAIN,
                border_width=1,
                border_color=BTN_IDLE,
                font=("Segoe UI", 12, "bold"),
                command=command,
            )
            self.nav_buttons[name] = btn
            self.nav_button_order.append(name)
            self.nav_button_widths[name] = btn_width
            self.nav_widgets.append((name, btn, btn_width))

        self.task_button = ctk.CTkButton(
            self.nav_frame,
            text="Task",
            width=100,
            height=36,
            corner_radius=12,
            fg_color=BTN_IDLE,
            hover_color=BTN_IDLE_HOVER,
            text_color=TEXT_MAIN,
            border_width=1,
            border_color=BTN_IDLE,
            font=("Segoe UI", 12, "bold"),
            command=self.toggle_task_dropdown,
        )
        self.nav_widgets.append(("Task", self.task_button, 100))

        self.work_schedule_button = ctk.CTkButton(
            self.nav_frame,
            text="Work Schedule",
            width=126,
            height=36,
            corner_radius=12,
            fg_color=BTN_IDLE,
            hover_color=BTN_IDLE_HOVER,
            text_color=TEXT_MAIN,
            border_width=1,
            border_color=BTN_IDLE,
            font=("Segoe UI", 12, "bold"),
            command=self.toggle_work_schedule_dropdown,
        )
        self.nav_widgets.append(("Work Schedule", self.work_schedule_button, 126))

        self.work_schedule_dropdown = ctk.CTkFrame(
            self,
            fg_color="#201915",
            corner_radius=16,
            border_width=2,
            border_color="#a47b4d",
            width=232,
            height=232,
        )

        work_schedule_dropdown_inner = ctk.CTkFrame(
            self.work_schedule_dropdown,
            fg_color="#2b231e",
            corner_radius=14,
            border_width=1,
            border_color="#5f4934",
        )
        work_schedule_dropdown_inner.pack(fill="both", expand=True, padx=8, pady=8)

        work_items = [
            ("Work Schedule", self.show_work_schedule_page),
            ("Monthly Leave Summary", self.show_leave_summary_page),
            ("Schedule Setup", self.show_schedule_setup_page),
            ("Create Leave Request", self.show_leave_request_page),
        ]

        for i, (name, command) in enumerate(work_items):
            btn = ctk.CTkButton(
                work_schedule_dropdown_inner,
                text=name,
                width=180,
                height=38,
                corner_radius=12,
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_MAIN,
                border_width=1,
                border_color=BTN_IDLE,
                font=("Segoe UI", 12, "bold"),
                anchor="w",
                command=lambda cmd=command: self.handle_work_schedule_menu_action(cmd),
            )
            btn.pack(fill="x", padx=10, pady=(10 if i == 0 else 6, 0))

        self.work_schedule_dropdown.place_forget()

        self.task_dropdown = ctk.CTkFrame(
            self,
            fg_color="#201915",
            corner_radius=16,
            border_width=2,
            border_color="#a47b4d",
            width=220,
            height=190,
        )

        task_dropdown_inner = ctk.CTkFrame(
            self.task_dropdown,
            fg_color="#2b231e",
            corner_radius=14,
            border_width=1,
            border_color="#5f4934",
        )
        task_dropdown_inner.pack(fill="both", expand=True, padx=8, pady=8)

        task_items = [
            ("Report", lambda: self.show_process_page("report")),
            ("Follow", lambda: self.show_process_page("follow")),
            ("Setup / Training", lambda: self.show_process_page("setup_training")),
        ]

        for i, (name, command) in enumerate(task_items):
            btn = ctk.CTkButton(
                task_dropdown_inner,
                text=name,
                width=180,
                height=38,
                corner_radius=12,
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_MAIN,
                border_width=1,
                border_color=BTN_IDLE,
                font=("Segoe UI", 12, "bold"),
                anchor="w",
                command=lambda cmd=command: self.handle_task_menu_action(cmd),
            )
            btn.pack(fill="x", padx=10, pady=(10 if i == 0 else 6, 0))

        self.task_dropdown.place_forget()

        # ===== NOTIFICATION =====
        self.notification_container = ctk.CTkFrame(
            self.right_cluster,
            fg_color="transparent",
            width=76,
            height=70,
        )
        self.notification_container.pack(side="left", padx=(0, 14), pady=(8, 0))
        self.notification_container.grid_propagate(False)

        self.notification_circle = ctk.CTkFrame(
            self.notification_container,
            width=44,
            height=44,
            corner_radius=22,
            fg_color=BTN_IDLE,
            border_width=1,
            border_color=TOPBAR_BORDER,
        )
        self.notification_circle.pack(pady=(0, 3))
        self.notification_circle.pack_propagate(False)

        self.notification_icon_label = ctk.CTkLabel(
            self.notification_circle,
            text="🔔",
            font=("Segoe UI Symbol", 16, "bold"),
            text_color=TEXT_MAIN,
        )
        self.notification_icon_label.place(relx=0.5, rely=0.5, anchor="center")

        self.notification_badge = ctk.CTkLabel(
            self.notification_circle,
            text="0",
            width=18,
            height=18,
            corner_radius=9,
            fg_color="#dc2626",
            text_color="#ffffff",
            font=("Segoe UI", 9, "bold"),
        )

        self.notification_label = ctk.CTkLabel(
            self.notification_container,
            text="NOTICE",
            font=("Segoe UI", 9),
            text_color=TEXT_SUB,
        )
        self.notification_label.pack()

        def _open_notifications(event=None):
            self.toggle_notification_popup()

        self._bind_topbar_action(
            self.notification_container,
            self.notification_circle,
            self.notification_icon_label,
            self.notification_label,
            _open_notifications,
            BTN_IDLE,
            BTN_IDLE_HOVER,
        )
        initial_unread_count = self.user.get("notification_unread_count", 0)
        if not initial_unread_count:
            initial_unread_count = len(self.build_notification_items())
        self.set_notification_badge_count(initial_unread_count)

        # ===== CLOCK =====
        self.clock_outer = ctk.CTkFrame(
            self.right_cluster,
            fg_color="#241d18",
            corner_radius=18,
            border_width=1,
            border_color="#a47b4d",
            width=104,
            height=60,
        )
        self.clock_outer.pack(side="left", padx=(0, 6), pady=(4, 4))
        self.clock_outer.grid_propagate(False)

        clock_inner = ctk.CTkFrame(
            self.clock_outer,
            fg_color=BG_PANEL_2,
            corner_radius=14,
            border_width=1,
            border_color=TOPBAR_BORDER,
        )
        clock_inner.pack(fill="both", expand=True, padx=4, pady=4)
        clock_inner.grid_rowconfigure(0, weight=1)
        clock_inner.grid_rowconfigure(1, weight=1)
        clock_inner.grid_columnconfigure(0, weight=1)

        self.clock_date_label = ctk.CTkLabel(
            clock_inner,
            text="Tue 01/01/2026",
            font=("Segoe UI", 10, "bold"),
            text_color=TEXT_SUB,
        )
        self.clock_date_label.grid(row=0, column=0, sticky="s", pady=(2, 0))

        self.clock_time_label = ctk.CTkLabel(
            clock_inner,
            text="01:10 PM",
            font=("Segoe UI", 14, "bold"),
            text_color=BTN_ACTIVE,
        )
        self.clock_time_label.grid(row=1, column=0, sticky="n", pady=(0, 2))

        # ===== USER INFO =====
        self.right_info_box = ctk.CTkFrame(
            self.right_cluster,
            fg_color="transparent",
            width=150,
            height=68,
        )
        self.right_info_box.pack(side="left", padx=(0, 6), pady=(2, 2))
        self.right_info_box.grid_propagate(False)
        self.right_info_box.grid_rowconfigure(0, weight=1)
        self.right_info_box.grid_rowconfigure(1, weight=1)
        self.right_info_box.grid_rowconfigure(2, weight=1)
        self.right_info_box.grid_columnconfigure(0, weight=1)

        self.app_name_label = ctk.CTkLabel(
            self.right_info_box,
            text="Delta Assistant",
            font=("Segoe UI", 15, "bold"),
            text_color=TEXT_MAIN,
        )
        self.app_name_label.grid(row=0, column=0, sticky="", pady=(0, 0))

        self.version_label = ctk.CTkLabel(
            self.right_info_box,
            text="Version: 0.0.1",
            font=("Segoe UI", 10),
            text_color=TEXT_SUB,
        )
        self.version_label.grid(row=1, column=0, sticky="", pady=(0, 0))

        self.welcome_label = ctk.CTkLabel(
            self.right_info_box,
            text=f"User: {self.user.get('username', 'Unknown')} ({self.get_display_role()})",
            font=("Segoe UI", 9, "bold"),
            text_color=TEXT_SUB,
        )
        self.welcome_label.grid(row=2, column=0, sticky="", pady=(0, 0))


        # ===== SETTINGS =====
        self.settings_container = ctk.CTkFrame(
            self.right_cluster,
            fg_color="transparent",
            width=76,
            height=70,
        )
        self.settings_container.pack(side="left", padx=(0, 6), pady=(2, 2))
        self.settings_container.grid_propagate(False)

        self.settings_circle = ctk.CTkFrame(
            self.settings_container,
            width=44,
            height=44,
            corner_radius=22,
            fg_color=BTN_IDLE,
            border_width=1,
            border_color=TOPBAR_BORDER,
        )
        self.settings_circle.pack(pady=(0, 3))
        self.settings_circle.pack_propagate(False)

        if self.settings_icon is not None:
            settings_icon_label = ctk.CTkLabel(
                self.settings_circle,
                text="",
                image=self.settings_icon,
            )
        else:
            settings_icon_label = ctk.CTkLabel(
                self.settings_circle,
                text="⚙",
                font=("Segoe UI", 16, "bold"),
                text_color=TEXT_MAIN,
            )
        settings_icon_label.place(relx=0.5, rely=0.5, anchor="center")

        self.settings_label = ctk.CTkLabel(
            self.settings_container,
            text="SETTING",
            font=("Segoe UI", 9),
            text_color=TEXT_SUB,
        )
        self.settings_label.pack()

        def _open_settings(event=None):
            self.show_settings_page()
        self._bind_topbar_action(
            self.settings_container,
            self.settings_circle,
            settings_icon_label,
            self.settings_label,
            _open_settings,
            BTN_IDLE,
            BTN_IDLE_HOVER,
        )

        # ===== LOCK =====
        self.lock_container = ctk.CTkFrame(
            self.right_cluster,
            fg_color="transparent",
            width=76,
            height=70,
        )
        self.lock_container.pack(side="left", padx=(0, 6), pady=(2, 2))
        self.lock_container.grid_propagate(False)

        self.lock_circle = ctk.CTkFrame(
            self.lock_container,
            width=44,
            height=44,
            corner_radius=22,
            fg_color=BTN_IDLE,
            border_width=1,
            border_color=TOPBAR_BORDER,
        )
        self.lock_circle.pack(pady=(0, 3))
        self.lock_circle.pack_propagate(False)

        if self.lock_icon is not None:
            lock_icon_label = ctk.CTkLabel(
                self.lock_circle,
                text="",
                image=self.lock_icon,
            )
        else:
            lock_icon_label = ctk.CTkLabel(
                self.lock_circle,
                text="L",
                font=("Segoe UI", 16, "bold"),
                text_color=TEXT_MAIN,
            )
        lock_icon_label.place(relx=0.5, rely=0.5, anchor="center")

        self.lock_label = ctk.CTkLabel(
            self.lock_container,
            text="LOCK",
            font=("Segoe UI", 9),
            text_color=TEXT_SUB,
        )
        self.lock_label.pack()

        def _lock_screen(event=None):
            self.lock_screen()

        self._bind_topbar_action(
            self.lock_container,
            self.lock_circle,
            lock_icon_label,
            self.lock_label,
            _lock_screen,
            BTN_IDLE,
            BTN_IDLE_HOVER,
        )

        # ===== LOGOUT =====
        self.logout_container = ctk.CTkFrame(
            self.right_cluster,
            fg_color="transparent",
            width=76,
            height=70,
        )
        self.logout_container.pack(side="left", padx=(0, 0), pady=(2, 2))
        self.logout_container.grid_propagate(False)

        self.logout_circle = ctk.CTkFrame(
            self.logout_container,
            width=44,
            height=44,
            corner_radius=22,
            fg_color=BTN_DANGER,
            border_width=1,
            border_color=TOPBAR_BORDER,
        )
        self.logout_circle.pack(pady=(0, 3))
        self.logout_circle.pack_propagate(False)

        if self.logout_icon is not None:
            logout_icon_label = ctk.CTkLabel(
                self.logout_circle,
                text="",
                image=self.logout_icon,
            )
        else:
            logout_icon_label = ctk.CTkLabel(
                self.logout_circle,
                text="⎋",
                font=("Segoe UI", 16, "bold"),
                text_color=TEXT_MAIN,
            )
        logout_icon_label.place(relx=0.5, rely=0.5, anchor="center")

        self.logout_label = ctk.CTkLabel(
            self.logout_container,
            text="LOG OUT",
            font=("Segoe UI", 9),
            text_color=TEXT_SUB,
        )
        self.logout_label.pack()

        def _do_logout(event=None):
            if messagebox.askyesno("Confirm", "Do you want to log out?"):
                self.on_logout()
        self._bind_topbar_action(
            self.logout_container,
            self.logout_circle,
            logout_icon_label,
            self.logout_label,
            _do_logout,
            BTN_DANGER,
            BTN_DANGER_HOVER,
        )

        # ===== OVERLAY MENU =====
        self.overlay_menu_frame = ctk.CTkFrame(
            self,
            fg_color="#201915",
            corner_radius=18,
            border_width=2,
            border_color="#a47b4d",
            width=232,
            height=232,
        )

        overlay_menu_inner = ctk.CTkFrame(
            self.overlay_menu_frame,
            fg_color="#2b231e",
            corner_radius=16,
            border_width=1,
            border_color="#5f4934",
        )
        overlay_menu_inner.pack(fill="both", expand=True, padx=8, pady=8)

        extra_items = [
            ("Function 1", self.placeholder_function),
            ("Function 2", self.placeholder_function),
            ("Function 3", self.placeholder_function),
            ("Function 4", self.placeholder_function),
        ]

        for i, (name, command) in enumerate(extra_items):
            btn = ctk.CTkButton(
                overlay_menu_inner,
                text=name,
                width=180,
                height=40,
                corner_radius=12,
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_MAIN,
                border_width=1,
                border_color=BTN_IDLE,
                font=("Segoe UI", 12, "bold"),
                command=command,
            )
            btn.pack(fill="x", padx=10, pady=(10 if i == 0 else 6, 0))

        self.overlay_menu_frame.place_forget()

    def build_body(self):
        self.body_frame = ctk.CTkFrame(self, fg_color=BG_APP, corner_radius=0)
        self.body_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        self.body_frame.grid_rowconfigure(0, weight=1)
        self.body_frame.grid_columnconfigure(0, weight=1)

        self.content_wrapper = ctk.CTkFrame(
            self.body_frame,
            fg_color=CONTENT_BG,
            corner_radius=22,
            border_width=2,
            border_color=CONTENT_BORDER,
        )
        self.content_wrapper.grid(row=0, column=0, sticky="nsew")
        self.content_wrapper.grid_rowconfigure(0, weight=1)
        self.content_wrapper.grid_columnconfigure(0, weight=1)

        self.content_frame = ctk.CTkFrame(
            self.content_wrapper,
            fg_color=CONTENT_BG,
            corner_radius=22,
        )
        self.content_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    # =========================================================
    # RESPONSIVE HEADER
    # =========================================================
    def on_topbar_resize(self, event=None):
        if self.reflow_after_id is not None:
            try:
                self.after_cancel(self.reflow_after_id)
            except Exception:
                pass

        self.reflow_after_id = self.after(120, self.reflow_header_layout)

    def apply_header_density_mode(self, compact: bool):
        if self.header_compact_mode == compact:
            return

        self.header_compact_mode = compact

        if self.header_frame is not None:
            self.header_frame.grid_configure(padx=16, pady=(10, 8) if compact else (16, 10))

        if self.body_frame is not None:
            self.body_frame.grid_configure(padx=16, pady=(0, 12) if compact else (0, 16))

    def reflow_header_layout(self):
        self.reflow_after_id = None

        if not self.winfo_exists():
            return

        try:
            total_width = self.topbar_main.winfo_width()
            if total_width <= 1:
                self.reflow_after_id = self.after(100, self.reflow_header_layout)
                return

            compact_mode = str(getattr(self.parent, "display_mode", "windowed")).strip().lower() != "maximized"
            self.apply_header_density_mode(compact_mode)

            nav_width = self.nav_frame.winfo_width()
            if nav_width <= 1:
                self.update_idletasks()
                nav_width = self.nav_frame.winfo_width()

            if nav_width <= 1:
                self.reflow_after_id = self.after(100, self.reflow_header_layout)
                return

            available_width = max(260, nav_width - 12)

            for widget in self.nav_frame.winfo_children():
                widget.grid_forget()

            row = 0
            col = 0

            for item_name, widget, item_width in self.nav_widgets:
                widget.grid(row=row, column=col, padx=(0, 8), pady=4, sticky="w")
                col += 1

            # Keep windowed mode aligned like maximized mode: one horizontal nav row.
            row_count = 1
            base_height = 84 if compact_mode else 102
            new_height = base_height

            current_height = self.topbar_main.cget("height")
            if current_height != new_height:
                self.topbar_main.configure(height=new_height)

        except Exception:
            pass

    # =========================================================
    # EXTRA MENU ANIMATION
    # =========================================================
    def toggle_expand_menu(self):
        if self.overlay_menu_frame is None:
            return

        if self.menu_open:
            self.menu_open = False
            self.overlay_menu_frame.place_forget()
            self.menu_toggle_btn.configure(
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_MAIN,
            )
        else:
            if self.work_schedule_dropdown is not None:
                self.work_schedule_dropdown.place_forget()
            self.work_schedule_dropdown_open = False
            if self.task_dropdown is not None:
                self.task_dropdown.place_forget()
            self.task_dropdown_open = False

            self.menu_open = True
            self.overlay_menu_frame.place(x=24, y=95)
            self.overlay_menu_frame.lift()
            self.menu_toggle_btn.configure(
                fg_color=BTN_ACTIVE,
                hover_color=BTN_ACTIVE_HOVER,
                text_color=TEXT_DARK,
            )

    def placeholder_function(self):
        messagebox.showinfo("Thông báo", "Chức năng này sẽ phát triển sau.")

    def toggle_work_schedule_dropdown(self):
        if self.work_schedule_dropdown is None or self.work_schedule_button is None:
            return

        if not self.can_open_work_schedule_menu():
            self.show_work_schedule_page()
            return

        if self.work_schedule_dropdown_open:
            self.work_schedule_dropdown_open = False
            self.work_schedule_dropdown.place_forget()
            return

        try:
            if self.overlay_menu_frame is not None:
                self.overlay_menu_frame.place_forget()
            self.menu_open = False
            if self.task_dropdown is not None:
                self.task_dropdown.place_forget()
            self.task_dropdown_open = False

            btn_x = self.work_schedule_button.winfo_x()
            btn_y = self.work_schedule_button.winfo_y()
            btn_h = self.work_schedule_button.winfo_height()

            self.work_schedule_dropdown.place(
                in_=self.nav_frame, x=btn_x - 2, y=btn_y + btn_h + 8
            )
            self.work_schedule_dropdown.lift()
            self.work_schedule_dropdown_open = True
        except Exception:
            pass

    def toggle_task_dropdown(self):
        if self.task_dropdown is None or self.task_button is None:
            return

        if self.task_dropdown_open:
            self.task_dropdown_open = False
            self.task_dropdown.place_forget()
            return

        try:
            if self.overlay_menu_frame is not None:
                self.overlay_menu_frame.place_forget()
            self.menu_open = False

            if self.work_schedule_dropdown is not None:
                self.work_schedule_dropdown.place_forget()
            self.work_schedule_dropdown_open = False

            btn_x = self.task_button.winfo_x()
            btn_y = self.task_button.winfo_y()
            btn_h = self.task_button.winfo_height()

            self.task_dropdown.place(
                in_=self.nav_frame, x=btn_x - 2, y=btn_y + btn_h + 8
            )
            self.task_dropdown.lift()
            self.task_dropdown_open = True
        except Exception:
            pass

    def hide_top_menus(self, preserve_notification=False):
        self.menu_open = False
        if self.overlay_menu_frame is not None:
            self.overlay_menu_frame.place_forget()

        self.work_schedule_dropdown_open = False
        if self.work_schedule_dropdown is not None:
            self.work_schedule_dropdown.place_forget()

        self.task_dropdown_open = False
        if self.task_dropdown is not None:
            self.task_dropdown.place_forget()

        if not preserve_notification:
            self.hide_notification_popup()

        if self.menu_toggle_btn is not None:
            self.menu_toggle_btn.configure(
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_MAIN,
            )

    def build_lock_screen_overlay(self):
        if self.lock_screen_overlay is not None and self.lock_screen_overlay.winfo_exists():
            return

        self.lock_screen_overlay = ctk.CTkFrame(
            self,
            fg_color="#130f0c",
            corner_radius=0,
        )

        center_card = ctk.CTkFrame(
            self.lock_screen_overlay,
            fg_color=BG_PANEL,
            corner_radius=24,
            border_width=1,
            border_color=TOPBAR_BORDER,
            width=420,
            height=420,
        )
        center_card.place(relx=0.5, rely=0.47, anchor="center")
        center_card.pack_propagate(False)

        inner_card = ctk.CTkFrame(
            center_card,
            fg_color=BG_PANEL_2,
            corner_radius=20,
            border_width=1,
            border_color="#5f4934",
        )
        inner_card.pack(fill="both", expand=True, padx=10, pady=10)

        if self.lock_icon is not None:
            lock_icon_label = ctk.CTkLabel(
                inner_card,
                text="",
                image=self.lock_icon,
            )
        else:
            lock_icon_label = ctk.CTkLabel(
                inner_card,
                text="LOCKED",
                font=("Segoe UI", 20, "bold"),
                text_color=BTN_ACTIVE,
            )
        lock_icon_label.pack(pady=(30, 10))

        ctk.CTkLabel(
            inner_card,
            text="App Locked",
            font=("Segoe UI", 28, "bold"),
            text_color=TEXT_MAIN,
        ).pack()

        ctk.CTkLabel(
            inner_card,
            text="Click unlock and enter your 4-digit PIN.",
            font=("Segoe UI", 13),
            text_color=TEXT_SUB,
        ).pack(pady=(8, 18))

        self.lock_screen_time_label = ctk.CTkLabel(
            inner_card,
            text="01:10 PM",
            font=("Segoe UI", 32, "bold"),
            text_color=BTN_ACTIVE,
        )
        self.lock_screen_time_label.pack()

        self.lock_screen_date_label = ctk.CTkLabel(
            inner_card,
            text="Tue 01/01/2026",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_SUB,
        )
        self.lock_screen_date_label.pack(pady=(4, 22))

        ctk.CTkLabel(
            inner_card,
            text=f"User: {self.user.get('username', 'Unknown')}",
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT_SUB,
        ).pack(pady=(0, 10))

        ctk.CTkButton(
            inner_card,
            text="Unlock",
            width=220,
            height=46,
            corner_radius=14,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 15, "bold"),
            command=self.open_unlock_dialog,
        ).pack(pady=(8, 12))


    def show_lock_screen_overlay(self):
        self.build_lock_screen_overlay()
        if self.lock_screen_overlay is None:
            return

        self.lock_screen_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lock_screen_overlay.lift()

    def hide_lock_screen_overlay(self):
        if self.lock_screen_overlay is not None and self.lock_screen_overlay.winfo_exists():
            self.lock_screen_overlay.place_forget()

    def finish_lock_screen_setup(self):
        self.hide_top_menus()
        self.is_screen_locked = True
        self.show_lock_screen_overlay()

    def lock_screen(self):
        if self.is_screen_locked:
            self.show_lock_screen_overlay()
            return

        username = self.user.get("username", "").strip()
        status_result = get_pin_status_api(username)

        if not status_result.get("success"):
            messagebox.showerror(
                "PIN Error",
                status_result.get("message", "Can not check PIN status."),
            )
            return

        if not status_result.get("has_pin", False):
            messagebox.showinfo(
                "Create PIN",
                "You need to create a 4-digit PIN before using lock screen.",
            )
            self.open_create_pin_flow(on_completed=self.finish_lock_screen_setup)
            return

        self.finish_lock_screen_setup()

    def unlock_screen(self):
        self.is_screen_locked = False
        self.hide_lock_screen_overlay()

    def open_unlock_dialog(self):
        username = self.user.get("username", "").strip()

        def after_enter_pin(pin_code):
            result = verify_pin_api(username, pin_code, username)

            if result.get("success"):
                unlock_dialog.destroy()
                self.unlock_screen()
            else:
                messagebox.showerror(
                    "PIN Error",
                    result.get("message", "PIN is incorrect."),
                )

        def open_forgot_pin_from_unlock():
            unlock_dialog.destroy()
            self.open_forgot_pin_flow(on_completed=self.unlock_screen)

        unlock_dialog = PinVerifyDialog(
            self,
            title="Unlock with 4-digit PIN",
            on_success=after_enter_pin,
            secondary_text="Forgot",
            on_secondary=open_forgot_pin_from_unlock,
        )

    def handle_work_schedule_menu_action(self, callback):
        self.work_schedule_dropdown_open = False
        if self.work_schedule_dropdown is not None:
            self.work_schedule_dropdown.place_forget()

        self.task_dropdown_open = False
        if self.task_dropdown is not None:
            self.task_dropdown.place_forget()

        self.update_idletasks()
        callback()

    def handle_task_menu_action(self, callback):
        self.task_dropdown_open = False
        if self.task_dropdown is not None:
            self.task_dropdown.place_forget()

        self.update_idletasks()
        callback()

    def show_welcome_page(self):
        self.hide_top_menus()
        self.current_page = "Welcome"
        self.update_function_visibility()

        for page_name, button in self.nav_buttons.items():
            button.configure(
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_MAIN,
                border_color=BTN_IDLE,
            )

        if self.work_schedule_button is not None:
            self.work_schedule_button.configure(
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_MAIN,
                border_color=BTN_IDLE,
            )

        if self.task_button is not None:
            self.task_button.configure(
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_MAIN,
                border_color=BTN_IDLE,
            )

        self.clear_content_frame()

        welcome_card = ctk.CTkFrame(
            self.content_frame,
            fg_color=CONTENT_INNER,
            corner_radius=18,
            border_width=1,
            border_color=CONTENT_BORDER,
        )
        welcome_card.pack(fill="both", expand=True, padx=18, pady=18)
        welcome_card.grid_rowconfigure(0, weight=1)
        welcome_card.grid_columnconfigure(0, weight=1)

        hero_box = ctk.CTkFrame(welcome_card, fg_color="transparent")
        hero_box.grid(row=0, column=0)

        if self.logo_image is not None:
            ctk.CTkLabel(
                hero_box,
                text="",
                image=self.logo_image,
            ).pack(pady=(10, 20))

        ctk.CTkLabel(
            hero_box,
            text="Welcome to Delta Support",
            font=("Segoe UI", 30, "bold"),
            text_color=TEXT_DARK,
        ).pack(pady=(0, 10))

        ctk.CTkLabel(
            hero_box,
            text="A product within the All In One Merchant ecosystem.",
            font=("Segoe UI", 15),
            text_color=TEXT_MUTED_DARK,
        ).pack(pady=(0, 24))

        if not self.functions_started and self.startup_gate_pending:
            ctk.CTkLabel(
                hero_box,
                text="Loading Tasks...",
                font=("Segoe UI", 14, "bold"),
                text_color=TEXT_MUTED_DARK,
            ).pack()
            ctk.CTkLabel(
                hero_box,
                text="Please wait a moment.",
                font=("Segoe UI", 13),
                text_color=TEXT_MUTED_DARK,
            ).pack(pady=(6, 0))
        elif not self.functions_started:
            ctk.CTkButton(
                hero_box,
                text="Start",
                width=180,
                height=46,
                corner_radius=14,
                fg_color=BTN_ACTIVE,
                hover_color=BTN_ACTIVE_HOVER,
                text_color=TEXT_DARK,
                font=("Segoe UI", 15, "bold"),
                command=self.start_function_experience,
            ).pack()
        else:
            ctk.CTkLabel(
                hero_box,
                text="Choose a function from the top menu to continue.",
                font=("Segoe UI", 14),
                text_color=TEXT_MUTED_DARK,
            ).pack()

    # =========================================================
    # PAGES
    # =========================================================
    def show_pos_page(self):
        if not self.can_access("POS"):
            self.show_access_denied("POS")
            return

        self.hide_top_menus()
        self.set_active_nav("POS")
        self.clear_content_frame()

        self.create_section_title(
            self.content_frame,
            "POS",
            "Tra cứu và quản lý dữ liệu POS.",
        )

        page_host = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        page_host.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        pos_page = POSPage(page_host)
        pos_page.pack(fill="both", expand=True)

    def show_sql_page(self):
        if not self.can_access("SQL"):
            self.show_access_denied("SQL")
            return

        self.hide_top_menus()
        self.set_active_nav("SQL")
        self.clear_content_frame()

        page_host = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        page_host.pack(fill="both", expand=True, padx=18, pady=(18, 18))

        try:
            sql_page = SQLPage(page_host, current_user=self.user)
            sql_page.pack(fill="both", expand=True)
        except Exception:
            self.create_fallback_text(
                page_host,
                "SQLPage hiện chưa sẵn sàng hoặc đang lỗi import.",
            )

    def show_link_data_page(self):
        if not self.can_access("Link / Data"):
            self.show_access_denied("Link / Data")
            return

        self.hide_top_menus()
        self.set_active_nav("Link / Data")
        self.clear_content_frame()

        self.create_section_title(
            self.content_frame,
            "Link / Data",
            "Tập hợp link, sheet và dữ liệu nội bộ.",
        )

        page_host = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        page_host.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        link_data_page = LinkDataPage(page_host)
        link_data_page.pack(fill="both", expand=True)

    def show_process_page(self, initial_section="report", initial_task_id=None):
        if not self.can_access("Task"):
            self.show_access_denied("Task")
            return

        self.hide_top_menus()
        self.set_active_nav("Task")
        self.clear_content_frame()

        self.create_section_title(
            self.content_frame,
            "Task",
            "Khu vực task sẽ được build trước.",
        )

        page_host = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        page_host.pack(fill="both", expand=True, padx=18, pady=(18, 18))

        try:
            process_page = ProcessPage(
                page_host,
                initial_section=initial_section,
                current_user=self.user,
                initial_task_id=initial_task_id,
            )
            process_page.pack(fill="both", expand=True)
        except Exception:
            self.create_fallback_text(
                page_host,
                "ProcessPage hiện chưa sẵn sàng hoặc đang lỗi import.",
            )

    def show_work_schedule_page(self):
        if not self.can_access("Work Schedule"):
            self.show_access_denied("Work Schedule")
            return

        self.hide_top_menus()
        self.set_active_nav("Work Schedule")
        self.clear_content_frame()

        page_host = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        page_host.pack(fill="both", expand=True, padx=18, pady=(18, 18))

        current_user = self.user.get("username", "")
        current_role = self.user.get("role", "")
        current_department = self.user.get("department", "")
        current_team = self.user.get("team", "General")

        tech_schedule_page = TechSchedulePage(
            page_host,
            current_user=current_user,
            current_role=current_role,
            current_department=current_department,
            current_team=current_team,
        )
        tech_schedule_page.pack(fill="both", expand=True)

    def show_leave_summary_page(self):
        if not self.can_access("Monthly Leave Summary"):
            self.show_access_denied("Monthly Leave Summary")
            return

        self.hide_top_menus()
        self.set_active_nav("Monthly Leave Summary")
        self.clear_content_frame()

        page_host = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        page_host.pack(fill="both", expand=True, padx=18, pady=(18, 18))

        summary_page = LeaveSummaryPage(
            page_host,
            current_user=self.user.get("username", ""),
            current_role=self.user.get("role", ""),
        )
        summary_page.pack(fill="both", expand=True)

    def show_leave_request_page(self):
        if not self.can_access("Create Leave Request"):
            self.show_access_denied("Create Leave Request")
            return

        self.hide_top_menus()
        self.set_active_nav("Create Leave Request")
        self.clear_content_frame()

        page_host = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        page_host.pack(fill="both", expand=True, padx=18, pady=(18, 18))

        request_page = LeaveRequestPage(
            page_host,
            current_user=self.user.get("username", ""),
            current_role=self.user.get("role", ""),
        )
        request_page.pack(fill="both", expand=True)

    def show_schedule_setup_page(self):
        if not self.can_access("Schedule Setup"):
            self.show_access_denied("Schedule Setup")
            return

        self.hide_top_menus()
        self.set_active_nav("Schedule Setup")
        self.clear_content_frame()

        page_host = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        page_host.pack(fill="both", expand=True, padx=18, pady=(18, 18))

        setup_page = ScheduleSetupPage(
            page_host,
            current_user=self.user.get("username", ""),
            current_role=self.user.get("role", ""),
            current_department=self.user.get("department", ""),
            current_team=self.user.get("team", "General"),
        )
        setup_page.pack(fill="both", expand=True)

    def show_settings_page(self):
        if not self.can_access("Settings"):
            self.show_access_denied("Settings")
            return

        self.hide_top_menus()
        self.current_page = "Settings"

        for page_name, button in self.nav_buttons.items():
            button.configure(
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_MAIN,
                border_color=BTN_IDLE,
            )

        if self.work_schedule_button is not None:
            self.work_schedule_button.configure(
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_MAIN,
                border_color=BTN_IDLE,
            )

        self.clear_content_frame()

        self.create_section_title(
            self.content_frame,
            "Settings",
            "Thông tin tài khoản và cài đặt cơ bản.",
        )

        scroll = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        user_card = ctk.CTkFrame(
            scroll,
            fg_color=CONTENT_INNER,
            corner_radius=18,
            border_width=1,
            border_color=CONTENT_BORDER,
        )
        user_card.pack(fill="x", pady=8)

        ctk.CTkLabel(
            user_card,
            text="Current User",
            font=("Segoe UI", 16, "bold"),
            text_color=TEXT_DARK,
        ).pack(anchor="w", padx=20, pady=(18, 8))

        ctk.CTkLabel(
            user_card,
            text=f"Username: {self.user.get('username', 'Unknown')}",
            font=("Segoe UI", 14),
            text_color=TEXT_MUTED_DARK,
        ).pack(anchor="w", padx=20, pady=3)

        ctk.CTkLabel(
            user_card,
            text=f"Role: {self.get_display_role()}",
            font=("Segoe UI", 14),
            text_color=TEXT_MUTED_DARK,
        ).pack(anchor="w", padx=20, pady=(3, 18))

        pass_card = ctk.CTkFrame(
            scroll,
            fg_color=CONTENT_INNER,
            corner_radius=18,
            border_width=1,
            border_color=CONTENT_BORDER,
        )
        pass_card.pack(fill="x", pady=8)

        ctk.CTkLabel(
            pass_card,
            text="Change Password",
            font=("Segoe UI", 16, "bold"),
            text_color=TEXT_DARK,
        ).pack(anchor="w", padx=20, pady=(18, 10))

        self.old_password_entry = ctk.CTkEntry(
            pass_card,
            width=360,
            height=42,
            placeholder_text="Current Password",
            placeholder_text_color=INPUT_PLACEHOLDER,
            show="*",
            fg_color=INPUT_BG,
            text_color=INPUT_TEXT,
            border_color=INPUT_BORDER,
            corner_radius=12,
        )
        self.old_password_entry.pack(anchor="w", padx=20, pady=6)

        self.new_password_entry = ctk.CTkEntry(
            pass_card,
            width=360,
            height=42,
            placeholder_text="New Password",
            placeholder_text_color=INPUT_PLACEHOLDER,
            show="*",
            fg_color=INPUT_BG,
            text_color=INPUT_TEXT,
            border_color=INPUT_BORDER,
            corner_radius=12,
        )
        self.new_password_entry.pack(anchor="w", padx=20, pady=6)

        self.confirm_new_password_entry = ctk.CTkEntry(
            pass_card,
            width=360,
            height=42,
            placeholder_text="Confirm New Password",
            placeholder_text_color=INPUT_PLACEHOLDER,
            show="*",
            fg_color=INPUT_BG,
            text_color=INPUT_TEXT,
            border_color=INPUT_BORDER,
            corner_radius=12,
        )
        self.confirm_new_password_entry.pack(anchor="w", padx=20, pady=6)

        ctk.CTkButton(
            pass_card,
            text="Update Password",
            width=180,
            height=42,
            corner_radius=12,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 14, "bold"),
            command=self.open_change_password_with_pin,
        ).pack(anchor="w", padx=20, pady=(14, 10))

        ctk.CTkButton(
            pass_card,
            text="Change PIN",
            width=180,
            height=42,
            corner_radius=12,
            fg_color=BTN_IDLE,
            hover_color=BTN_IDLE_HOVER,
            text_color=TEXT_MAIN,
            font=("Segoe UI", 14, "bold"),
            command=self.open_change_pin_flow,
        ).pack(anchor="w", padx=20, pady=(0, 18))

        if self.get_role_key() in ["admin", "management", "manager"]:
            admin_card = ctk.CTkFrame(
                scroll,
                fg_color=CONTENT_INNER,
                corner_radius=18,
                border_width=1,
                border_color=CONTENT_BORDER,
            )
            admin_card.pack(fill="x", pady=8)

            ctk.CTkLabel(
                admin_card,
                text="Admin Tools",
                font=("Segoe UI", 16, "bold"),
                text_color=TEXT_DARK,
            ).pack(anchor="w", padx=20, pady=(18, 10))

            ctk.CTkLabel(
                admin_card,
                text="Khu vực dành cho admin. Có thể mở rộng approve user và phân quyền.",
                font=("Segoe UI", 13),
                text_color=TEXT_MUTED_DARK,
                wraplength=800,
                justify="left",
            ).pack(anchor="w", padx=20, pady=(0, 10))

            ctk.CTkButton(
                admin_card,
                text="Admin Manager",
                width=190,
                height=42,
                corner_radius=12,
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_MAIN,
                font=("Segoe UI", 14, "bold"),
                command=self.open_admin_manager,
            ).pack(anchor="w", padx=20, pady=(0, 18))

    def open_admin_manager(self):
        if not self.can_access("Admin Approval"):
            self.show_access_denied("Admin Approval")
            return

        try:
            if (
                self.admin_manager_window is not None
                and self.admin_manager_window.winfo_exists()
            ):
                self.admin_manager_window.deiconify()
                self.admin_manager_window.lift()
                self.admin_manager_window.focus_force()
                self.admin_manager_window.attributes("-topmost", True)
                self.admin_manager_window.after(
                    300, lambda: self.admin_manager_window.attributes("-topmost", False)
                )
                return
        except Exception:
            self.admin_manager_window = None

        try:
            self.admin_manager_window = AdminApprovalPage(
                self,
                admin_name=self.user.get("username", "admin"),
                current_role=self.user.get("role", ""),
                current_department=self.user.get("department", ""),
                current_team=self.user.get("team", "General"),
            )
            self.admin_manager_window.lift()
            self.admin_manager_window.focus_force()
            self.admin_manager_window.attributes("-topmost", True)
            self.admin_manager_window.after(
                300, lambda: self.admin_manager_window.attributes("-topmost", False)
            )

        except Exception as e:
            messagebox.showerror(
                "Admin Manager Error",
                f"Không thể mở Admin Manager.\n\nChi tiết: {e}",
            )

    def show_admin_approval_page(self):
        self.open_admin_manager()

    # =========================================================
    # ACTIONS
    # =========================================================
    def handle_change_password(self):
        username = self.user.get("username", "")
        old_password = self.old_password_entry.get().strip()
        new_password = self.new_password_entry.get().strip()
        confirm_new_password = self.confirm_new_password_entry.get().strip()

        if not old_password or not new_password or not confirm_new_password:
            messagebox.showerror("Error", "Vui lòng nhập đầy đủ thông tin.")
            return

        if new_password != confirm_new_password:
            messagebox.showerror("Error", "Xác nhận mật khẩu mới không khớp.")
            return

        result = change_password_api(username, old_password, new_password)

        if result.get("success"):
            messagebox.showinfo(
                "Success",
                result.get("message", "Đổi mật khẩu thành công."),
            )
            self.old_password_entry.delete(0, "end")
            self.new_password_entry.delete(0, "end")
            self.confirm_new_password_entry.delete(0, "end")
        else:
            messagebox.showerror(
                "Error",
                result.get("message", "Đổi mật khẩu thất bại."),
            )

    def setup_click_outside(self):
        try:
            root = self.winfo_toplevel()
            root.bind("<Button-1>", self.handle_click_outside, add="+")
        except Exception:
            pass

    def handle_click_outside(self, event):
        try:
            if not self.winfo_exists():
                return

            widget = event.widget

            parent = widget
            while parent is not None:
                if parent == self.menu_toggle_btn:
                    return
                parent = parent.master

            parent = widget
            while parent is not None:
                if parent == self.overlay_menu_frame:
                    return
                parent = parent.master

            parent = widget
            while parent is not None:
                if parent == self.work_schedule_button:
                    return
                parent = parent.master

            parent = widget
            while parent is not None:
                if parent == self.work_schedule_dropdown:
                    return
                parent = parent.master

            parent = widget
            while parent is not None:
                if parent == self.task_button:
                    return
                parent = parent.master

            parent = widget
            while parent is not None:
                if parent == self.task_dropdown:
                    return
                parent = parent.master

            parent = widget
            while parent is not None:
                if parent == self.notification_container:
                    return
                parent = parent.master

            parent = widget
            while parent is not None:
                if parent == self.notification_popup:
                    return
                parent = parent.master

            self.hide_top_menus()

        except Exception:
            pass

        # đảm bảo luôn đóng dropdown
        self.work_schedule_dropdown_open = False
        if (
            self.work_schedule_dropdown is not None
            and self.work_schedule_dropdown.winfo_exists()
        ):
            self.work_schedule_dropdown.place_forget()

        self.task_dropdown_open = False
        if self.task_dropdown is not None and self.task_dropdown.winfo_exists():
            self.task_dropdown.place_forget()

        self.hide_notification_popup()

    def open_change_password_with_pin(self):
        username = self.user.get("username", "").strip()

        status_result = get_pin_status_api(username)

        if not status_result.get("success"):
            messagebox.showerror(
                "PIN Error",
                status_result.get("message", "Không kiểm tra được trạng thái PIN."),
            )
            return

        has_pin = status_result.get("has_pin", False)

        if not has_pin:
            self.open_create_pin_flow()
            return

        def after_enter_pin(pin_code):
            result = verify_pin_api(username, pin_code, username)

            if result.get("success"):
                pin_dialog.destroy()
                self.handle_change_password()
            else:
                messagebox.showerror(
                    "PIN Error",
                    result.get("message", "PIN không đúng."),
                )

        def open_forgot_pin_from_password():
            pin_dialog.destroy()
            self.open_forgot_pin_flow(on_completed=self.handle_change_password)

        pin_dialog = PinVerifyDialog(
            self,
            title="Enter 4-digit PIN",
            on_success=after_enter_pin,
            secondary_text="Forgot",
            on_secondary=open_forgot_pin_from_password,
        )

    def open_create_pin_flow(self, on_completed=None):
        username = self.user.get("username", "").strip()

        first_pin_holder = {"value": None}

        def after_first_pin(pin_code):
            first_dialog.destroy()
            first_pin_holder["value"] = pin_code

            def after_confirm_pin(confirm_code):
                confirm_dialog.destroy()

                if confirm_code != first_pin_holder["value"]:
                    messagebox.showerror(
                        "PIN Error",
                        "PIN confirmation does not match.",
                    )
                    return

                result = set_pin_api(username, confirm_code, username)

                if result.get("success"):
                    messagebox.showinfo("Success", "PIN created successfully.")
                    if on_completed is not None:
                        on_completed()
                    else:
                        self.handle_change_password()
                else:
                    messagebox.showerror(
                        "PIN Error",
                        result.get("message", "Can not create PIN"),
                    )

            confirm_dialog = PinVerifyDialog(
                self,
                title="Confirm 4-digit PIN",
                on_success=after_confirm_pin,
            )

        first_dialog = PinVerifyDialog(
            self,
            title="Create 4-digit PIN",
            on_success=after_first_pin,
        )

    def open_forgot_pin_flow(self, on_completed=None):
        username = self.user.get("username", "").strip()

        send_result = send_forgot_pin_otp_api(username)
        if not send_result.get("success"):
            messagebox.showerror(
                "OTP Error",
                send_result.get("message", "Unable to send OTP."),
            )
            return

        messagebox.showinfo(
            "OTP Sent",
            "OTP has been sent to your registered email address.",
        )

        reset_data = {"otp": "", "new_pin": ""}
        dialog_ref = {"dialog": None}

        def show_reset_error(message):
            messagebox.showerror("PIN Reset Error", message)

        def finish_reset(confirm_pin):
            if confirm_pin != reset_data["new_pin"]:
                show_reset_error("PIN confirmation does not match.")
                dialog_ref["dialog"].set_input_mode(
                    "Confirm new PIN",
                    4,
                    "Re-enter your new 4-digit PIN.",
                )
                dialog_ref["dialog"].on_success = finish_reset
                return

            result = reset_pin_with_otp_api(
                username,
                reset_data["otp"],
                confirm_pin,
                username,
            )

            if result.get("success"):
                dialog_ref["dialog"].destroy()
                messagebox.showinfo("Success", "PIN reset successfully.")
                if on_completed:
                    on_completed()
            else:
                show_reset_error(result.get("message", "Failed to reset PIN."))
                dialog_ref["dialog"].set_input_mode(
                    "Enter 6-digit OTP",
                    6,
                    "Enter the OTP sent to your registered email address.",
                )
                dialog_ref["dialog"].on_success = step_enter_otp

        def step_new_pin(new_pin):
            reset_data["new_pin"] = new_pin
            dialog_ref["dialog"].set_input_mode(
                "Confirm new PIN",
                4,
                "Re-enter your new 4-digit PIN.",
            )
            dialog_ref["dialog"].on_success = finish_reset

        def step_enter_otp(otp_code):
            reset_data["otp"] = otp_code
            dialog_ref["dialog"].set_input_mode(
                "Create new PIN",
                4,
                "Create your new 4-digit PIN.",
            )
            dialog_ref["dialog"].on_success = step_new_pin

        dialog_ref["dialog"] = PinVerifyDialog(
            self,
            title="Enter 6-digit OTP",
            on_success=step_enter_otp,
            digits=6,
            message_text="Enter the OTP sent to your registered email address.",
        )

    def open_change_pin_flow(self):
        username = self.user.get("username", "").strip()

        dialog_ref = {"dialog": None}
        pin_data = {"old_pin": "", "new_pin": ""}

        def show_error(msg):
            messagebox.showerror("PIN Error", msg)

        def step_confirm_new_pin(confirm_pin):
            if confirm_pin != pin_data["new_pin"]:
                show_error("PIN confirmation does not match.")
                dialog_ref["dialog"].pin_value = ""
                dialog_ref["dialog"].update_display()
                dialog_ref["dialog"].set_dialog_title("Confirm new PIN")
                return

            result_change = change_pin_api(
                username,
                pin_data["old_pin"],
                pin_data["new_pin"],
                username,
            )

            if result_change.get("success"):
                messagebox.showinfo("Success", "PIN changed successfully.")
                dialog_ref["dialog"].destroy()
            else:
                show_error(result_change.get("message", "Failed to change PIN."))
                dialog_ref["dialog"].pin_value = ""
                dialog_ref["dialog"].update_display()
                dialog_ref["dialog"].set_dialog_title("Enter current PIN")
                dialog_ref["dialog"].on_success = step_old_pin

        def step_new_pin(new_pin):
            pin_data["new_pin"] = new_pin
            dialog_ref["dialog"].pin_value = ""
            dialog_ref["dialog"].update_display()
            dialog_ref["dialog"].set_dialog_title("Confirm new PIN")
            dialog_ref["dialog"].on_success = step_confirm_new_pin

        def step_old_pin(old_pin):
            result = verify_pin_api(username, old_pin, username)

            if not result.get("success"):
                show_error(result.get("message", "Wrong current PIN."))
                dialog_ref["dialog"].pin_value = ""
                dialog_ref["dialog"].update_display()
                dialog_ref["dialog"].set_dialog_title("Enter current PIN")
                return

            pin_data["old_pin"] = old_pin
            dialog_ref["dialog"].pin_value = ""
            dialog_ref["dialog"].update_display()
            dialog_ref["dialog"].set_dialog_title("Enter new PIN")
            dialog_ref["dialog"].on_success = step_new_pin

        def open_forgot_pin_from_change():
            dialog_ref["dialog"].destroy()
            self.open_forgot_pin_flow()

        dialog_ref["dialog"] = PinVerifyDialog(
            self,
            title="Enter current PIN",
            on_success=step_old_pin,
            secondary_text="Forgot",
            on_secondary=open_forgot_pin_from_change,
        )
