# pages/signup_page.py

import customtkinter as ctk
from tkinter import messagebox

from services.signup_service import send_register_otp, register_api
from utils.theme import (
    BG_MAIN,
    BG_PANEL,
    BORDER,
    TEXT_MAIN,
    TEXT_SUB,
    BTN_PRIMARY,
    BTN_PRIMARY_HOVER,
    BTN_DARK,
    BTN_DARK_HOVER,
    INPUT_BG,
    INPUT_TEXT,
    INPUT_PLACEHOLDER,
)


class SignUpPage(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)

        self.title("Sign Up")
        self.geometry("460x820")
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)

        self.grab_set()

        self.selected_department = "Select Department"
        self.department_menu_open = False

        container = ctk.CTkFrame(
            self,
            fg_color=BG_PANEL,
            corner_radius=24,
            border_width=1,
            border_color=BORDER,
        )
        container.pack(fill="both", expand=True, padx=14, pady=14)

        title_label = ctk.CTkLabel(
            container,
            text="Create Account",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color=TEXT_MAIN,
        )
        title_label.pack(pady=(24, 10))

        sub_label = ctk.CTkLabel(
            container,
            text="Đăng ký tài khoản nhân viên",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_SUB,
        )
        sub_label.pack(pady=(0, 18))

        entry_width = 310
        entry_height = 44
        entry_corner = 14
        border_hex = "#b79a67"

        # ================= INPUT =================
        self.username_entry = ctk.CTkEntry(
            container,
            width=entry_width,
            height=entry_height,
            placeholder_text="Username",
            corner_radius=entry_corner,
            fg_color=INPUT_BG,
            text_color=INPUT_TEXT,
            placeholder_text_color=INPUT_PLACEHOLDER,
            border_width=1,
            border_color=border_hex,
        )
        self.username_entry.pack(pady=7)

        self.full_name_entry = ctk.CTkEntry(
            container,
            width=entry_width,
            height=entry_height,
            placeholder_text="Họ và tên",
            corner_radius=entry_corner,
            fg_color=INPUT_BG,
            text_color=INPUT_TEXT,
            placeholder_text_color=INPUT_PLACEHOLDER,
            border_width=1,
            border_color=border_hex,
        )
        self.full_name_entry.pack(pady=7)

        self.email_entry = ctk.CTkEntry(
            container,
            width=entry_width,
            height=entry_height,
            placeholder_text="Email (@aiomerchant.com)",
            corner_radius=entry_corner,
            fg_color=INPUT_BG,
            text_color=INPUT_TEXT,
            placeholder_text_color=INPUT_PLACEHOLDER,
            border_width=1,
            border_color=border_hex,
        )
        self.email_entry.pack(pady=7)

        # ================= DEPARTMENT =================
        self.department_frame = ctk.CTkComboBox(
            container,
            values=[
                "Technical Support",
                "Sale Team",
                "Office",
                "Management",
                "Customer Service",
                "Marketing Team",
            ],
            width=entry_width,
            height=entry_height,
            fg_color=INPUT_BG,
            text_color=INPUT_TEXT,
            border_color=border_hex,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            command=self.set_department,
        )
        self.department_frame.set("Select Department")
        self.department_frame.pack(pady=7)

        # ================= TEAM =================
        self.team_combo = ctk.CTkComboBox(
            container,
            values=["General"],
            width=entry_width,
            height=entry_height,
            fg_color=INPUT_BG,
            text_color=INPUT_TEXT,
            border_color=border_hex,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
        )
        self.team_combo.set("General")
        self.team_combo.pack(pady=7)

        # ================= PASSWORD =================
        self.password_entry = ctk.CTkEntry(
            container,
            width=entry_width,
            height=entry_height,
            placeholder_text="Password",
            show="*",
            corner_radius=entry_corner,
            fg_color=INPUT_BG,
            text_color=INPUT_TEXT,
            placeholder_text_color=INPUT_PLACEHOLDER,
            border_width=1,
            border_color=border_hex,
        )
        self.password_entry.pack(pady=7)

        self.confirm_password_entry = ctk.CTkEntry(
            container,
            width=entry_width,
            height=entry_height,
            placeholder_text="Confirm Password",
            show="*",
            corner_radius=entry_corner,
            fg_color=INPUT_BG,
            text_color=INPUT_TEXT,
            placeholder_text_color=INPUT_PLACEHOLDER,
            border_width=1,
            border_color=border_hex,
        )
        self.confirm_password_entry.pack(pady=7)

        self.otp_entry = ctk.CTkEntry(
            container,
            width=entry_width,
            height=entry_height,
            placeholder_text="OTP Code",
            corner_radius=entry_corner,
            fg_color=INPUT_BG,
            text_color=INPUT_TEXT,
            placeholder_text_color=INPUT_PLACEHOLDER,
            border_width=1,
            border_color=border_hex,
        )
        self.otp_entry.pack(pady=7)

        # ================= BUTTON =================
        ctk.CTkButton(
            container,
            text="Send OTP",
            width=entry_width,
            height=entry_height,
            fg_color=BTN_DARK,
            hover_color=BTN_DARK_HOVER,
            command=self.handle_send_otp,
        ).pack(pady=(16, 10))

        ctk.CTkButton(
            container,
            text="Sign Up",
            width=entry_width,
            height=entry_height,
            fg_color=BTN_PRIMARY,
            hover_color=BTN_PRIMARY_HOVER,
            command=self.handle_signup,
        ).pack(pady=(0, 10))

    # ================= LOGIC =================
    def set_department(self, value):
        self.selected_department = value

        if value == "Sale Team":
            self.team_combo.configure(values=["Team 1", "Team 2", "Team 3"])
            self.team_combo.set("Team 1")
        else:
            self.team_combo.configure(values=["General"])
            self.team_combo.set("General")

    def handle_send_otp(self):
        email = self.email_entry.get().strip().lower()

        if not email.endswith("@aiomerchant.com"):
            messagebox.showerror("Error", "Chỉ nhận email công ty")
            return

        result = send_register_otp(email)

        if result.get("success"):
            messagebox.showinfo("Success", "OTP đã gửi")
        else:
            messagebox.showerror("Error", result.get("message"))

    def handle_signup(self):
        username = self.username_entry.get().strip()
        full_name = self.full_name_entry.get().strip()
        email = self.email_entry.get().strip().lower()
        department = self.selected_department
        team = self.team_combo.get().strip()
        password = self.password_entry.get().strip()
        confirm_password = self.confirm_password_entry.get().strip()
        otp = self.otp_entry.get().strip()

        if not all([username, full_name, email, password, confirm_password, otp]):
            messagebox.showerror("Error", "Thiếu thông tin")
            return

        if department == "Select Department":
            messagebox.showerror("Error", "Chọn Department")
            return

        if password != confirm_password:
            messagebox.showerror("Error", "Sai mật khẩu")
            return

        result = register_api(
            username, full_name, email, password, otp, department, team
        )

        if result.get("success"):
            messagebox.showinfo("Success", "Đăng ký thành công")
            self.destroy()
        else:
            messagebox.showerror("Error", result.get("message"))
