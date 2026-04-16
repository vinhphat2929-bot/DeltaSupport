import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk
import requests
import threading
from datetime import datetime, timedelta

from services.auth_service import get_tech_schedule_api

API_BASE_URL = "https://underline-steersman-crepe.ngrok-free.dev"

BG_CARD = "#fffaf3"
BORDER = "#6e5846"
TEXT_MAIN = "#2a221d"
TEXT_SUB = "#705d4f"
HEADER_BG = "#2f2721"
HEADER_TEXT = "#f5efe6"

SHIFT_COLORS = {
    "Shift 1": "#dfead8",
    "Shift 2": "#f4dddd",
    "Shift 3": "#dbe8f6",
}

STATUS_COLORS = {
    "WORK": "#ffffff",
    "OFF": "#f7e7a9",
    "A.L": "#b8e0b8",
    "S.L": "#f3c6c6",
    "C.T.O": "#cddcf6",
    "U.L": "#e8d4f0",
    "Other": "#e7e7e7",
}

STATUS_LIST = ["WORK", "OFF", "A.L", "S.L", "C.T.O", "U.L", "Other"]

DEPARTMENTS = [
    "Technical Support",
    "Sale Team",
    "Office",
    "Management",
    "Customer Service",
    "Marketing Team",
]


def darken_hex(hex_color, amount=0.18):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    r = max(0, int(r * (1 - amount)))
    g = max(0, int(g * (1 - amount)))
    b = max(0, int(b * (1 - amount)))

    return f"#{r:02x}{g:02x}{b:02x}"


