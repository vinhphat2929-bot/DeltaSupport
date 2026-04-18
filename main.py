import os
import ctypes
import customtkinter as ctk
from PIL import Image, ImageTk

from pages.login_page import LoginPage
from main_app import MainAppPage
from splash_screen import SplashScreen

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

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


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.current_user = None
        self.display_mode = "windowed"
        self._native_style_job = None

        self.title("Delta Assistant")
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.set_app_icon()
        self.apply_display_mode("windowed", force=True)
        self.after(150, self.schedule_native_window_style_refresh)

        self.withdraw()
        self.after(100, self.show_splash)

    def get_base_path(self):
        return os.path.dirname(os.path.abspath(__file__))

    def set_app_icon(self):
        base_path = self.get_base_path()
        icon_path = os.path.join(base_path, "data", "app.ico")

        if not os.path.exists(icon_path):
            print(f"Không tìm thấy icon: {icon_path}")
            return

        try:
            icon_image = Image.open(icon_path)
            icon_photo = ImageTk.PhotoImage(icon_image)
            self.iconphoto(True, icon_photo)
            self._icon_photo = icon_photo
        except Exception as e:
            print("Không load được icon:", e)

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
        self.schedule_native_window_style_refresh(delay=60)
        self.show_login()

    def show_login(self):
        self.clear_window()
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


if __name__ == "__main__":
    app = App()
    app.mainloop()
