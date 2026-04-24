import os
import tkinter as tk

from PIL import Image, ImageTk

from utils.resource_utils import get_data_path


class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.transparent_color = "#010203"
        self.splash_photo = None
        self.configure(bg=self.transparent_color)
        self.title("")
        self.resizable(False, False)
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        splash_path = get_data_path("home.png")
        fallback_logo_path = get_data_path("icon.png")
        splash_size = (846, 295)

        try:
            self.wm_attributes("-transparentcolor", self.transparent_color)
        except Exception:
            self.transparent_color = "#000000"
            self.configure(bg=self.transparent_color)

        if os.path.exists(splash_path):
            try:
                splash_image = self.load_image_fit(splash_path, 846, 295)
                splash_size = splash_image.size
                self.splash_photo = ImageTk.PhotoImage(splash_image)
            except Exception:
                self.splash_photo = None
        elif os.path.exists(fallback_logo_path):
            try:
                splash_image = self.load_image_fit(fallback_logo_path, 132, 132)
                splash_size = splash_image.size
                self.splash_photo = ImageTk.PhotoImage(splash_image)
            except Exception:
                pass

        self.update_idletasks()
        width, height = splash_size
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        if self.splash_photo is not None:
            splash_label = tk.Label(
                self,
                image=self.splash_photo,
                bg=self.transparent_color,
                bd=0,
                highlightthickness=0,
            )
            splash_label.place(x=0, y=0, width=width, height=height)
        else:
            fallback = tk.Label(
                self,
                text="DA",
                font=("Segoe UI", 42, "bold"),
                fg="#8b5e1a",
                bg=self.transparent_color,
                bd=0,
                highlightthickness=0,
            )
            fallback.place(relx=0.5, rely=0.5, anchor="center")

        self.deiconify()
        self.lift()
        self.update()

    def load_image_fit(self, path, max_width, max_height):
        image = Image.open(path).convert("RGBA")
        width, height = image.size
        scale = min(max_width / width, max_height / height)
        size = (max(1, int(width * scale)), max(1, int(height * scale)))
        if size != image.size:
            image = image.resize(size, Image.Resampling.LANCZOS)
        return image
