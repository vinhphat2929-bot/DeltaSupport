import os
import customtkinter as ctk
from PIL import Image
from utils.resource_utils import get_data_path


class SplashScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Delta One")
        self.geometry("440x320")
        self.resizable(False, False)
        self.configure(fg_color="#1a1210")
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        self.logo_image = None

        self.update_idletasks()
        width = 440
        height = 320
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        container = ctk.CTkFrame(
            self,
            fg_color="#1a1210",
            corner_radius=24,
            border_width=1,
            border_color="#6f4b1f"
        )
        container.pack(fill="both", expand=True, padx=2, pady=2)

        logo_path = get_data_path("logo_mark_v3.png")
        fallback_logo_path = get_data_path("logo.png")
        if os.path.exists(logo_path):
            try:
                self.logo_image = self.load_image_fit(logo_path, 200, 120)
                logo_label = ctk.CTkLabel(container, image=self.logo_image, text="")
                logo_label.pack(pady=(30, 12))
            except Exception:
                fallback = ctk.CTkLabel(
                    container,
                    text="DA",
                    font=ctk.CTkFont(size=42, weight="bold"),
                    text_color="#f4e7c1"
                )
                fallback.pack(pady=(35, 15))
        elif os.path.exists(fallback_logo_path):
            try:
                self.logo_image = self.load_image_fit(fallback_logo_path, 200, 120)
                logo_label = ctk.CTkLabel(container, image=self.logo_image, text="")
                logo_label.pack(pady=(30, 12))
            except Exception:
                pass

        title = ctk.CTkLabel(
            container,
            text="Delta One",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#f4e7c1"
        )
        title.pack()

        subtitle = ctk.CTkLabel(
            container,
            text="Loading...",
            font=ctk.CTkFont(size=13),
            text_color="#bfa36a"
        )
        subtitle.pack(pady=(8, 16))

        self.progress = ctk.CTkProgressBar(
            container,
            width=220,
            height=10,
            corner_radius=10,
            fg_color="#3a2a1e",
            progress_color="#c89b3c"
        )
        self.progress.pack()
        self.progress.start()

    def load_image_fit(self, path, max_width, max_height):
        image = Image.open(path)
        width, height = image.size
        scale = min(max_width / width, max_height / height)
        size = (max(1, int(width * scale)), max(1, int(height * scale)))
        return ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=size,
        )
