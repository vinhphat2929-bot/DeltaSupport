import customtkinter as ctk


BG_MAIN = "#1a1210"
BG_PANEL = "#2a1d18"
BORDER = "#6f4b1f"
TEXT_MAIN = "#f4e7c1"
TEXT_SUB = "#d8c2a8"
BTN_PRIMARY = "#a36a1f"
BTN_PRIMARY_HOVER = "#c8892c"
BTN_SECONDARY = "#3a241a"
BTN_SECONDARY_HOVER = "#5a3726"


class UpdatePromptDialog(ctk.CTkToplevel):
    def __init__(self, master, update_info, on_update, on_later):
        super().__init__(master)

        self.update_info = update_info or {}
        self.on_update = on_update
        self.on_later = on_later

        self.title("App Update")
        self.geometry("560x360")
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)
        self.transient(master)
        self.lift()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))
        self.protocol("WM_DELETE_WINDOW", self.handle_later)
        self.grab_set()

        container = ctk.CTkFrame(
            self,
            fg_color=BG_PANEL,
            corner_radius=20,
            border_width=1,
            border_color=BORDER,
        )
        container.pack(fill="both", expand=True, padx=16, pady=16)

        title_label = ctk.CTkLabel(
            container,
            text="Co ban cap nhat moi",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=TEXT_MAIN,
        )
        title_label.pack(pady=(24, 10))

        current_version = str(self.update_info.get("current_version", "") or "").strip()
        latest_version = str(self.update_info.get("version", "") or "").strip()
        subtitle_text = f"Current: {current_version or '-'}    New: {latest_version or '-'}"
        subtitle_label = ctk.CTkLabel(
            container,
            text=subtitle_text,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f0d0a0",
        )
        subtitle_label.pack()

        release_notes = str(self.update_info.get("release_notes", "") or "").strip()
        if not release_notes:
            release_notes = "Ban moi da san sang. Ban muon update ngay bay gio hay de sau?"

        notes_label = ctk.CTkLabel(
            container,
            text=release_notes,
            wraplength=470,
            justify="left",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_SUB,
        )
        notes_label.pack(fill="x", padx=28, pady=(18, 12))

        self.status_label = ctk.CTkLabel(
            container,
            text="",
            wraplength=470,
            justify="center",
            font=ctk.CTkFont(size=13),
            text_color="#f0d0a0",
        )
        self.status_label.pack(fill="x", padx=28, pady=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(
            container,
            height=12,
            corner_radius=12,
            fg_color="#3c2b22",
            progress_color="#c58b42",
        )
        self.progress_bar.pack(fill="x", padx=28, pady=(6, 16))
        self.progress_bar.set(0)

        action_row = ctk.CTkFrame(container, fg_color="transparent")
        action_row.pack(fill="x", padx=28, pady=(4, 24))
        action_row.grid_columnconfigure(0, weight=1)
        action_row.grid_columnconfigure(1, weight=1)

        self.later_button = ctk.CTkButton(
            action_row,
            text="Later",
            height=48,
            corner_radius=14,
            fg_color=BTN_SECONDARY,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.handle_later,
        )
        self.later_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.update_button = ctk.CTkButton(
            action_row,
            text="UPDATE",
            height=48,
            corner_radius=14,
            fg_color=BTN_PRIMARY,
            hover_color=BTN_PRIMARY_HOVER,
            text_color="#2a1d18",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.handle_update,
        )
        self.update_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        if bool(self.update_info.get("mandatory")):
            self.later_button.configure(state="disabled")
            self.status_label.configure(text="Ban nay bat buoc update truoc khi tiep tuc.")

    def handle_later(self):
        if bool(self.update_info.get("mandatory")):
            return
        if callable(self.on_later):
            self.on_later()

    def handle_update(self):
        if callable(self.on_update):
            self.on_update()

    def set_busy(self, message):
        self.status_label.configure(text=message)
        self.update_button.configure(state="disabled")
        if not bool(self.update_info.get("mandatory")):
            self.later_button.configure(state="disabled")

    def set_progress(self, downloaded_bytes, total_bytes):
        if total_bytes > 0:
            self.progress_bar.set(min(1, downloaded_bytes / total_bytes))
            downloaded_mb = downloaded_bytes / (1024 * 1024)
            total_mb = total_bytes / (1024 * 1024)
            self.status_label.configure(
                text=f"Dang tai ban cap nhat... {downloaded_mb:.1f}/{total_mb:.1f} MB"
            )
        else:
            self.progress_bar.set(0)
            self.status_label.configure(text="Dang tai ban cap nhat...")

    def set_error(self, message):
        self.status_label.configure(text=message)
        self.update_button.configure(state="normal")
        if not bool(self.update_info.get("mandatory")):
            self.later_button.configure(state="normal")

    def set_completed(self, message):
        self.progress_bar.set(1)
        self.status_label.configure(text=message)
        self.update_button.configure(state="disabled")
        self.later_button.configure(state="disabled")
