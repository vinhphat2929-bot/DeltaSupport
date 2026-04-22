# pages/tech_schedule_page.py
# =========================================================
# DELTA ASSISTANT - WORK SCHEDULE PAGE (REDESIGNED)
# =========================================================

import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk
import requests
import threading
from datetime import datetime, timedelta
import math

from services.auth_service import get_tech_schedule_api
from services.app_config import API_BASE_URL

# ===== THEME =====
BG_PAGE       = "transparent"
BG_CARD       = "#fffaf3"
BG_CANVAS     = "#f5ede0"
BORDER        = "#c8a97a"
BORDER_SOFT   = "#dfc9a0"

TEXT_MAIN     = "#2a1d10"
TEXT_SUB      = "#8a6b4a"
TEXT_HEADER   = "#f7eedf"

HEADER_BG     = "#3a2a1c"
TOPBAR_BG     = "#fffaf3"

BTN_PRIMARY        = "#b87d3a"
BTN_PRIMARY_HOVER  = "#d49a50"
BTN_DARK           = "#3a2a1c"
BTN_DARK_HOVER     = "#4e3925"

# ===== SHIFT COLORS (đậm và rõ hơn) =====
SHIFT_COLORS = {
    "Shift 1": {"bg": "#e8f5e2", "border": "#7db86a", "title": "#2d6b1f", "header": "#3a5c2e"},
    "Shift 2": {"bg": "#fce8e8", "border": "#d97a7a", "title": "#8b2525", "header": "#6b3030"},
    "Shift 3": {"bg": "#e4eefa", "border": "#6a96d0", "title": "#1a3f7a", "header": "#2a4d7a"},
}
SHIFT_DEFAULT = {"bg": "#f0ece4", "border": "#b0956e", "title": "#4a3520", "header": "#4a3520"}

# ===== STATUS COLORS (màu đậm, dễ phân biệt) =====
STATUS_COLORS = {
    "WORK":  {"bg": "#d4edda", "text": "#155724", "border": "#7fba8a"},
    "OFF":   {"bg": "#fff3cd", "text": "#856404", "border": "#d4a940"},
    "A.L":  {"bg": "#c8e6c9", "text": "#1b5e20", "border": "#66bb6a"},
    "S.L":  {"bg": "#ffcdd2", "text": "#b71c1c", "border": "#ef9a9a"},
    "C.T.O": {"bg": "#bbdefb", "text": "#0d47a1", "border": "#64b5f6"},
    "U.L":  {"bg": "#e1bee7", "text": "#4a148c", "border": "#ba68c8"},
    "Other": {"bg": "#e0e0e0", "text": "#424242", "border": "#9e9e9e"},
}
STATUS_DEFAULT = {"bg": "#f5f5f5", "text": "#333333", "border": "#cccccc"}

STATUS_LIST = ["WORK", "OFF", "A.L", "S.L", "C.T.O", "U.L", "Other"]

DEPARTMENTS = [
    "Technical Support",
    "Sale Team",
    "Office",
    "Management",
    "Customer Service",
    "Marketing Team",
]


def darken_hex(hex_color, amount=0.15):
    hex_color = hex_color.lstrip("#")
    r = max(0, int(int(hex_color[0:2], 16) * (1 - amount)))
    g = max(0, int(int(hex_color[2:4], 16) * (1 - amount)))
    b = max(0, int(int(hex_color[4:6], 16) * (1 - amount)))
    return f"#{r:02x}{g:02x}{b:02x}"


def draw_rounded_rect(canvas, x1, y1, x2, y2, radius=8, fill="#ffffff", outline="#cccccc", width=1):
    """Vẽ hình chữ nhật có bo góc trên tk.Canvas."""
    r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
    points = [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]
    return canvas.create_polygon(
        points,
        smooth=True,
        fill=fill,
        outline=outline,
        width=width,
    )


def repair_vietnamese_text(text):
    value = str(text if text is not None else "").strip()
    if not value:
        return ""

    suspicious_tokens = ["Ã", "Ä", "áº", "á»", "â€", "Â"]
    if any(token in value for token in suspicious_tokens):
        for encoding in ("latin1", "cp1252"):
            try:
                fixed = value.encode(encoding).decode("utf-8")
                if fixed:
                    return fixed
            except Exception:
                continue
    return value


