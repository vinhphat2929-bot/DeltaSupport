import os
import ctypes
import threading
import tempfile
from pathlib import Path
import customtkinter as ctk
from PIL import Image, ImageTk
from tkinter import messagebox

from pages.login_page import LoginPage
from main_app import MainAppPage
from splash_screen import SplashScreen
from services.update_service import (
    check_for_app_update,
    download_update_package,
    ensure_update_can_start,
    get_current_app_version,
    is_frozen_app,
    launch_self_update,
)
from utils.resource_utils import get_data_path
from widgets.update_prompt_dialog import UpdatePromptDialog
from app_version import APP_NAME

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_USER_MODEL_ID = "AIO.DeltaOne"
GWL_STYLE = -16
GA_ROOT = 2
WS_MAXIMIZEBOX = 0x00010000
WS_THICKFRAME = 0x00040000
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020
user32 = ctypes.windll.user32
user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long
user32.SetWindowPos.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_uint,
]
user32.SetWindowPos.restype = ctypes.c_int
user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
user32.GetAncestor.restype = ctypes.c_void_p
shell32 = ctypes.windll.shell32
shell32.SetCurrentProcessExplicitAppUserModelID.argtypes = [ctypes.c_wchar_p]
shell32.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_int


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.current_user = None
        self.display_mode = "windowed"
        self._native_style_job = None
        self._icon_photo = None
        self._bitmap_icon_path = None
        self._update_check_started = False
        self._update_check_in_progress = False
        self._update_dialog = None
        self._update_in_progress = False
        self._update_info = None
        self._update_last_result = None
        self.main_page = None

        self.title(APP_NAME)
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.set_windows_app_id()
        self.set_app_icon()
        self.apply_display_mode("windowed", force=True)
        self.after(150, self.schedule_native_window_style_refresh)

        self.withdraw()
        self.after(100, self.show_splash)

    def get_base_path(self):
        return os.path.dirname(os.path.abspath(__file__))

    def set_windows_app_id(self):
        try:
            shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except Exception:
            pass

    def set_app_icon(self):
        photo_icon_path = get_data_path("icon.png")
        bitmap_icon_path = self.resolve_bitmap_icon_path(photo_icon_path)
        self._bitmap_icon_path = bitmap_icon_path

        if not os.path.exists(photo_icon_path):
            photo_icon_path = bitmap_icon_path

        if not os.path.exists(photo_icon_path):
            print(f"Khong tim thay icon: {photo_icon_path}")
            return

        try:
            if bitmap_icon_path and os.path.exists(bitmap_icon_path):
                self.iconbitmap(bitmap_icon_path)
        except Exception:
            pass

        try:
            with Image.open(photo_icon_path) as icon_image:
                icon_variants = []
                for icon_size in (256, 128, 64, 48, 32, 16):
                    resized = icon_image.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                    icon_variants.append(ImageTk.PhotoImage(resized))
                if icon_variants:
                    self.iconphoto(True, *icon_variants)
                    self._icon_photo = icon_variants
        except Exception as e:
            print("Khong load duoc icon:", e)

    def resolve_bitmap_icon_path(self, photo_icon_path=""):
        icon_candidates = [
            get_data_path("app_v3.ico"),
            get_data_path("app_v2.ico"),
            get_data_path("app.ico"),
        ]
        for candidate in icon_candidates:
            if candidate and os.path.exists(candidate):
                return candidate

        photo_icon_path = str(photo_icon_path or "").strip()
        if not photo_icon_path or not os.path.exists(photo_icon_path):
            return ""

        generated_icon_path = Path(tempfile.gettempdir()) / "DeltaOne" / "runtime_app.ico"
        try:
            generated_icon_path.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(photo_icon_path) as icon_image:
                icon_image.save(
                    generated_icon_path,
                    format="ICO",
                    sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
                )
            return str(generated_icon_path)
        except Exception:
            return ""

    def clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()

    def _get_native_window_handle(self):
        hwnd = self.winfo_id()
        try:
            root_hwnd = user32.GetAncestor(hwnd, GA_ROOT)
            if root_hwnd:
                return root_hwnd
        except Exception:
            pass
        return hwnd

    def apply_native_window_style(self):
        self._native_style_job = None

        try:
            hwnd = self._get_native_window_handle()
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            style = (style | WS_MAXIMIZEBOX) & ~WS_THICKFRAME
            user32.SetWindowLongW(hwnd, GWL_STYLE, style)
            user32.SetWindowPos(
                hwnd,
                0,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
            )
        except Exception:
            pass

    def schedule_native_window_style_refresh(self, delay=20):
        if self._native_style_job is not None:
            try:
                self.after_cancel(self._native_style_job)
            except Exception:
                pass

        self._native_style_job = self.after(delay, self.apply_native_window_style)

    def get_windowed_geometry(self):
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        width = min(max(1240, int(screen_w * 0.7)), max(1240, screen_w - 120))
        height = min(max(760, int(screen_h * 0.72)), max(760, screen_h - 110))
        x = max(20, (screen_w - width) // 2)
        y = max(20, (screen_h - height) // 2)
        return width, height, x, y

    def apply_display_mode(self, mode, force=False):
        mode = "maximized" if str(mode).strip().lower() in ["maximized", "zoomed"] else "windowed"
        if not force and self.display_mode == mode:
            return

        self.display_mode = mode

        if mode == "maximized":
            self.state("zoomed")
        else:
            self.state("normal")
            self.apply_windowed_geometry()

        self.schedule_native_window_style_refresh(delay=40)

    def toggle_display_mode(self):
        next_mode = "windowed" if self.display_mode == "maximized" else "maximized"
        self.apply_display_mode(next_mode)

    def apply_windowed_geometry(self):
        width, height, x, y = self.get_windowed_geometry()
        self.geometry(f"{width}x{height}+{x}+{y}")

    def show_splash(self):
        self.splash = SplashScreen(self)
        self.splash.after(2200, self.start_main_window)

    def start_main_window(self):
        if hasattr(self, "splash") and self.splash.winfo_exists():
            self.splash.destroy()

        self.deiconify()
        self.set_app_icon()
        self.after(180, self.set_app_icon)
        self.schedule_native_window_style_refresh(delay=60)
        self.show_login()
        self.after(350, self.start_app_update_check)

    def show_login(self):
        self.clear_window()
        self.main_page = None
        login_page = LoginPage(self, self.handle_login_success)
        login_page.pack(fill="both", expand=True)

    def handle_login_success(self, user):
        self.current_user = user
        self.show_main_app()

    def handle_logout(self):
        self.current_user = None
        self.show_login()

    def show_main_app(self):
        self.clear_window()
        main_page = MainAppPage(self, self.handle_logout, self.current_user)
        main_page.pack(fill="both", expand=True)
        self.main_page = main_page

    def start_app_update_check(self):
        if self._update_check_started:
            return

        self._update_check_started = True
        self._start_update_check(manual=False)

    def _start_update_check(self, manual=False):
        if self._update_check_in_progress:
            return

        self._update_check_in_progress = True
        self.notify_update_state_changed()
        threading.Thread(target=self._run_update_check, args=(manual,), daemon=True).start()

    def _run_update_check(self, manual=False):
        result = check_for_app_update()
        self.after(0, lambda: self.handle_update_check_result(result, manual=manual))

    def handle_update_check_result(self, result, manual=False):
        if not self.winfo_exists():
            return

        self._update_check_in_progress = False
        self._update_last_result = result
        if result.get("success"):
            self._update_info = result
        self.notify_update_state_changed()

        if not result.get("success"):
            if manual:
                messagebox.showerror(
                    "App Update",
                    result.get("message", "Khong kiem tra duoc ban cap nhat."),
                )
            return

        if not result.get("update_available"):
            if manual:
                messagebox.showinfo("App Update", "Khong co cap nhat moi.")
            return

        if not manual:
            self.show_update_prompt(result)

    def get_update_state(self):
        update_info = self._update_info or {}
        current_version = get_current_app_version()
        latest_version = str(update_info.get("version", "") or "").strip()
        update_available = bool(update_info.get("update_available"))
        can_self_update = is_frozen_app()
        status_text = "Chua kiem tra update."

        if self._update_in_progress:
            status_text = "Dang cap nhat app..."
        elif self._update_check_in_progress:
            status_text = "Dang kiem tra ban moi..."
        elif update_available and latest_version:
            status_text = f"Co ban moi: {latest_version}"
        elif self._update_last_result:
            if self._update_last_result.get("success"):
                status_text = ""
            else:
                status_text = self._update_last_result.get("message", "Khong kiem tra duoc update.")

        return {
            "current_version": current_version,
            "latest_version": latest_version,
            "update_available": update_available,
            "check_in_progress": self._update_check_in_progress,
            "update_in_progress": self._update_in_progress,
            "can_self_update": can_self_update,
            "mandatory": bool(update_info.get("mandatory")),
            "status_text": status_text,
        }

    def notify_update_state_changed(self):
        try:
            if self.main_page is not None and self.main_page.winfo_exists():
                self.main_page.refresh_update_settings_card()
        except Exception:
            pass

    def check_for_updates_from_settings(self):
        self._update_check_started = True
        self._start_update_check(manual=True)

    def start_cached_update_from_settings(self):
        if self._update_info and self._update_info.get("update_available"):
            self.begin_app_update()
            return

        self.check_for_updates_from_settings()

    def show_update_prompt(self, update_info):
        if self._update_dialog and self._update_dialog.winfo_exists():
            return

        self._update_dialog = UpdatePromptDialog(
            self,
            update_info=update_info,
            on_update=self.begin_app_update,
            on_later=self.dismiss_update_prompt,
        )

    def dismiss_update_prompt(self):
        if self._update_dialog and self._update_dialog.winfo_exists():
            try:
                self._update_dialog.grab_release()
            except Exception:
                pass
            self._update_dialog.destroy()
        self._update_dialog = None

    def begin_app_update(self):
        if self._update_in_progress:
            return

        if not self._update_info:
            return

        precheck = ensure_update_can_start()
        if not precheck.get("success"):
            messagebox.showerror("App Update", precheck.get("message", "Khong the bat dau update."))
            if self._update_dialog and self._update_dialog.winfo_exists():
                self._update_dialog.set_error(precheck.get("message", "Khong the bat dau update."))
            return

        if not is_frozen_app():
            messagebox.showinfo("App Update", "Auto update chi hoat dong tren ban .exe da build.")
            return

        self._update_in_progress = True
        self.notify_update_state_changed()
        if self._update_dialog and self._update_dialog.winfo_exists():
            self._update_dialog.set_busy("Dang chuan bi tai ban cap nhat...")

        threading.Thread(target=self._download_and_apply_update, daemon=True).start()

    def _download_and_apply_update(self):
        result = download_update_package(
            self._update_info,
            progress_callback=lambda downloaded, total: self.after(
                0,
                lambda: self._update_dialog
                and self._update_dialog.winfo_exists()
                and self._update_dialog.set_progress(downloaded, total),
            ),
        )
        if not result.get("success"):
            self.after(0, lambda: self.handle_update_failure(result))
            return

        apply_result = launch_self_update(result.get("download_path"))
        if not apply_result.get("success"):
            self.after(0, lambda: self.handle_update_failure(apply_result))
            return

        self.after(0, lambda: self.handle_update_success(apply_result))

    def handle_update_failure(self, result):
        self._update_in_progress = False
        self.notify_update_state_changed()
        message = result.get("message", "Update failed.")
        if self._update_dialog and self._update_dialog.winfo_exists():
            self._update_dialog.set_error(message)
        messagebox.showerror("App Update", message)

    def handle_update_success(self, result):
        message = result.get("message", "Dang cap nhat app...")
        if self._update_dialog and self._update_dialog.winfo_exists():
            self._update_dialog.set_completed(message)
        self.after(500, self.destroy)


if __name__ == "__main__":
    app = App()
    app.mainloop()
