import os
import customtkinter as ctk
from PIL import Image
from tkinter import messagebox
from datetime import datetime

from pages.pos_page import POSPage
from pages.sql_page import SQLPage
from pages.link_data_page import LinkDataPage
from pages.process_page import ProcessPage
from pages.tech_schedule_page import TechSchedulePage
from pages.admin_approval_page import AdminApprovalPage
from pages.pin_verify_dialog import PinVerifyDialog
from pages.leave_summary_page import LeaveSummaryPage
from pages.leave_request_page import LeaveRequestPage

from services.auth_service import (
    get_pin_status_api,
    set_pin_api,
    verify_pin_api,
    change_pin_api,
    change_password_api,
)

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
CONTENT_BORDER = "#6e5846"

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

        self.logo_image = None
        self.settings_icon = None
        self.logout_icon = None

        self.menu_open = False
        self.reflow_after_id = None

        self.header_frame = None
        self.topbar_main = None
        self.nav_frame = None
        self.overlay_menu_frame = None
        self.content_wrapper = None
        self.content_frame = None

        self.clock_time_label = None
        self.clock_date_label = None

        self.nav_buttons = {}
        self.nav_button_order = []
        self.nav_button_widths = {}
        self.nav_widgets = []

        self.work_schedule_button = None
        self.work_schedule_dropdown = None
        self.work_schedule_dropdown_open = False

        self.extra_menu_buttons = {}
        self.admin_manager_window = None

        self.old_password_entry = None
        self.new_password_entry = None
        self.confirm_new_password_entry = None

        self.tooltip_window = None

        self.build_ui()
        self.update_clock()
        self.after(300, self.setup_click_outside)

        self.after(150, self.reflow_header_layout)
        self.after(200, self.show_welcome_page)

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

    def get_role(self):
        return str(self.user.get("role", "TS Junior")).strip()

    def get_display_role(self):
        return self.get_role()

    def can_open_work_schedule_menu(self):
        role = self.get_role()
        return role in [
            "Admin",
            "Management",
            "HR",
            "Leader",
            "Manager",
            "TS Leader",
            "Sale Leader",
        ]

    def can_access(self, page_name):
        role = str(self.get_role()).strip()

        all_staff_roles = [
            "TS Leader",
            "TS Senior",
            "TS Junior",
            "TS Probation",
            "Sale Leader",
            "Sale Staff",
            "Sale Admin",
            "HR",
            "Accountant",
            "Management",
            "Admin",
            "CS Leader",
            "CS Staff",
            "MT Leader",
            "MT Staff",
            "Leader",
            "Manager",
            "Tech",
            "TechDS",
            "Sale",
        ]

        permission_map = {
            "POS": all_staff_roles,
            "Link / Data": all_staff_roles,
            "Cách xử lý": all_staff_roles,
            "SQL": ["TS Leader", "TS Senior", "Management", "Admin"],
            "Work Schedule": all_staff_roles,
            "Monthly Leave Summary": [
                "Admin",
                "Management",
                "HR",
                "Accountant",
                "Leader",
                "Manager",
                "TS Leader",
                "Sale Leader",
            ],
            "Create Leave Request": all_staff_roles,
            "Settings": all_staff_roles,
            "Admin Approval": ["Admin", "Management"],
        }

        allowed_roles = permission_map.get(page_name, ["Admin"])
        return role in allowed_roles

    def show_access_denied(self, page_name=None):
        messagebox.showwarning(
            "Not Available",
            "This feature is not available.",
        )

    def clear_content_frame(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

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

    def create_section_title(self, parent, title, subtitle=""):
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
        self.logo_image = self.safe_load_icon("logo.png", (74, 74))
        if self.logo_image is None:
            self.logo_image = self.safe_load_icon("app.ico", (74, 74))
        if self.logo_image is None:
            self.logo_image = self.safe_load_icon("home.png", (74, 74))

        self.settings_icon = self.safe_load_icon("setting.png", (22, 22))
        self.logout_icon = self.safe_load_icon("log-out.png", (24, 24))

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.build_header()
        self.build_body()

    def build_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 10))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.topbar_main = ctk.CTkFrame(
            self.header_frame,
            fg_color=TOPBAR_BG,
            corner_radius=20,
            border_width=1,
            border_color=TOPBAR_BORDER,
            height=102,
        )
        self.topbar_main.grid(row=0, column=0, sticky="ew")
        self.topbar_main.grid_propagate(False)

        self.topbar_main.grid_rowconfigure(0, weight=1)
        self.topbar_main.grid_columnconfigure(0, weight=0)
        self.topbar_main.grid_columnconfigure(1, weight=1)
        self.topbar_main.grid_columnconfigure(2, weight=0)
        self.topbar_main.grid_columnconfigure(3, weight=0)
        self.topbar_main.grid_columnconfigure(4, minsize=92)
        self.topbar_main.grid_columnconfigure(5, minsize=92)

        self.topbar_main.bind("<Configure>", self.on_topbar_resize)

        # ===== LEFT BOX =====
        left_box = ctk.CTkFrame(self.topbar_main, fg_color="transparent", height=72)
        left_box.grid(row=0, column=0, sticky="w", padx=(14, 8), pady=(15, 15))
        left_box.grid_propagate(False)

        if self.logo_image:
            logo_label = ctk.CTkLabel(left_box, text="", image=self.logo_image)
            logo_label.pack(side="left", padx=(0, 12), pady=0)

        self.menu_toggle_btn = ctk.CTkButton(
            left_box,
            text="☰",
            width=46,
            height=46,
            corner_radius=12,
            fg_color=BTN_IDLE,
            hover_color=BTN_IDLE_HOVER,
            text_color=TEXT_MAIN,
            font=("Segoe UI", 22, "bold"),
            command=self.toggle_expand_menu,
        )
        self.menu_toggle_btn.pack(side="left", pady=0)

        # ===== NAV =====
        self.nav_frame = ctk.CTkFrame(self.topbar_main, fg_color="transparent")
        self.nav_frame.grid(row=0, column=1, sticky="w", padx=(4, 10), pady=(15, 15))

        nav_items = [
            ("POS", self.show_pos_page, 112),
            ("SQL", self.show_sql_page, 112),
            ("Link / Data", self.show_link_data_page, 138),
            ("Cách xử lý", self.show_process_page, 130),
        ]

        self.nav_buttons = {}
        self.nav_button_order = []
        self.nav_button_widths = {}
        self.nav_widgets = []

        for name, command, btn_width in nav_items:
            btn = ctk.CTkButton(
                self.nav_frame,
                text=name,
                width=btn_width,
                height=42,
                corner_radius=14,
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_MAIN,
                border_width=1,
                border_color=BTN_IDLE,
                font=("Segoe UI", 13, "bold"),
                command=command,
            )
            self.nav_buttons[name] = btn
            self.nav_button_order.append(name)
            self.nav_button_widths[name] = btn_width
            self.nav_widgets.append((name, btn, btn_width))

        self.work_schedule_button = ctk.CTkButton(
            self.nav_frame,
            text="Work Schedule",
            width=180,
            height=42,
            corner_radius=14,
            fg_color=BTN_IDLE,
            hover_color=BTN_IDLE_HOVER,
            text_color=TEXT_MAIN,
            border_width=1,
            border_color=BTN_IDLE,
            font=("Segoe UI", 13, "bold"),
            command=self.toggle_work_schedule_dropdown,
        )
        self.nav_widgets.append(("Work Schedule", self.work_schedule_button, 180))

        self.work_schedule_dropdown = ctk.CTkFrame(
            self,
            fg_color="#2b231e",
            corner_radius=16,
            border_width=1,
            border_color="#8b6b4a",
            width=220,
            height=170,
        )

        work_items = [
            ("Work Schedule", self.show_work_schedule_page),
            ("Monthly Leave Summary", self.show_leave_summary_page),
            ("Create Leave Request", self.show_leave_request_page),
        ]

        for i, (name, command) in enumerate(work_items):
            btn = ctk.CTkButton(
                self.work_schedule_dropdown,
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
            btn.pack(fill="x", padx=14, pady=(12 if i == 0 else 6, 0))

        self.work_schedule_dropdown.place_forget()

        # ===== CLOCK =====
        clock_outer = ctk.CTkFrame(
            self.topbar_main,
            fg_color="#241d18",
            corner_radius=18,
            border_width=1,
            border_color="#a47b4d",
            width=148,
            height=74,
        )
        clock_outer.grid(row=0, column=2, padx=(6, 12), pady=(14, 14), sticky="")
        clock_outer.grid_propagate(False)

        clock_inner = ctk.CTkFrame(
            clock_outer,
            fg_color=BG_PANEL_2,
            corner_radius=14,
            border_width=1,
            border_color=TOPBAR_BORDER,
        )
        clock_inner.pack(fill="both", expand=True, padx=4, pady=4)

        self.clock_date_label = ctk.CTkLabel(
            clock_inner,
            text="Tue 01/01/2026",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_SUB,
        )
        self.clock_date_label.pack(pady=(8, 2))

        self.clock_time_label = ctk.CTkLabel(
            clock_inner,
            text="01:10 PM",
            font=("Segoe UI", 18, "bold"),
            text_color=BTN_ACTIVE,
        )
        self.clock_time_label.pack(pady=(0, 6))

        # ===== USER INFO =====
        right_info_box = ctk.CTkFrame(
            self.topbar_main,
            fg_color="transparent",
            height=72,
        )
        right_info_box.grid(row=0, column=3, padx=(0, 12), pady=(14, 14), sticky="e")
        right_info_box.grid_propagate(False)

        app_name = ctk.CTkLabel(
            right_info_box,
            text="Delta Assistant",
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_MAIN,
        )
        app_name.pack(anchor="e", pady=(2, 0))

        version = ctk.CTkLabel(
            right_info_box,
            text="Ver 0.0.1",
            font=("Segoe UI", 11),
            text_color=TEXT_SUB,
        )
        version.pack(anchor="e", pady=(2, 4))

        welcome = ctk.CTkLabel(
            right_info_box,
            text=f"User: {self.user.get('username', 'Unknown')} ({self.get_display_role()})",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT_SUB,
        )
        welcome.pack(anchor="e")

        # ===== SETTINGS =====
        settings_container = ctk.CTkFrame(
            self.topbar_main,
            fg_color="transparent",
            width=92,
            height=88,
        )
        settings_container.grid(
            row=0, column=4, padx=(0, 10), pady=(10, 10), sticky="e"
        )
        settings_container.grid_propagate(False)

        settings_circle = ctk.CTkFrame(
            settings_container,
            width=54,
            height=54,
            corner_radius=27,
            fg_color=BTN_IDLE,
            border_width=1,
            border_color=TOPBAR_BORDER,
        )
        settings_circle.pack(pady=(0, 4))
        settings_circle.pack_propagate(False)

        if self.settings_icon is not None:
            settings_icon_label = ctk.CTkLabel(
                settings_circle,
                text="",
                image=self.settings_icon,
            )
        else:
            settings_icon_label = ctk.CTkLabel(
                settings_circle,
                text="⚙",
                font=("Segoe UI", 18, "bold"),
                text_color=TEXT_MAIN,
            )
        settings_icon_label.place(relx=0.5, rely=0.5, anchor="center")

        settings_label = ctk.CTkLabel(
            settings_container,
            text="SETTING",
            font=("Segoe UI", 10),
            text_color=TEXT_MAIN,
        )
        settings_label.pack()

        def _open_settings(event=None):
            self.show_settings_page()

        settings_circle.bind("<Button-1>", _open_settings)
        settings_icon_label.bind("<Button-1>", _open_settings)
        settings_label.bind("<Button-1>", _open_settings)
        settings_container.bind("<Button-1>", _open_settings)

        # ===== LOGOUT =====
        logout_container = ctk.CTkFrame(
            self.topbar_main,
            fg_color="transparent",
            width=92,
            height=88,
        )
        logout_container.grid(row=0, column=5, padx=(0, 14), pady=(10, 10), sticky="e")
        logout_container.grid_propagate(False)

        logout_circle = ctk.CTkFrame(
            logout_container,
            width=54,
            height=54,
            corner_radius=27,
            fg_color=BTN_DANGER,
            border_width=1,
            border_color=TOPBAR_BORDER,
        )
        logout_circle.pack(pady=(0, 4))
        logout_circle.pack_propagate(False)

        if self.logout_icon is not None:
            logout_icon_label = ctk.CTkLabel(
                logout_circle,
                text="",
                image=self.logout_icon,
            )
        else:
            logout_icon_label = ctk.CTkLabel(
                logout_circle,
                text="⎋",
                font=("Segoe UI", 18, "bold"),
                text_color=TEXT_MAIN,
            )
        logout_icon_label.place(relx=0.5, rely=0.5, anchor="center")

        logout_label = ctk.CTkLabel(
            logout_container,
            text="LOG OUT",
            font=("Segoe UI", 10),
            text_color=TEXT_MAIN,
        )
        logout_label.pack()

        def _do_logout(event=None):
            if messagebox.askyesno("Confirm", "Do you want to log out?"):
                self.on_logout()

        logout_circle.bind("<Button-1>", _do_logout)
        logout_icon_label.bind("<Button-1>", _do_logout)
        logout_label.bind("<Button-1>", _do_logout)
        logout_container.bind("<Button-1>", _do_logout)

        # ===== OVERLAY MENU =====
        self.overlay_menu_frame = ctk.CTkFrame(
            self,
            fg_color="#2b231e",
            corner_radius=18,
            border_width=1,
            border_color="#8b6b4a",
            width=220,
            height=220,
        )

        extra_items = [
            ("Function 1", self.placeholder_function),
            ("Function 2", self.placeholder_function),
            ("Function 3", self.placeholder_function),
            ("Function 4", self.placeholder_function),
        ]

        for i, (name, command) in enumerate(extra_items):
            btn = ctk.CTkButton(
                self.overlay_menu_frame,
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
            btn.pack(fill="x", padx=16, pady=(12 if i == 0 else 6, 0))

        self.overlay_menu_frame.place_forget()

    def build_body(self):
        body_frame = ctk.CTkFrame(self, fg_color=BG_APP, corner_radius=0)
        body_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        body_frame.grid_rowconfigure(0, weight=1)
        body_frame.grid_columnconfigure(0, weight=1)

        self.content_wrapper = ctk.CTkFrame(
            body_frame,
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

    def reflow_header_layout(self):
        self.reflow_after_id = None

        if not self.winfo_exists():
            return

        try:
            total_width = self.topbar_main.winfo_width()
            if total_width <= 1:
                self.reflow_after_id = self.after(100, self.reflow_header_layout)
                return

            reserved_width = 560
            available_width = max(260, total_width - reserved_width)

            for widget in self.nav_frame.winfo_children():
                widget.grid_forget()

            row = 0
            col = 0
            used_width = 0
            row_count = 1

            for item_name, widget, item_width in self.nav_widgets:
                widget_width = item_width + 8

                if used_width + widget_width > available_width and used_width > 0:
                    row += 1
                    col = 0
                    used_width = 0
                    row_count += 1

                widget.grid(row=row, column=col, padx=(0, 8), pady=4, sticky="w")
                used_width += widget_width
                col += 1

            new_height = 102 + ((row_count - 1) * 50)

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

            btn_x = self.work_schedule_button.winfo_x()
            btn_y = self.work_schedule_button.winfo_y()
            btn_h = self.work_schedule_button.winfo_height()

            self.work_schedule_dropdown.place(
                in_=self.nav_frame, x=btn_x, y=btn_y + btn_h + 6
            )
            self.work_schedule_dropdown.lift()
            self.work_schedule_dropdown_open = True
        except Exception:
            pass

    def hide_top_menus(self):
        self.menu_open = False
        if self.overlay_menu_frame is not None:
            self.overlay_menu_frame.place_forget()

        self.work_schedule_dropdown_open = False
        if self.work_schedule_dropdown is not None:
            self.work_schedule_dropdown.place_forget()

        if self.menu_toggle_btn is not None:
            self.menu_toggle_btn.configure(
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_MAIN,
            )

    def handle_work_schedule_menu_action(self, callback):
        self.work_schedule_dropdown_open = False
        if self.work_schedule_dropdown is not None:
            self.work_schedule_dropdown.place_forget()

        self.update_idletasks()
        callback()

    def show_welcome_page(self):
        self.hide_top_menus()
        self.current_page = "Welcome"

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

        welcome_card = ctk.CTkFrame(
            self.content_frame,
            fg_color=CONTENT_INNER,
            corner_radius=18,
            border_width=1,
            border_color=CONTENT_BORDER,
        )
        welcome_card.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(
            welcome_card,
            text="Welcome to Delta Assistant",
            font=("Segoe UI", 26, "bold"),
            text_color=TEXT_DARK,
        ).pack(anchor="w", padx=24, pady=(24, 10))

        ctk.CTkLabel(
            welcome_card,
            text="Chọn chức năng ở thanh menu để bắt đầu.",
            font=("Segoe UI", 14),
            text_color=TEXT_MUTED_DARK,
        ).pack(anchor="w", padx=24, pady=(0, 20))

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

        self.create_section_title(
            self.content_frame,
            "SQL",
            "Tra cứu và thao tác dữ liệu SQL.",
        )

        page_host = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        page_host.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        try:
            sql_page = SQLPage(page_host)
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

    def show_process_page(self):
        if not self.can_access("Cách xử lý"):
            self.show_access_denied("Cách xử lý")
            return

        self.hide_top_menus()
        self.set_active_nav("Cách xử lý")
        self.clear_content_frame()

        self.create_section_title(
            self.content_frame,
            "Cách xử lý",
            "Quy trình và hướng dẫn xử lý nội bộ.",
        )

        page_host = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        page_host.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        try:
            process_page = ProcessPage(page_host)
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

        if self.get_role() in ["Admin", "Management", "admin"]:
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
                self, admin_name=self.user.get("username", "admin")
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

            self.hide_top_menus()

        except Exception:
            pass

        # đảm bảo luôn đóng dropdown
        self.work_schedule_dropdown_open = False
        if self.work_schedule_dropdown is not None:
            self.work_schedule_dropdown.place_forget()

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

        pin_dialog = PinVerifyDialog(
            self,
            title="Enter 4-digit PIN",
            on_success=after_enter_pin,
        )

    def open_create_pin_flow(self):
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
            dialog_ref["dialog"].set_dialog_title("Enter new PIN")
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

        dialog_ref["dialog"] = PinVerifyDialog(
            self,
            title="Enter current PIN",
            on_success=step_old_pin,
        )