class TechSchedulePage(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        current_user=None,
        current_role=None,
        current_department=None,
        current_team=None,
    ):
        super().__init__(parent, fg_color=BG_PAGE)

        self.current_user = current_user or ""
        self.current_role = (current_role or "").strip().lower()
        self.current_department = current_department or ""
        self.current_team = current_team or "General"

        self.week_start = datetime.now().strftime("%Y-%m-%d")
        self.week_start = self._normalize_to_monday(self.week_start)

        self.selected_department = (
            self.current_department
            if self.current_department in DEPARTMENTS
            else "Technical Support"
        )
        self.selected_team = self.current_team if self.current_team else "General"

        self.schedule_data = []
        self.pending_changes = {}
        self.popup_menu = None
        self.cell_map = []
        self.employee_name_map = {}

        self.day_order = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

        # Layout dimensions - sẽ được tính lại khi resize
        self.col_employee = 150
        self.col_time     = 130
        self.col_day      = 90
        self.row_height   = 42
        self.header_height = 48
        self.shift_title_height = 36
        self.section_gap  = 20
        self.pad_x        = 20
        self.pad_y        = 20
        self.radius       = 10
        self.resize_render_after_id = None
        self.pending_resize_render_force = False
        self.last_rendered_col_widths = None
        self.page_active = True
        self.debug_background_jobs = False

        self._build_ui()

    def _debug_job(self, label, message):
        if not getattr(self, "debug_background_jobs", False):
            return
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [TechSchedulePage] {label} | {message}")

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

    # =========================================================
    # PERMISSION
    # =========================================================
    def can_edit_schedule(self, target_department, target_team):
        role = self.current_role
        cur_dept = str(self.current_department).strip().lower()
        cur_team = str(self.current_team).strip()
        tgt_dept = str(target_department).strip().lower()
        tgt_team = str(target_team).strip()

        if role in ["admin", "management", "hr", "accountant", "leader", "manager"]:
            return True
        if role in ["ts leader", "sale leader", "mt leader", "cs leader"]:
            if cur_dept != tgt_dept:
                return False
            if tgt_dept == "sale team":
                return cur_team == tgt_team
            return True
        return False

    def user_can_edit_anything(self):
        return self.current_role in [
            "admin", "management", "hr", "accountant",
            "leader", "manager", "ts leader", "sale leader",
            "mt leader", "cs leader",
        ]

    # =========================================================
    # HELPERS
    # =========================================================
    def _normalize_to_monday(self, date_str):
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")
        except Exception:
            return date_str

    def _get_week_headers(self):
        try:
            monday = datetime.strptime(self.week_start, "%Y-%m-%d")
            result = []
            for i, code in enumerate(self.day_order):
                day = monday + timedelta(days=i)
                result.append(f"{code}\n{day.strftime('%d/%m')}")
            return result
        except Exception:
            return self.day_order

    def _shift_week(self, days):
        try:
            cur = datetime.strptime(self.week_entry.get().strip(), "%Y-%m-%d")
            new = (cur + timedelta(days=days)).strftime("%Y-%m-%d")
            normalized = self._normalize_to_monday(new)
            self.week_entry.delete(0, "end")
            self.week_entry.insert(0, normalized)
            self._on_load_click()
        except Exception:
            messagebox.showerror("Error", "Ngày không hợp lệ.")

    def _go_today(self):
        normalized = self._normalize_to_monday(datetime.now().strftime("%Y-%m-%d"))
        self.week_entry.delete(0, "end")
        self.week_entry.insert(0, normalized)
        self._on_load_click()

    def _get_permission_text(self):
        role = self.current_role
        dept = str(self.current_department).strip()
        team = str(self.current_team).strip()
        if role in ["admin", "management", "hr", "accountant", "leader", "manager"]:
            return "✓  Quyền hiện tại: có thể chỉnh sửa toàn bộ schedule."
        if role in ["ts leader", "sale leader", "mt leader", "cs leader"]:
            if dept.lower() == "sale team":
                return f"✓  Quyền: chỉnh sửa schedule '{dept}' - Team '{team}'."
            return f"✓  Quyền: chỉnh sửa schedule của '{dept}'."
        return "○  Quyền hiện tại: chỉ xem schedule (không thể chỉnh sửa)."

    def _get_team_values(self, department):
        if department == "Sale Team":
            return ["Team 1", "Team 2", "Team 3"]
        return ["General"]

    def _refresh_employee_name_map(self):
        self.employee_name_map = {
            str(item.get("username", "")).strip().lower(): item
            for item in self.schedule_data
            if str(item.get("username", "")).strip()
        }

    def _get_display_name_for_item(self, item):
        username = str(item.get("username", "")).strip()
        profile = self.employee_name_map.get(username.lower(), {})

        candidates = [
            item.get("display_name", ""),
            profile.get("display_name", ""),
            item.get("full_name", ""),
            item.get("employee_name", ""),
            item.get("name", ""),
            username,
        ]

        for candidate in candidates:
            text = repair_vietnamese_text(candidate)
            if text:
                return text
        return username

    # =========================================================
    # BUILD UI
    # =========================================================
    def _build_ui(self):
        self.pack(fill="both", expand=True)

        # ── TOP CARD ──────────────────────────────────────────
        top_card = ctk.CTkFrame(
            self,
            fg_color=TOPBAR_BG,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
        )
        top_card.pack(fill="x", padx=8, pady=(0, 8))

        # Title row
        title_row = ctk.CTkFrame(top_card, fg_color="transparent")
        title_row.pack(fill="x", padx=18, pady=(14, 6))

        ctk.CTkLabel(
            title_row,
            text="Work Schedule",
            font=("Segoe UI", 22, "bold"),
            text_color=TEXT_MAIN,
        ).pack(side="left")

        # Badge permission
        self.perm_badge = ctk.CTkLabel(
            title_row,
            text=self._get_permission_text(),
            font=("Segoe UI", 11, "italic"),
            text_color=TEXT_SUB,
        )
        self.perm_badge.pack(side="left", padx=(16, 0))

        # Filter row
        filter_row = ctk.CTkFrame(top_card, fg_color="transparent")
        filter_row.pack(fill="x", padx=18, pady=(0, 12))

        def _lbl(parent, text):
            ctk.CTkLabel(
                parent,
                text=text,
                font=("Segoe UI", 12),
                text_color=TEXT_SUB,
            ).pack(side="left", padx=(0, 5))

        _lbl(filter_row, "Department")
        self.department_combo = ctk.CTkComboBox(
            filter_row,
            values=DEPARTMENTS,
            width=170,
            height=34,
            corner_radius=10,
            fg_color="#f0e8d8",
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            text_color=TEXT_MAIN,
            command=self._on_department_change,
        )
        self.department_combo.pack(side="left", padx=(0, 14))
        self.department_combo.set(self.selected_department)

        _lbl(filter_row, "Team")
        self.team_combo = ctk.CTkComboBox(
            filter_row,
            values=self._get_team_values(self.selected_department),
            width=110,
            height=34,
            corner_radius=10,
            fg_color="#f0e8d8",
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            text_color=TEXT_MAIN,
        )
        self.team_combo.pack(side="left", padx=(0, 14))
        self.team_combo.set(self.selected_team)

        _lbl(filter_row, "Tuần (YYYY-MM-DD)")
        self.week_entry = ctk.CTkEntry(
            filter_row,
            width=138,
            height=34,
            corner_radius=10,
            fg_color="#f0e8d8",
            border_color=BORDER,
            text_color=TEXT_MAIN,
        )
        self.week_entry.pack(side="left", padx=(0, 14))
        self.week_entry.insert(0, self.week_start)

        # Buttons
        btn_cfg = dict(height=34, corner_radius=10, font=("Segoe UI", 12, "bold"))

        ctk.CTkButton(
            filter_row, text="◀ Prev", width=80,
            fg_color=BTN_DARK, hover_color=BTN_DARK_HOVER, text_color=TEXT_HEADER,
            command=lambda: self._shift_week(-7), **btn_cfg
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            filter_row, text="Today", width=74,
            fg_color=BTN_DARK, hover_color=BTN_DARK_HOVER, text_color=TEXT_HEADER,
            command=self._go_today, **btn_cfg
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            filter_row, text="Next ▶", width=80,
            fg_color=BTN_DARK, hover_color=BTN_DARK_HOVER, text_color=TEXT_HEADER,
            command=lambda: self._shift_week(7), **btn_cfg
        ).pack(side="left", padx=(0, 14))

        ctk.CTkButton(
            filter_row, text="Load Schedule", width=130,
            fg_color=BTN_PRIMARY, hover_color=BTN_PRIMARY_HOVER, text_color="#ffffff",
            command=self._on_load_click, **btn_cfg
        ).pack(side="left")

        # ── CANVAS CARD ───────────────────────────────────────
        canvas_card = ctk.CTkFrame(
            self,
            fg_color=BG_CARD,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
        )
        canvas_card.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        canvas_card.grid_rowconfigure(0, weight=1)
        canvas_card.grid_columnconfigure(0, weight=1)

        self.tk_canvas = tk.Canvas(
            canvas_card,
            bg=BG_CANVAS,
            highlightthickness=0,
            bd=0,
        )
        self.tk_canvas.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=(10, 0))

        self.v_scroll = ctk.CTkScrollbar(
            canvas_card, orientation="vertical", command=self.tk_canvas.yview,
            fg_color="transparent", button_color=BORDER, button_hover_color=BTN_PRIMARY,
        )
        self.v_scroll.grid(row=0, column=1, sticky="ns", padx=(2, 6), pady=6)

        self.h_scroll = ctk.CTkScrollbar(
            canvas_card, orientation="horizontal", command=self.tk_canvas.xview,
            fg_color="transparent", button_color=BORDER, button_hover_color=BTN_PRIMARY,
        )
        self.h_scroll.grid(row=1, column=0, sticky="ew", padx=6, pady=(2, 6))

        self.tk_canvas.configure(
            yscrollcommand=self.v_scroll.set,
            xscrollcommand=self.h_scroll.set,
        )

        self.tk_canvas.bind("<Button-1>", self._on_canvas_click)
        self.tk_canvas.bind("<Configure>", self._on_canvas_resize)

        # Mouse wheel scroll
        self.tk_canvas.bind("<MouseWheel>", lambda e: self.tk_canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self.tk_canvas.bind("<Shift-MouseWheel>", lambda e: self.tk_canvas.xview_scroll(-1 * (e.delta // 120), "units"))

        # Empty state label
        self._show_empty_state()

        # Save button
        if self.user_can_edit_anything():
            self.save_button = ctk.CTkButton(
                self,
                text="💾  Save Changes",
                width=150,
                height=38,
                corner_radius=12,
                fg_color=BTN_PRIMARY,
                hover_color=BTN_PRIMARY_HOVER,
                text_color="#ffffff",
                font=("Segoe UI", 13, "bold"),
                command=self._save_all_changes,
            )
            self.save_button.place(relx=0.985, rely=0.985, anchor="se")
        else:
            self.save_button = None

    # =========================================================
    # EVENTS
    # =========================================================
    def _on_department_change(self, value):
        self.selected_department = value
        teams = self._get_team_values(value)
        self.team_combo.configure(values=teams)
        self.team_combo.set(teams[0])

    def _on_load_click(self):
        raw = self.week_entry.get().strip()
        if not raw:
            messagebox.showerror("Error", "Vui lòng nhập ngày bắt đầu tuần.")
            return
        normalized = self._normalize_to_monday(raw)
        self.week_start = normalized
        self.week_entry.delete(0, "end")
        self.week_entry.insert(0, normalized)

        self.selected_department = self.department_combo.get().strip()
        self.selected_team = self.team_combo.get().strip()
        self.pending_changes.clear()
        self._close_popup()
        self._load_schedule()

    def _on_canvas_resize(self, event=None):
        """Khi canvas resize, tính lại col widths để fit."""
        if not self.schedule_data:
            return
        self._schedule_resize_render()

    def _schedule_resize_render(self, force=False):
        if not self.schedule_data:
            return

        self.pending_resize_render_force = self.pending_resize_render_force or force
        if not self.page_active:
            self._debug_job("resize_render", "skip_schedule inactive")
            return
        self._schedule_after_slot(
            "resize_render_after_id",
            90,
            self._flush_resize_render,
            "resize_render",
            require_visible=True,
        )

    def _flush_resize_render(self):
        if not self._can_run_page_job("resize_render_flush", require_visible=True):
            self.pending_resize_render_force = False
            return
        if not self.schedule_data:
            self.pending_resize_render_force = False
            return

        force = self.pending_resize_render_force
        self.pending_resize_render_force = False

        self._recalc_col_widths()
        current_widths = (self.col_employee, self.col_time, self.col_day)
        if not force and current_widths == self.last_rendered_col_widths:
            return
        self._render_schedule()

    def _recalc_col_widths(self):
        """Tự động tính chiều rộng các cột để vừa canvas."""
        try:
            canvas_w = self.tk_canvas.winfo_width()
        except Exception:
            canvas_w = 1000

        # Tối thiểu
        min_employee = 130
        min_time = 110
        min_day = 75

        fixed = min_employee + min_time * 2 + min_day * 7 + self.pad_x * 2 + 20
        extra = max(0, canvas_w - fixed)

        self.col_employee = min_employee + int(extra * 0.25)
        self.col_time     = min_time     + int(extra * 0.10)
        self.col_day      = min_day      + int(extra * 0.065)

    # =========================================================
    # LOAD DATA
    # =========================================================
    def _load_schedule(self):
        result = get_tech_schedule_api(self.week_start)
        if not result.get("success"):
            messagebox.showerror("Schedule Error", result.get("message", "Unable to load the schedule."))
            return

        raw_data = result.get("data", [])
        filtered = []
        for item in raw_data:
            item_dept = str(item.get("department") or "").strip()
            item_team = str(item.get("team") or "General").strip() or "General"
            if not item_dept:
                continue
            if item_dept != self.selected_department:
                continue
            if self.selected_department == "Sale Team" and item_team != self.selected_team:
                continue
            filtered.append(item)

        self.schedule_data = filtered
        self._refresh_employee_name_map()
        self._recalc_col_widths()
        self._render_schedule()

    # =========================================================
    # SAVE
    # =========================================================
    def _update_status_api(self, username, work_date, new_status):
        payload = {
            "username": username,
            "work_date": work_date,
            "status_code": new_status,
            "action_by": self.current_user,
            "note": "",
        }
        try:
            resp = requests.post(f"{API_BASE_URL}/tech-schedule/update", json=payload, timeout=15)
            data = resp.json()
            if resp.status_code != 200 or not data.get("success"):
                return False, data.get("message", "Lỗi cập nhật.")
            return True, "OK"
        except Exception as e:
            return False, str(e)

    def _save_all_changes(self):
        if not self.pending_changes:
            messagebox.showinfo("Info", "Không có thay đổi nào để lưu.")
            return
        self._close_popup()
        if self.save_button:
            self.save_button.configure(state="disabled", text="Đang lưu...")
        threading.Thread(target=self._save_worker, daemon=True).start()

    def _save_worker(self):
        failed = []
        for item in list(self.pending_changes.values()):
            ok, msg = self._update_status_api(item["username"], item["work_date"], item["status_code"])
            if not ok:
                failed.append(f'{item["username"]} {item["work_date"]}: {msg}')
        self.after(0, lambda: self._finish_save(failed))

    def _finish_save(self, failed):
        if self.save_button:
            self.save_button.configure(state="normal", text="💾  Save Changes")
        if failed:
            messagebox.showerror("Lỗi lưu", "Một số thay đổi chưa lưu:\n\n" + "\n".join(failed[:10]))
            return
        self.pending_changes.clear()
        messagebox.showinfo("Thành công", "Đã lưu thay đổi lịch làm!")
        self._load_schedule()

    # =========================================================
    # POPUP
    # =========================================================
    def _close_popup(self):
        if self.popup_menu:
            try:
                self.popup_menu.destroy()
            except Exception:
                pass
            self.popup_menu = None

    def _show_status_popup(self, screen_x, screen_y, cell_info):
        self._close_popup()
        self.popup_menu = ctk.CTkToplevel(self)
        self.popup_menu.overrideredirect(True)
        self.popup_menu.attributes("-topmost", True)
        self.popup_menu.configure(fg_color="#2a1d10")
        self.popup_menu.geometry(f"+{screen_x}+{screen_y}")

        outer = ctk.CTkFrame(
            self.popup_menu,
            fg_color="#fdf6ec",
            corner_radius=14,
            border_width=1,
            border_color=BORDER,
        )
        outer.pack(padx=1, pady=1)

        ctk.CTkLabel(
            outer,
            text=f"  {cell_info.get('display_name', cell_info['username'])}  —  {cell_info['day_name']}",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w", padx=14, pady=(12, 6))

        btn_frame = ctk.CTkFrame(outer, fg_color="transparent")
        btn_frame.pack(padx=10, pady=(0, 8))

        for idx, status in enumerate(STATUS_LIST):
            sc = STATUS_COLORS.get(status, STATUS_DEFAULT)
            btn = ctk.CTkButton(
                btn_frame,
                text=status,
                width=88,
                height=32,
                corner_radius=8,
                fg_color=sc["bg"],
                hover_color=darken_hex(sc["bg"], 0.10),
                text_color=sc["text"],
                border_width=1,
                border_color=sc["border"],
                font=("Segoe UI", 11, "bold"),
                command=lambda s=status, info=cell_info: self._apply_status_change(info, s),
            )
            btn.grid(row=idx // 2, column=idx % 2, padx=4, pady=3)

        ctk.CTkButton(
            outer,
            text="✕  Đóng",
            width=180,
            height=30,
            corner_radius=8,
            fg_color="#e8ddd0",
            hover_color=darken_hex("#e8ddd0", 0.10),
            text_color=TEXT_MAIN,
            font=("Segoe UI", 11),
            command=self._close_popup,
        ).pack(padx=10, pady=(0, 12))

    def _apply_status_change(self, cell_info, new_status):
        key = (cell_info["username"], cell_info["work_date"])
        if new_status == cell_info["status"]:
            self.pending_changes.pop(key, None)
        else:
            self.pending_changes[key] = {
                "username": cell_info["username"],
                "work_date": cell_info["work_date"],
                "status_code": new_status,
            }
        self._close_popup()
        self._render_schedule()

    # =========================================================
    # CANVAS CLICK
    # =========================================================
    def _on_canvas_click(self, event):
        self._close_popup()
        cx = self.tk_canvas.canvasx(event.x)
        cy = self.tk_canvas.canvasy(event.y)
        for cell in self.cell_map:
            x1, y1, x2, y2 = cell["bbox"]
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                if not cell["can_edit"]:
                    return
                sx = self.tk_canvas.winfo_rootx() + event.x + 6
                sy = self.tk_canvas.winfo_rooty() + event.y + 6
                self._show_status_popup(sx, sy, cell)
                return

    # =========================================================
    # RENDER HELPERS
    # =========================================================
    def _show_empty_state(self):
        self.tk_canvas.delete("all")
        self.cell_map = []

        # Background
        self.tk_canvas.configure(bg=BG_CANVAS)

        # Placeholder text
        self.tk_canvas.create_text(
            30, 30,
            text="Bấm  'Load Schedule'  để tải lịch làm việc.",
            fill=TEXT_SUB,
            font=("Segoe UI", 14),
            anchor="nw",
        )
        self.tk_canvas.configure(scrollregion=(0, 0, 1000, 300))

    def _draw_rounded_rect(self, x1, y1, x2, y2, r=8, fill="#fff", outline="#ccc", width=1):
        return draw_rounded_rect(self.tk_canvas, x1, y1, x2, y2, radius=r, fill=fill, outline=outline, width=width)

    def _draw_text(self, x, y, text, fill=TEXT_MAIN, font=("Segoe UI", 11), anchor="center"):
        return self.tk_canvas.create_text(x, y, text=text, fill=fill, font=font, anchor=anchor)

    def _draw_cell(self, x, y, w, h, text, bg, border, text_color=None, bold=False, radius=8):
        """Vẽ ô có bo góc."""
        tc = text_color or TEXT_MAIN
        self._draw_rounded_rect(x + 2, y + 2, x + w - 2, y + h - 2,
                                 r=radius, fill=bg, outline=border, width=1)
        self._draw_text(
            x + w / 2, y + h / 2,
            text, fill=tc,
            font=("Segoe UI", 10, "bold" if bold else "normal"),
        )

    def _draw_header_cell(self, x, y, w, h, text, shift_header_color):
        self._draw_rounded_rect(x + 1, y + 1, x + w - 1, y + h - 1,
                                 r=7, fill=shift_header_color, outline=shift_header_color, width=0)
        self._draw_text(
            x + w / 2, y + h / 2,
            text, fill=TEXT_HEADER,
            font=("Segoe UI", 10, "bold"),
        )

    def _draw_shift_banner(self, y, total_w, shift_name, shift_colors, user_count):
        badge_x = self.pad_x + 8
        badge_y = y + 6
        badge_w = 118
        badge_h = self.shift_title_height - 12
        line_y = y + (self.shift_title_height / 2)
        line_start = badge_x + badge_w + 18
        line_end = total_w - 42

        # Accent line instead of a fully filled title bar.
        self.tk_canvas.create_line(
            line_start,
            line_y,
            line_end,
            line_y,
            fill=shift_colors["border"],
            width=2,
        )
        self.tk_canvas.create_line(
            line_start,
            line_y + 5,
            line_end - 90,
            line_y + 5,
            fill=BORDER_SOFT,
            width=1,
        )

        # Shift badge
        self._draw_rounded_rect(
            badge_x,
            badge_y,
            badge_x + badge_w,
            badge_y + badge_h,
            r=11,
            fill=shift_colors["header"],
            outline=shift_colors["header"],
            width=0,
        )
        self._draw_text(
            badge_x + (badge_w / 2),
            badge_y + badge_h / 2,
            shift_name,
            fill="#ffffff",
            font=("Segoe UI", 13, "bold"),
            anchor="center",
        )

        # Small count chip on the right to make the top row feel less empty.
        chip_text = f"{user_count} staff"
        chip_w = 74
        chip_h = 24
        chip_x2 = total_w - 26
        chip_x1 = chip_x2 - chip_w
        chip_y1 = y + (self.shift_title_height - chip_h) / 2
        chip_y2 = chip_y1 + chip_h

        self._draw_rounded_rect(
            chip_x1,
            chip_y1,
            chip_x2,
            chip_y2,
            r=9,
            fill=BG_CARD,
            outline=shift_colors["border"],
            width=1,
        )
        self._draw_text(
            (chip_x1 + chip_x2) / 2,
            (chip_y1 + chip_y2) / 2,
            chip_text,
            fill=shift_colors["title"],
            font=("Segoe UI", 9, "bold"),
        )

    # =========================================================
    # RENDER SCHEDULE
    # =========================================================
    def _render_schedule(self):
        self.tk_canvas.delete("all")
        self.cell_map = []

        if not self.schedule_data:
            self._show_empty_state()
            self.last_rendered_col_widths = None
            return

        # Group by shift
        grouped = {}
        for item in self.schedule_data:
            shift = item.get("shift_name", "Shift ?")
            user = item.get("username", "")
            display_name = self._get_display_name_for_item(item)
            grouped.setdefault(shift, {})
            grouped[shift].setdefault(user, {"display_name": display_name, "days": {}})
            grouped[shift][user]["days"][item.get("day_name", "")] = item

        # Column total width
        total_w = (
            self.pad_x
            + self.col_employee
            + self.col_time * 2
            + self.col_day * 7
            + 30
        )

        y = self.pad_y

        # ── TITLE ──────────────────────────────────────────
        title = f"Weekly Schedule  ·  {self.selected_department}"
        if self.selected_department == "Sale Team":
            title += f"  ·  {self.selected_team}"
        title += f"  ·  Tuần {self.week_start}"

        self._draw_text(
            self.pad_x, y, title,
            fill=TEXT_MAIN,
            font=("Segoe UI", 15, "bold"),
            anchor="nw",
        )
        y += 38

        headers = (
            ["Employee", "VN Time", "US Time"]
            + self._get_week_headers()
        )
        col_widths = (
            [self.col_employee, self.col_time, self.col_time]
            + [self.col_day] * 7
        )

        # ── SHIFTS ────────────────────────────────────────
        for shift_name, users in grouped.items():
            sc = SHIFT_COLORS.get(shift_name, SHIFT_DEFAULT)
            num_rows = len(users)

            block_h = (
                self.shift_title_height
                + self.header_height
                + num_rows * self.row_height
                + 16
            )

            # Shift outer box
            self._draw_rounded_rect(
                self.pad_x - 6, y,
                total_w - 14, y + block_h,
                r=14,
                fill=sc["bg"],
                outline=sc["border"],
                width=2,
            )

            self._draw_shift_banner(y, total_w, shift_name, sc, num_rows)
            y += self.shift_title_height

            # Header row
            x = self.pad_x
            for hdr, cw in zip(headers, col_widths):
                self._draw_header_cell(x, y, cw, self.header_height, hdr, sc["header"])
                x += cw
            y += self.header_height

            # Data rows
            for username, user_info in users.items():
                display_name = user_info.get("display_name", username)
                days = user_info.get("days", {})
                sample = next(iter(days.values()))
                vn_time = sample.get("vn_time_range", "")
                us_time = sample.get("us_time_range", "")
                tgt_dept = sample.get("department", self.selected_department)
                tgt_team = sample.get("team", self.selected_team)
                can_edit = self.can_edit_schedule(tgt_dept, tgt_team)

                x = self.pad_x

                # Fixed cols: Employee, VN Time, US Time
                for text, cw in [
                    (display_name, self.col_employee),
                    (vn_time, self.col_time),
                    (us_time, self.col_time),
                ]:
                    self._draw_cell(
                        x, y, cw, self.row_height,
                        text,
                        bg=BG_CARD,
                        border=BORDER_SOFT,
                        text_color=TEXT_MAIN,
                        bold=False,
                        radius=self.radius,
                    )
                    x += cw

                # Day cols
                for day_name in self.day_order:
                    item = days.get(day_name)
                    cw = self.col_day

                    if not item:
                        self._draw_cell(
                            x, y, cw, self.row_height,
                            "—", bg="#f0ece4",
                            border=BORDER_SOFT,
                            text_color="#c0a882",
                            radius=self.radius,
                        )
                        x += cw
                        continue

                    key = (username, item["work_date"])
                    status = (
                        self.pending_changes[key]["status_code"]
                        if key in self.pending_changes
                        else item["status_code"]
                    )
                    is_pending = key in self.pending_changes

                    sc_status = STATUS_COLORS.get(status, STATUS_DEFAULT)

                    # Đổ màu ô
                    self._draw_cell(
                        x, y, cw, self.row_height,
                        status,
                        bg=sc_status["bg"],
                        border=sc_status["border"],
                        text_color=sc_status["text"],
                        bold=True,
                        radius=self.radius,
                    )

                    # Chấm nhỏ báo pending change
                    if is_pending:
                        px = x + cw - 10
                        py = y + 8
                        self.tk_canvas.create_oval(px, py, px + 6, py + 6, fill="#e05a1a", outline="")

                    # Nếu có thể edit → thêm vào cell_map
                    if can_edit:
                        self.cell_map.append({
                            "bbox": (x, y, x + cw, y + self.row_height),
                            "username": username,
                            "display_name": display_name,
                            "work_date": item["work_date"],
                            "status": item["status_code"],
                            "day_name": day_name,
                            "target_department": tgt_dept,
                            "target_team": tgt_team,
                            "can_edit": True,
                        })

                    x += cw

                y += self.row_height

            y += self.section_gap + 10

        # Cập nhật scroll region
        self.tk_canvas.configure(scrollregion=(0, 0, max(total_w + 40, self.tk_canvas.winfo_width()), y + 30))
        self.last_rendered_col_widths = (self.col_employee, self.col_time, self.col_day)

    def on_page_resume(self):
        self.page_active = True
        self._debug_job("page_resume", "wake")
        self._close_popup()
        if self.schedule_data:
            self._schedule_resize_render(force=True)

    def on_page_hide(self):
        self.page_active = False
        self._debug_job("page_hide", "sleep")
        self._close_popup()
        self._cancel_after_slot("resize_render_after_id", "resize_render")
        self.pending_resize_render_force = False

    def destroy(self):
        self.on_page_hide()
        super().destroy()
