import os
import customtkinter as ctk
from PIL import Image, ImageTk

from pages.login_page import LoginPage
from main_app import MainAppPage
from splash_screen import SplashScreen

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.current_user = None

        self.title("Delta Assistant")
        self.geometry("1100x650")
        self.minsize(1000, 600)

        self.set_app_icon()

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

    def show_splash(self):
        self.splash = SplashScreen(self)
        self.splash.after(2200, self.start_main_window)

    def start_main_window(self):
        if hasattr(self, "splash") and self.splash.winfo_exists():
            self.splash.destroy()

        self.deiconify()
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
