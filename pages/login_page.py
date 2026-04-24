import os
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image

from services.auth_service import login_api
from pages.signup_page import SignUpPage
from utils.resource_utils import get_data_path


class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, on_login_success):
        super().__init__(parent, fg_color="#0f0b0a")
        self.parent = parent
        self.on_login_success = on_login_success

        self.logo_image = None
        self.user_icon = None
        self.lock_icon = None

        self.build_ui()

    def get_base_path(self):
        return os.path.dirname(os.path.abspath(__file__))

    def load_icon(self, filename, size=(20, 20)):
        path = get_data_path(filename)

        if os.path.exists(path):
            try:
                return ctk.CTkImage(Image.open(path), size=size)
            except Exception:
                return None
        return None

    def load_image_fit(self, filename, max_width, max_height):
        path = get_data_path(filename)

        if not os.path.exists(path):
            return None

        try:
            image = Image.open(path)
            width, height = image.size
            if width <= 0 or height <= 0:
                return None

            scale = min(max_width / width, max_height / height)
            size = (max(1, int(width * scale)), max(1, int(height * scale)))
            return ctk.CTkImage(light_image=image, dark_image=image, size=size)
        except Exception:
            return None

    def build_ui(self):
        self.user_icon = self.load_icon("user.png", (20, 20))
        self.lock_icon = self.load_icon("lock.png", (20, 20))

        container = ctk.CTkFrame(
            self,
            width=450,
            height=650,
            corner_radius=26,
            fg_color="#1a1210",
            border_width=1,
            border_color="#6f4b1f",
        )
        container.place(relx=0.5, rely=0.5, anchor="center")
        container.pack_propagate(False)

        logo_path = get_data_path("logo_mark_v3.png")
        fallback_logo_path = get_data_path("logo.png")

        if os.path.exists(logo_path):
            try:
                self.logo_image = self.load_image_fit("logo_mark_v3.png", 210, 130)
                logo_label = ctk.CTkLabel(container, image=self.logo_image, text="")
                logo_label.pack(pady=(22, 8))
            except Exception:
                fallback_logo = ctk.CTkLabel(
                    container,
                    text="DA",
                    font=ctk.CTkFont(size=34, weight="bold"),
                    text_color="#f4e7c1",
                )
                fallback_logo.pack(pady=(24, 12))
        elif os.path.exists(fallback_logo_path):
            try:
                self.logo_image = self.load_image_fit("logo.png", 210, 130)
                logo_label = ctk.CTkLabel(container, image=self.logo_image, text="")
                logo_label.pack(pady=(22, 8))
            except Exception:
                pass

        title = ctk.CTkLabel(
            container,
            text="Delta One",
            font=ctk.CTkFont(size=38, weight="bold"),
            text_color="#f4e7c1",
        )
        title.pack(pady=(4, 18))

        # ===== USERNAME =====
        user_frame = ctk.CTkFrame(
            container, width=300, height=48, corner_radius=14, fg_color="#f6ead2"
        )
        user_frame.pack(pady=10)
        user_frame.pack_propagate(False)

        ctk.CTkLabel(user_frame, image=self.user_icon, text="").pack(
            side="left", padx=(12, 4)
        )

        ctk.CTkLabel(
            user_frame, text="|", text_color="#8f6b32", font=("Segoe UI", 16, "bold")
        ).pack(side="left")

        self.username_entry = ctk.CTkEntry(
            user_frame,
            border_width=0,
            fg_color="transparent",
            text_color="black",
            placeholder_text="Username",
            placeholder_text_color="#8a8175",
        )
        self.username_entry.pack(side="left", fill="both", expand=True, padx=8)

        # ===== PASSWORD =====
        pass_frame = ctk.CTkFrame(
            container, width=300, height=48, corner_radius=14, fg_color="#f6ead2"
        )
        pass_frame.pack(pady=10)
        pass_frame.pack_propagate(False)

        ctk.CTkLabel(pass_frame, image=self.lock_icon, text="").pack(
            side="left", padx=(12, 4)
        )

        ctk.CTkLabel(
            pass_frame, text="|", text_color="#8f6b32", font=("Segoe UI", 16, "bold")
        ).pack(side="left")

        self.password_entry = ctk.CTkEntry(
            pass_frame,
            border_width=0,
            fg_color="transparent",
            text_color="black",
            placeholder_text="Password",
            placeholder_text_color="#8a8175",
            show="*",
        )
        self.password_entry.pack(side="left", fill="both", expand=True, padx=8)

        # ===== LOGIN BUTTON =====
        login_btn = ctk.CTkButton(
            container,
            text="Login",
            width=300,
            height=46,
            corner_radius=14,
            fg_color="#a36a1f",
            hover_color="#d4a64a",
            text_color="#fffaf0",
            font=("Segoe UI", 15, "bold"),
            command=self.handle_login,
        )
        login_btn.pack(pady=(22, 12))

        # ===== SIGN UP =====
        signup_btn = ctk.CTkButton(
            container,
            text="Sign Up",
            width=300,
            height=46,
            corner_radius=14,
            fg_color="#3a2a1e",
            hover_color="#5a3e22",
            text_color="#f4e7c1",
            font=("Segoe UI", 15, "bold"),
            command=self.open_signup,
        )
        signup_btn.pack()

        self.username_entry.bind("<Return>", lambda event: self.handle_login())
        self.password_entry.bind("<Return>", lambda event: self.handle_login())

    def handle_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning(
                "Thiếu thông tin", "Vui lòng nhập username và password."
            )
            return

        result = login_api(username, password)

        if result.get("success"):
            user = {
                "username": result.get("username"),
                "full_name": result.get("full_name", ""),
                "display_name": result.get("display_name", ""),
                "role": result.get("role"),
                "department": result.get("department", "Technical Support"),
                "team": result.get("team", "General"),
            }
            self.on_login_success(user)
        else:
            messagebox.showerror(
                "Login Failed", result.get("message", "Sai tài khoản hoặc mật khẩu.")
            )

    def open_signup(self):
        signup_window = SignUpPage(self)
        signup_window.focus()
