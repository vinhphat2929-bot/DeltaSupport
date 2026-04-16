import os
import customtkinter as ctk
from PIL import Image


class SplashScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Delta Assistant")
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

        logo_path = os.path.join("data", "logo.png")
        if os.path.exists(logo_path):
            try:
                self.logo_image = ctk.CTkImage(
                    light_image=Image.open(logo_path),
                    dark_image=Image.open(logo_path),
                    size=(150, 150)
                )
                logo_label = ctk.CTkLabel(container, image=self.logo_image, text="")
                logo_label.pack(pady=(26, 10))
            except Exception:
                fallback = ctk.CTkLabel(
                    container,
                    text="DA",
                    font=ctk.CTkFont(size=42, weight="bold"),
                    text_color="#f4e7c1"
                )
                fallback.pack(pady=(35, 15))

        title = ctk.CTkLabel(
            container,
            text="Delta Assistant",
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