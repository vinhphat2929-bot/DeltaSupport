import customtkinter as ctk
from tkinter import messagebox
from datetime import date

from services.auth_service import get_tech_schedule_month_summary_api

BG_MAIN = "#f3ede4"
BG_CARD = "#fffaf3"
BORDER = "#6e5846"
TEXT_MAIN = "#2a221d"
TEXT_SUB = "#705d4f"
HEADER_BG = "#2f2721"
HEADER_TEXT = "#f5efe6"

DEPARTMENTS = [
    "Technical Support",
    "Sale Team",
    "Office",
    "Management",
    "Customer Service",
    "Marketing Team",
]


class LeaveSummaryPage(ctk.CTkFrame):
    def __init__(
        self,
        master,
        current_user=None,
        current_role=None,
        current_department=None,
        current_team=None,
    ):
        super().__init__(master, fg_color="transparent")

        self.current_user = current_user or ""
        self.current_role = current_role or ""
        self.current_department = current_department or ""
        self.current_team = current_team or "General"

        today = date.today()
        self.summary_month = today.month
        self.summary_year = today.year

        self.selected_department = (
            self.current_department if self.current_department else "Technical Support"
        )
        if self.selected_department not in DEPARTMENTS:
            self.selected_department = "Technical Support"

        self.selected_team = self.current_team if self.current_team else "General"
        self.summary_data = []

        self.build_ui()

    # =========================================================
    # PERMISSION
    # =========================================================
    def can_view_summary(self):
        role = str(self.current_role).strip().lower()
        return role in [
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

        title_label = ctk.CTkLabel(
            top_card,
            text="Monthly Leave Summary",
            font=("Segoe UI", 22, "bold"),
            text_color=TEXT_MAIN,
        )
        title_label.grid(row=0, column=0, padx=18, pady=(14, 6), sticky="w")

        self.permission_label = ctk.CTkLabel(
            top_card,
            text="",
            font=("Segoe UI", 12, "italic"),
            text_color=TEXT_SUB,
        )
        self.permission_label.grid(
            row=1, column=0, columnspan=8, padx=18, pady=(0, 8), sticky="w"
        )

        ctk.CTkLabel(
            top_card,
            text="Department",
            font=("Segoe UI", 12),
            text_color=TEXT_SUB,
        ).grid(row=2, column=0, padx=18, pady=(0, 4), sticky="w")

        self.department_combobox = ctk.CTkComboBox(
            top_card,
            values=DEPARTMENTS,
            width=180,
            height=36,
            corner_radius=10,
            command=self.on_department_change,
        )
        self.department_combobox.grid(
            row=2, column=1, padx=(0, 12), pady=(0, 10), sticky="w"
        )
        self.department_combobox.set(self.selected_department)

        ctk.CTkLabel(
            top_card,
            text="Month",
            font=("Segoe UI", 12),
            text_color=TEXT_SUB,
        ).grid(row=2, column=2, padx=(0, 4), pady=(0, 4), sticky="w")

        self.month_entry = ctk.CTkEntry(
            top_card,
            width=100,
            height=36,
            corner_radius=10,
        )
        self.month_entry.grid(row=2, column=3, padx=(0, 12), pady=(0, 10), sticky="w")
        self.month_entry.insert(0, str(self.summary_month))

        ctk.CTkLabel(
            top_card,
            text="Year",
            font=("Segoe UI", 12),
            text_color=TEXT_SUB,
        ).grid(row=2, column=4, padx=(0, 4), pady=(0, 4), sticky="w")

        self.year_entry = ctk.CTkEntry(
            top_card,
            width=110,
            height=36,
            corner_radius=10,
        )
        self.year_entry.grid(row=2, column=5, padx=(0, 12), pady=(0, 10), sticky="w")
        self.year_entry.insert(0, str(self.summary_year))

        self.load_button = ctk.CTkButton(
            top_card,
            text="Load Summary",
            width=140,
            height=36,
            corner_radius=10,
            command=self.on_load_summary_click,
        )
        self.load_button.grid(row=2, column=6, padx=(0, 12), pady=(0, 10), sticky="w")

        body_card = ctk.CTkFrame(
            self,
            fg_color=BG_CARD,
            corner_radius=16,
            border_width=1,
            border_color=BORDER,
        )
        body_card.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        body_card.grid_rowconfigure(0, weight=1)
        body_card.grid_columnconfigure(0, weight=1)
        body_card.grid_columnconfigure(1, weight=0)

        self.table_wrap = ctk.CTkScrollableFrame(
            body_card,
            fg_color="transparent",
            corner_radius=0,
        )
        self.table_wrap.grid(row=0, column=0, sticky="nsew", padx=(12, 8), pady=12)

        self.note_wrap = ctk.CTkFrame(
            body_card,
            fg_color=BG_MAIN,
            corner_radius=14,
            border_width=1,
            border_color=BORDER,
            width=260,
        )
        self.note_wrap.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
        self.note_wrap.grid_propagate(False)

        self.build_note_panel()
        self.update_permission_text()
        self.render_empty_state()

    def build_note_panel(self):
        ctk.CTkLabel(
            self.note_wrap,
            text="Note",
            font=("Segoe UI", 16, "bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w", padx=16, pady=(16, 10))

        note_items = [
            "A.L = Annual Leave",
            "S.L = Sick Leave",
            "C.T.O = Compensatory Time Off",
            "U.L = Unpaid Leave",
            "Other = Other Leave Type",
        ]

        for item in note_items:
            ctk.CTkLabel(
                self.note_wrap,
                text=f"• {item}",
                font=("Segoe UI", 12),
                text_color=TEXT_SUB,
                justify="left",
                wraplength=220,
            ).pack(anchor="w", padx=16, pady=4)

    def update_permission_text(self):
        if self.can_view_summary():
            self.permission_label.configure(
                text="Quyền hiện tại: có thể xem Monthly Leave Summary."
            )
        else:
            self.permission_label.configure(
                text="Quyền hiện tại: không được xem Monthly Leave Summary."
            )

    # =========================================================
    # EVENTS
    # =========================================================
    def on_department_change(self, selected_department):
        self.selected_department = selected_department

    def on_load_summary_click(self):
        if not self.can_view_summary():
            self.render_access_denied()
            return

        try:
            self.summary_month = int(self.month_entry.get().strip())
            self.summary_year = int(self.year_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Month and year must be numbers.")
            return

        self.selected_department = self.department_combobox.get().strip()
        self.load_summary()

    # =========================================================
    # DATA
    # =========================================================
    def load_summary(self):
        if not self.can_view_summary():
            self.render_access_denied()
            return

        try:
            result = get_tech_schedule_month_summary_api(
                self.summary_month,
                self.summary_year,
            )

            if not result.get("success"):
                messagebox.showerror(
                    "Summary Error",
                    result.get("message", "Cannot load monthly summary."),
                )
                return

            raw_data = result.get("data", [])

            filtered = []
            for item in raw_data:
                item_department = str(
                    item.get("department", "Technical Support")
                ).strip()
                if item_department != self.selected_department:
                    continue
                filtered.append(item)

            self.summary_data = filtered
            self.render_summary()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =========================================================
    # RENDER
    # =========================================================
    def clear_table(self):
        for widget in self.table_wrap.winfo_children():
            widget.destroy()

    def render_empty_state(self):
        self.clear_table()

        ctk.CTkLabel(
            self.table_wrap,
            text="Monthly Leave Summary",
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w", padx=8, pady=(8, 10))

        ctk.CTkLabel(
            self.table_wrap,
            text="Bấm 'Load Summary' để tải dữ liệu.",
            font=("Segoe UI", 13),
            text_color=TEXT_SUB,
        ).pack(anchor="w", padx=8, pady=(0, 10))

    def render_access_denied(self):
        self.clear_table()

        ctk.CTkLabel(
            self.table_wrap,
            text="Monthly Leave Summary",
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w", padx=8, pady=(8, 10))

        ctk.CTkLabel(
            self.table_wrap,
            text="Access Denied",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w", padx=8, pady=(0, 6))

        ctk.CTkLabel(
            self.table_wrap,
            text="Chỉ Admin, Management, HR, Accountant và Leader mới được xem.",
            font=("Segoe UI", 12),
            text_color=TEXT_SUB,
            justify="left",
            wraplength=700,
        ).pack(anchor="w", padx=8, pady=(0, 10))

    def render_summary(self):
        self.clear_table()

        title_text = f"Monthly Leave Summary - {self.selected_department} - {self.summary_month}/{self.summary_year}"

        title = ctk.CTkLabel(
            self.table_wrap,
            text=title_text,
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_MAIN,
        )
        title.pack(anchor="w", padx=8, pady=(8, 12))

        if not self.summary_data:
            ctk.CTkLabel(
                self.table_wrap,
                text="No monthly summary data found.",
                font=("Segoe UI", 13),
                text_color=TEXT_SUB,
            ).pack(anchor="w", padx=8, pady=(0, 12))
            return

        table = ctk.CTkFrame(self.table_wrap, fg_color="transparent")
        table.pack(fill="x", padx=4, pady=(0, 12))

        headers = ["Username", "A.L", "S.L", "C.T.O", "U.L", "Other", "Total"]
        widths = [140, 90, 90, 90, 90, 90, 90]

        for col, header in enumerate(headers):
            lbl = ctk.CTkLabel(
                table,
                text=header,
                font=("Segoe UI", 12, "bold"),
                text_color=HEADER_TEXT,
                fg_color=HEADER_BG,
                corner_radius=8,
                width=widths[col],
                height=34,
            )
            lbl.grid(row=0, column=col, padx=4, pady=4, sticky="nsew")

        for row_idx, item in enumerate(self.summary_data, start=1):
            values = [
                item.get("username", item.get("Username", "")),
                item.get("A.L", 0),
                item.get("S.L", 0),
                item.get("C.T.O", 0),
                item.get("U.L", 0),
                item.get("Other", 0),
                item.get("Total", 0),
            ]

            for col_idx, value in enumerate(values):
                lbl = ctk.CTkLabel(
                    table,
                    text=str(value),
                    font=("Segoe UI", 12),
                    text_color=TEXT_MAIN,
                    fg_color=BG_MAIN,
                    corner_radius=8,
                    width=widths[col_idx],
                    height=34,
                )
                lbl.grid(row=row_idx, column=col_idx, padx=4, pady=4, sticky="nsew")