class TechSchedulePage(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        current_user=None,
        current_role=None,
        current_department=None,
        current_team=None,
    ):
        super().__init__(parent, fg_color="transparent")

        self.current_user = current_user or ""
        self.current_role = (current_role or "").strip().lower()
        self.current_department = current_department or ""
        self.current_team = current_team or "General"

        self.week_start = "2026-04-13"
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

        self.day_order = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

        self.col_widths = {
            "employee": 170,
            "vn": 140,
            "us": 140,
            "day": 95,
        }
        self.row_height = 38
        self.header_height = 52
        self.shift_title_height = 34
        self.section_gap = 18
        self.left_pad = 18
        self.top_pad = 18

        self.build_ui()

    # =========================================================
    # PERMISSION
    # =========================================================
    def can_edit_schedule(self, target_department, target_team):
        role = self.current_role
        current_department = str(self.current_department).strip().lower()
        current_team = str(self.current_team).strip()

        target_department = str(target_department).strip().lower()
        target_team = str(target_team).strip()

        if role in ["admin", "management", "hr", "accountant", "leader", "manager"]:
            return True

        if role in ["ts leader", "sale leader", "mt leader", "cs leader"]:
            if current_department != target_department:
                return False
            if target_department == "sale team":
                return current_team == target_team
            return True

        return False

    def user_can_edit_anything(self):
        return self.current_role in [
            "admin",
            "management",
            "hr",
            "accountant",
            "leader",
            "manager",
            "ts leader",
            "sale leader",
            "mt leader",
            "cs leader",
        ]

    # =========================================================
    # HELPERS
    # =========================================================
    def normalize_to_monday(self, date_str):
        try:
            input_date = datetime.strptime(date_str, "%Y-%m-%d")
            monday = input_date - timedelta(days=input_date.weekday())
            return monday.strftime("%Y-%m-%d")
        except Exception:
            return date_str

    def get_week_headers(self):
        try:
            monday = datetime.strptime(self.week_start, "%Y-%m-%d")
            headers = []
            for i, day_code in enumerate(self.day_order):
                current_day = monday + timedelta(days=i)
                headers.append(f"{day_code}\n{current_day.strftime('%d/%m')}")
            return headers
        except Exception:
            return self.day_order

    def shift_week(self, days):
        try:
            current = datetime.strptime(self.week_entry.get().strip(), "%Y-%m-%d")
            new_date = current + timedelta(days=days)
            normalized = self.normalize_to_monday(new_date.strftime("%Y-%m-%d"))

            self.week_entry.delete(0, "end")
            self.week_entry.insert(0, normalized)

            self.on_load_schedule_click()
        except Exception:
            messagebox.showerror("Error", "Ngày tuần không hợp lệ.")

    def go_to_today_week(self):
        today_str = datetime.now().strftime("%Y-%m-%d")
        normalized = self.normalize_to_monday(today_str)

        self.week_entry.delete(0, "end")
        self.week_entry.insert(0, normalized)

        self.on_load_schedule_click()

    # =========================================================
    # UI
    # =========================================================
    def build_ui(self):
        self.pack(fill="both", expand=True)

        top_card = ctk.CTkFrame(
            self,
            fg_color=BG_CARD,
            corner_radius=16,
            border_width=1,
            border_color=BORDER,
        )
        top_card.pack(fill="x", padx=8, pady=(0, 10))

        ctk.CTkLabel(
            top_card,
            text="Work Schedule",
            font=("Segoe UI", 20, "bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w", padx=18, pady=(14, 6))

        filter_row = ctk.CTkFrame(top_card, fg_color="transparent")
        filter_row.pack(fill="x", padx=18, pady=(0, 6))

        left_filters = ctk.CTkFrame(filter_row, fg_color="transparent")
        left_filters.pack(side="left", anchor="w")

        right_actions = ctk.CTkFrame(filter_row, fg_color="transparent")
        right_actions.pack(side="right", anchor="e")

        ctk.CTkLabel(
            left_filters,
            text="Department",
            font=("Segoe UI", 12),
            text_color=TEXT_SUB,
        ).pack(side="left", padx=(0, 6))

        self.department_combo = ctk.CTkComboBox(
            left_filters,
            values=DEPARTMENTS,
            width=160,
            height=34,
            corner_radius=10,
            command=self.on_department_change,
        )
        self.department_combo.pack(side="left", padx=(0, 12))
        self.department_combo.set(self.selected_department)

        ctk.CTkLabel(
            left_filters,
            text="Team",
            font=("Segoe UI", 12),
            text_color=TEXT_SUB,
        ).pack(side="left", padx=(0, 6))

        self.team_combo = ctk.CTkComboBox(
            left_filters,
            values=self.get_team_values(self.selected_department),
            width=110,
            height=34,
            corner_radius=10,
        )
        self.team_combo.pack(side="left", padx=(0, 12))
        self.team_combo.set(self.selected_team)

        ctk.CTkLabel(
            left_filters,
            text="Week Start (YYYY-MM-DD)",
            font=("Segoe UI", 12),
            text_color=TEXT_SUB,
        ).pack(side="left", padx=(0, 6))

        self.week_entry = ctk.CTkEntry(
            left_filters,
            width=140,
            height=34,
            corner_radius=10,
        )
        self.week_entry.pack(side="left", padx=(0, 12))
        self.week_entry.insert(0, self.week_start)

        ctk.CTkButton(
            right_actions,
            text="Prev Week",
            width=90,
            height=34,
            corner_radius=10,
            command=lambda: self.shift_week(-7),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            right_actions,
            text="Today",
            width=80,
            height=34,
            corner_radius=10,
            command=self.go_to_today_week,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            right_actions,
            text="Next Week",
            width=90,
            height=34,
            corner_radius=10,
            command=lambda: self.shift_week(7),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            right_actions,
            text="Load Schedule",
            width=120,
            height=34,
            corner_radius=10,
            command=self.on_load_schedule_click,
        ).pack(side="left")

        self.permission_label = ctk.CTkLabel(
            top_card,
            text=self.get_permission_text(),
            font=("Segoe UI", 12, "italic"),
            text_color=TEXT_SUB,
        )
        self.permission_label.pack(anchor="w", padx=18, pady=(4, 12))

        canvas_card = ctk.CTkFrame(
            self,
            fg_color=BG_CARD,
            corner_radius=16,
            border_width=1,
            border_color=BORDER,
        )
        canvas_card.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        self.tk_canvas = tk.Canvas(
            canvas_card,
            bg=BG_CARD,
            highlightthickness=0,
            bd=0,
        )
        self.tk_canvas.grid(row=0, column=0, sticky="nsew")

        self.v_scroll = ctk.CTkScrollbar(
            canvas_card,
            orientation="vertical",
            command=self.tk_canvas.yview,
        )
        self.v_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=6)

        self.h_scroll = ctk.CTkScrollbar(
            canvas_card,
            orientation="horizontal",
            command=self.tk_canvas.xview,
        )
        self.h_scroll.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))

        canvas_card.grid_rowconfigure(0, weight=1)
        canvas_card.grid_columnconfigure(0, weight=1)

        self.tk_canvas.configure(
            yscrollcommand=self.v_scroll.set,
            xscrollcommand=self.h_scroll.set,
        )

        self.tk_canvas.bind("<Button-1>", self.on_canvas_click)

        self.empty_label = ctk.CTkLabel(
            self.tk_canvas,
            text="Bấm 'Load Schedule' để tải lịch làm.",
            font=("Segoe UI", 14),
            text_color=TEXT_SUB,
        )
        self.empty_window = self.tk_canvas.create_window(
            20, 20, anchor="nw", window=self.empty_label
        )

        if self.user_can_edit_anything():
            self.save_button = ctk.CTkButton(
                self,
                text="Save Changes",
                width=140,
                height=36,
                corner_radius=10,
                command=self.save_all_changes,
            )
            self.save_button.place(relx=0.985, rely=0.985, anchor="se")
        else:
            self.save_button = None

    def get_team_values(self, department):
        if department == "Sale Team":
            return ["Team 1", "Team 2", "Team 3"]
        return ["General"]

    def on_department_change(self, selected_department):
        self.selected_department = selected_department
        team_values = self.get_team_values(selected_department)
        self.team_combo.configure(values=team_values)
        self.team_combo.set(team_values[0])

    def get_permission_text(self):
        role = self.current_role
        current_department = str(self.current_department).strip()
        current_team = str(self.current_team).strip()

        if role in ["admin", "management", "hr", "accountant", "leader", "manager"]:
            return "Quyền hiện tại: có thể chỉnh sửa schedule."

        if role in ["ts leader", "sale leader", "mt leader", "cs leader"]:
            if current_department.lower() == "sale team":
                return f"Quyền hiện tại: chỉ sửa được schedule của Department '{current_department}' - Team '{current_team}'."
            return f"Quyền hiện tại: chỉ sửa được schedule của Department '{current_department}'."

        return "Quyền hiện tại: chỉ xem schedule."

    # =========================================================
    # LOAD
    # =========================================================
    def on_load_schedule_click(self):
        week_start = self.week_entry.get().strip()
        if not week_start:
            messagebox.showerror("Error", "Please enter week start date.")
            return

        normalized_week_start = self.normalize_to_monday(week_start)
        self.week_start = normalized_week_start

        self.week_entry.delete(0, "end")
        self.week_entry.insert(0, normalized_week_start)

        self.selected_department = self.department_combo.get().strip()
        self.selected_team = self.team_combo.get().strip()
        self.pending_changes.clear()
        self.close_popup_menu()
        self.load_schedule()

    def load_schedule(self):
        result = get_tech_schedule_api(self.week_start)

        if not result.get("success"):
            messagebox.showerror(
                "Schedule Error",
                result.get("message", "Cannot load Work Schedule."),
            )
            return

        raw_data = result.get("data", [])

        filtered = []
        for item in raw_data:
            item_department = str(
                item.get("department", self.selected_department)
            ).strip()
            item_team = str(item.get("team", "General") or "General").strip()

            if item_department != self.selected_department:
                continue

            if (
                self.selected_department == "Sale Team"
                and item_team != self.selected_team
            ):
                continue

            filtered.append(item)

        self.schedule_data = filtered
        self.render_schedule()

    # =========================================================
    # SAVE
    # =========================================================
    def update_schedule_status(self, username, work_date, new_status):
        payload = {
            "username": username,
            "work_date": work_date,
            "status_code": new_status,
            "action_by": self.current_user,
            "note": "",
        }

        try:
            response = requests.post(
                f"{API_BASE_URL}/tech-schedule/update",
                json=payload,
                timeout=15,
            )

            try:
                data = response.json()
            except Exception:
                data = {"success": False, "message": response.text}

            if response.status_code != 200 or not data.get("success"):
                return False, data.get("message", "Cập nhật schedule thất bại.")

            return True, "OK"

        except Exception as e:
            return False, str(e)

    def save_all_changes(self):
        if not self.pending_changes:
            messagebox.showinfo("Info", "Không có thay đổi nào để lưu.")
            return

        self.close_popup_menu()

        if self.save_button is not None:
            self.save_button.configure(state="disabled", text="Saving...")

        threading.Thread(target=self._save_all_changes_worker, daemon=True).start()

    def _save_all_changes_worker(self):
        failed = []

        pending_items = list(self.pending_changes.values())

        for item in pending_items:
            ok, msg = self.update_schedule_status(
                item["username"],
                item["work_date"],
                item["status_code"],
            )
            if not ok:
                failed.append(f'{item["username"]} - {item["work_date"]}: {msg}')

        self.after(0, lambda: self._finish_save_all_changes(failed))

    def _finish_save_all_changes(self, failed):
        if self.save_button is not None:
            self.save_button.configure(state="normal", text="Save Changes")

        if failed:
            messagebox.showerror(
                "Update Error",
                "Một số thay đổi chưa lưu được:\n\n" + "\n".join(failed[:10]),
            )
            return

        self.pending_changes.clear()
        messagebox.showinfo("Success", "Đã lưu thay đổi lịch làm.")
        self.load_schedule()

    # =========================================================
    # POPUP MENU
    # =========================================================
    def close_popup_menu(self):
        if self.popup_menu is not None:
            try:
                self.popup_menu.destroy()
            except Exception:
                pass
            self.popup_menu = None

    def show_status_popup(self, screen_x, screen_y, cell_info):
        self.close_popup_menu()

        self.popup_menu = ctk.CTkToplevel(self)
        self.popup_menu.overrideredirect(True)
        self.popup_menu.attributes("-topmost", True)
        self.popup_menu.configure(fg_color=BG_CARD)
        self.popup_menu.geometry(f"+{screen_x}+{screen_y}")

        outer = ctk.CTkFrame(
            self.popup_menu,
            fg_color=BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=BORDER,
        )
        outer.pack(padx=1, pady=1)

        ctk.CTkLabel(
            outer,
            text=f'{cell_info["username"]} - {cell_info["day_name"]}',
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w", padx=12, pady=(10, 6))

        btn_wrap = ctk.CTkFrame(outer, fg_color="transparent")
        btn_wrap.pack(padx=10, pady=(0, 10))

        for idx, status in enumerate(STATUS_LIST):
            btn = ctk.CTkButton(
                btn_wrap,
                text=status,
                width=82,
                height=30,
                corner_radius=8,
                fg_color=STATUS_COLORS.get(status, "#ffffff"),
                hover_color=darken_hex(STATUS_COLORS.get(status, "#ffffff"), 0.08),
                text_color=TEXT_MAIN,
                border_width=1,
                border_color=darken_hex(STATUS_COLORS.get(status, "#ffffff"), 0.22),
                command=lambda s=status, info=cell_info: self.apply_status_change(
                    info, s
                ),
            )
            btn.grid(row=idx // 2, column=idx % 2, padx=4, pady=4)

        close_btn = ctk.CTkButton(
            outer,
            text="Close",
            width=170,
            height=30,
            corner_radius=8,
            fg_color="#d7cfc3",
            hover_color="#c7beb1",
            text_color=TEXT_MAIN,
            command=self.close_popup_menu,
        )
        close_btn.pack(padx=10, pady=(0, 10))

    def apply_status_change(self, cell_info, new_status):
        key = (cell_info["username"], cell_info["work_date"])
        original_status = cell_info["status"]

        if new_status == original_status:
            self.pending_changes.pop(key, None)
        else:
            self.pending_changes[key] = {
                "username": cell_info["username"],
                "work_date": cell_info["work_date"],
                "status_code": new_status,
            }

        self.close_popup_menu()
        self.render_schedule()

    # =========================================================
    # CANVAS CLICK
    # =========================================================
    def on_canvas_click(self, event):
        self.close_popup_menu()

        canvas_x = self.tk_canvas.canvasx(event.x)
        canvas_y = self.tk_canvas.canvasy(event.y)

        for cell in self.cell_map:
            x1, y1, x2, y2 = cell["bbox"]
            if x1 <= canvas_x <= x2 and y1 <= canvas_y <= y2:
                if not cell["can_edit"]:
                    return

                screen_x = self.tk_canvas.winfo_rootx() + event.x + 6
                screen_y = self.tk_canvas.winfo_rooty() + event.y + 6
                self.show_status_popup(screen_x, screen_y, cell)
                return

    # =========================================================
    # RENDER
    # =========================================================
    def clear_canvas(self):
        self.tk_canvas.delete("all")
        self.cell_map = []

    def draw_text(
        self, x, y, text, fill=TEXT_MAIN, font=("Segoe UI", 11), anchor="center"
    ):
        self.tk_canvas.create_text(x, y, text=text, fill=fill, font=font, anchor=anchor)

    def draw_cell(self, x, y, w, h, text, fill, outline, bold=False):
        self.tk_canvas.create_rectangle(
            x,
            y,
            x + w,
            y + h,
            fill=fill,
            outline=outline,
            width=1,
        )
        self.draw_text(
            x + w / 2,
            y + h / 2,
            text,
            fill=TEXT_MAIN,
            font=("Segoe UI", 11, "bold" if bold else "normal"),
        )

    def render_schedule(self):
        self.clear_canvas()

        if not self.schedule_data:
            self.empty_label = ctk.CTkLabel(
                self.tk_canvas,
                text="Không có dữ liệu. Bấm 'Load Schedule' để tải lịch.",
                font=("Segoe UI", 14),
                text_color=TEXT_SUB,
            )
            self.tk_canvas.create_window(20, 20, anchor="nw", window=self.empty_label)
            self.tk_canvas.configure(scrollregion=(0, 0, 1000, 400))
            return

        grouped = {}
        for item in self.schedule_data:
            shift = item.get("shift_name", "")
            username = item.get("username", "")
            grouped.setdefault(shift, {})
            grouped[shift].setdefault(username, {})
            grouped[shift][username][item.get("day_name", "")] = item

        total_width = (
            self.left_pad
            + self.col_widths["employee"]
            + self.col_widths["vn"]
            + self.col_widths["us"]
            + (self.col_widths["day"] * 7)
            + 30
        )

        y = self.top_pad

        title_text = f"Weekly Schedule - {self.selected_department}"
        if self.selected_department == "Sale Team":
            title_text += f" - {self.selected_team}"
        title_text += f" - Week Start {self.week_start}"

        self.draw_text(
            self.left_pad,
            y,
            title_text,
            fill=TEXT_MAIN,
            font=("Segoe UI", 16, "bold"),
            anchor="nw",
        )
        y += 34

        for shift_name, users in grouped.items():
            shift_fill = SHIFT_COLORS.get(shift_name, BG_CARD)
            shift_outline = darken_hex(shift_fill, 0.20)

            self.tk_canvas.create_rectangle(
                self.left_pad - 8,
                y,
                total_width - 20,
                y
                + self.shift_title_height
                + self.header_height
                + (len(users) * self.row_height)
                + 14,
                fill=shift_fill,
                outline=shift_outline,
                width=1,
            )

            self.draw_text(
                self.left_pad + 8,
                y + 9,
                shift_name,
                fill=TEXT_MAIN,
                font=("Segoe UI", 14, "bold"),
                anchor="nw",
            )
            y += self.shift_title_height

            x = self.left_pad
            headers = ["Employee", "VN Time", "US Time"] + self.get_week_headers()
            widths = [
                self.col_widths["employee"],
                self.col_widths["vn"],
                self.col_widths["us"],
            ] + [self.col_widths["day"]] * 7

            for header, width in zip(headers, widths):
                self.tk_canvas.create_rectangle(
                    x,
                    y,
                    x + width,
                    y + self.header_height,
                    fill=HEADER_BG,
                    outline=HEADER_BG,
                    width=1,
                )
                self.draw_text(
                    x + width / 2,
                    y + self.header_height / 2,
                    header,
                    fill=HEADER_TEXT,
                    font=("Segoe UI", 10, "bold"),
                )
                x += width

            y += self.header_height

            for username, days in users.items():
                sample_item = next(iter(days.values()))
                vn_time = sample_item.get("vn_time_range", "")
                us_time = sample_item.get("us_time_range", "")
                target_department = sample_item.get(
                    "department", self.selected_department
                )
                target_team = sample_item.get("team", self.selected_team)

                x = self.left_pad

                base_cells = [
                    (username, self.col_widths["employee"]),
                    (vn_time, self.col_widths["vn"]),
                    (us_time, self.col_widths["us"]),
                ]

                for text, width in base_cells:
                    self.draw_cell(
                        x,
                        y,
                        width,
                        self.row_height,
                        text,
                        fill=BG_CARD,
                        outline=BORDER,
                        bold=False,
                    )
                    x += width

                for day_name in self.day_order:
                    item = days.get(day_name)
                    status = item["status_code"] if item else ""
                    work_date = item["work_date"] if item else ""

                    width = self.col_widths["day"]

                    if not item:
                        self.draw_cell(
                            x,
                            y,
                            width,
                            self.row_height,
                            "",
                            fill=BG_CARD,
                            outline=BORDER,
                            bold=False,
                        )
                        x += width
                        continue

                    key = (username, work_date)
                    if key in self.pending_changes:
                        status = self.pending_changes[key]["status_code"]

                    fill_color = STATUS_COLORS.get(status, "#ffffff")
                    outline_color = darken_hex(fill_color, 0.22)

                    self.draw_cell(
                        x,
                        y,
                        width,
                        self.row_height,
                        status,
                        fill=fill_color,
                        outline=outline_color,
                        bold=True,
                    )

                    can_edit = self.can_edit_schedule(target_department, target_team)
                    if can_edit:
                        self.cell_map.append(
                            {
                                "bbox": (x, y, x + width, y + self.row_height),
                                "username": username,
                                "work_date": work_date,
                                "status": item["status_code"],
                                "day_name": day_name,
                                "target_department": target_department,
                                "target_team": target_team,
                                "can_edit": True,
                            }
                        )

                    x += width

                y += self.row_height

            y += self.section_gap

        self.tk_canvas.configure(scrollregion=(0, 0, total_width, y + 20))
