import customtkinter as ctk
import tempfile
from pathlib import Path

from PIL import Image, ImageTk

from utils.resource_utils import get_data_path
from utils.window_icon_utils import apply_app_window_icon


BG_MAIN = "#130f0d"
SURFACE = "#1d1714"
SURFACE_ELEVATED = "#241c18"
SURFACE_MUTED = "#2e241f"
BORDER = "#5f4633"
ACCENT = "#d6952d"
ACCENT_HOVER = "#e5a43a"
ACCENT_SOFT = "#f3d3a3"
TEXT_MAIN = "#f6ecd8"
TEXT_SUB = "#cdbdaa"
TEXT_MUTED = "#aa9785"
SUCCESS = "#8dd6b5"
ERROR = "#ff9d93"
BTN_SECONDARY = "#2c211c"
BTN_SECONDARY_HOVER = "#382922"


class UpdatePromptDialog(ctk.CTkToplevel):
    def __init__(self, master, update_info, on_update, on_later):
        super().__init__(master)

        self.update_info = update_info or {}
        self.on_update = on_update
        self.on_later = on_later
        self.logo_image = None
        self._icon_refs = []
        self._dialog_bitmap_icon_path = ""

        self.title("DELTA ONE Update")
        self.geometry("760x640")
        self.minsize(760, 640)
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)
        self.transient(master)
        self.lift()
        self.attributes("-topmost", True)
        self.after(260, lambda: self.attributes("-topmost", False))
        self.protocol("WM_DELETE_WINDOW", self.handle_later)
        self.grab_set()

        self._apply_window_icon(master)
        self._build_ui()
        self.after(80, lambda: self._apply_window_icon(master))
        self.after(260, lambda: self._apply_window_icon(master))
        self._center_over_master(master)

    def _apply_window_icon(self, master):
        self._dialog_bitmap_icon_path = apply_app_window_icon(self, master)
        return
        bitmap_icon_path = self._resolve_bitmap_icon_path(master)
        if bitmap_icon_path:
            try:
                self.iconbitmap(bitmap_icon_path)
            except Exception:
                pass
            try:
                self.iconbitmap(default=bitmap_icon_path)
            except Exception:
                pass

        icon_refs = list(getattr(master, "_icon_photo", []) or [])
        if not icon_refs:
            icon_refs = self._load_titlebar_icon_refs()
        if icon_refs:
            try:
                self.iconphoto(True, *icon_refs)
                self._icon_refs = icon_refs
            except Exception:
                pass

    def _resolve_bitmap_icon_path(self, master):
        if self._dialog_bitmap_icon_path:
            return self._dialog_bitmap_icon_path

        for filename in ("logo-goc.png", "app_v3.png", "logo.png", "icon.png"):
            source_path = Path(get_data_path(filename))
            if not source_path.exists():
                continue
            generated_icon_path = Path(tempfile.gettempdir()) / "DeltaOne" / "update_dialog.ico"
            try:
                generated_icon_path.parent.mkdir(parents=True, exist_ok=True)
                with Image.open(source_path) as source_image:
                    icon_image = source_image.convert("RGBA")
                icon_image.thumbnail((256, 256), Image.Resampling.LANCZOS)
                square_icon = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
                offset = (
                    (256 - icon_image.width) // 2,
                    (256 - icon_image.height) // 2,
                )
                square_icon.alpha_composite(icon_image, offset)
                square_icon.save(
                    generated_icon_path,
                    format="ICO",
                    sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
                )
                self._dialog_bitmap_icon_path = str(generated_icon_path)
                return self._dialog_bitmap_icon_path
            except Exception:
                continue

        bitmap_icon_path = str(getattr(master, "_bitmap_icon_path", "") or "").strip()
        if bitmap_icon_path:
            return bitmap_icon_path

        for filename in ("app_v3.ico", "app.ico"):
            candidate = get_data_path(filename)
            if candidate and Path(candidate).exists():
                self._dialog_bitmap_icon_path = candidate
                return candidate

        return ""

    def _load_titlebar_icon_refs(self):
        for filename in ("app_v3.png", "logo.png", "icon.png"):
            file_path = Path(get_data_path(filename))
            if not file_path.exists():
                continue
            try:
                with Image.open(file_path) as icon_image:
                    refs = []
                    for icon_size in (256, 128, 64, 48, 32, 16):
                        resized = icon_image.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                        refs.append(ImageTk.PhotoImage(resized))
                    return refs
            except Exception:
                continue
        return []

    def _center_over_master(self, master):
        self.update_idletasks()
        try:
            master_x = master.winfo_rootx()
            master_y = master.winfo_rooty()
            master_w = max(master.winfo_width(), 1)
            master_h = max(master.winfo_height(), 1)
            width = self.winfo_width()
            height = self.winfo_height()
            pos_x = max(20, master_x + (master_w - width) // 2)
            pos_y = max(20, master_y + (master_h - height) // 2)
            self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        except Exception:
            pass

    def _load_logo_image(self):
        for filename in ("app_v3.png", "logo.png", "icon.png"):
            file_path = get_data_path(filename)
            try:
                image = Image.open(file_path).convert("RGBA")
                self.logo_image = ctk.CTkImage(light_image=image, dark_image=image, size=(72, 72))
                return self.logo_image
            except Exception:
                continue
        return None

    def _build_release_notes(self):
        release_notes = str(self.update_info.get("release_notes", "") or "").strip()
        if release_notes:
            return release_notes
        return (
            "A new build is ready to install. The app will close and reopen "
            "automatically after the update finishes."
        )

    def _build_version_card(self, parent, title, value, accent=False):
        card = ctk.CTkFrame(
            parent,
            fg_color=SURFACE_MUTED if not accent else "#2f2218",
            corner_radius=14,
            border_width=1,
            border_color="#4d392c" if not accent else "#7b5829",
        )
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_MUTED,
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 2))

        ctk.CTkLabel(
            card,
            text=value or "-",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=ACCENT_SOFT if accent else TEXT_MAIN,
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))

        return card

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(
            shell,
            fg_color=SURFACE,
            corner_radius=24,
            border_width=1,
            border_color=BORDER,
        )
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=0)
        container.grid_rowconfigure(1, weight=0)
        container.grid_rowconfigure(2, weight=1)
        container.grid_rowconfigure(3, weight=0)

        accent_bar = ctk.CTkFrame(
            container,
            fg_color=ACCENT,
            height=4,
            corner_radius=999,
        )
        accent_bar.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 0))

        content = ctk.CTkFrame(container, fg_color="transparent")
        content.grid(row=1, column=0, sticky="ew", padx=24, pady=(18, 0))
        content.grid_columnconfigure(0, weight=0)
        content.grid_columnconfigure(1, weight=1)

        branding_card = ctk.CTkFrame(
            content,
            fg_color=SURFACE_ELEVATED,
            corner_radius=22,
            border_width=1,
            border_color="#4d392c",
            width=148,
            height=148,
        )
        branding_card.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 18))
        branding_card.grid_propagate(False)

        logo_image = self._load_logo_image()
        logo_label = ctk.CTkLabel(
            branding_card,
            text="",
            image=logo_image,
        )
        if logo_image is None:
            logo_label.configure(
                text="D1",
                font=ctk.CTkFont(size=28, weight="bold"),
                text_color=ACCENT_SOFT,
            )
        logo_label.pack(pady=(20, 10))

        ctk.CTkLabel(
            branding_card,
            text="DELTA ONE",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_MAIN,
        ).pack()

        ctk.CTkLabel(
            branding_card,
            text="Updater",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        ).pack(pady=(2, 0))

        header_wrap = ctk.CTkFrame(content, fg_color="transparent")
        header_wrap.grid(row=0, column=1, sticky="new")
        header_wrap.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_wrap,
            text="Update Available",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=TEXT_MAIN,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header_wrap,
            text="A newer build is ready to download and install.",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SUB,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        current_version = str(self.update_info.get("current_version", "") or "").strip()
        latest_version = str(self.update_info.get("version", "") or "").strip()

        version_row = ctk.CTkFrame(content, fg_color="transparent")
        version_row.grid(row=1, column=1, sticky="ew", pady=(18, 0))
        version_row.grid_columnconfigure(0, weight=1)
        version_row.grid_columnconfigure(1, weight=1)

        self._build_version_card(version_row, "Current version", current_version).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 8),
        )
        self._build_version_card(version_row, "New version", latest_version, accent=True).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(8, 0),
        )

        notes_card = ctk.CTkFrame(
            container,
            fg_color=SURFACE_ELEVATED,
            corner_radius=20,
            border_width=1,
            border_color="#493629",
        )
        notes_card.grid(row=2, column=0, sticky="nsew", padx=24, pady=(22, 14))
        notes_card.grid_columnconfigure(0, weight=1)
        notes_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            notes_card,
            text="Release Notes",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=ACCENT_SOFT,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 10))

        self.notes_box = ctk.CTkTextbox(
            notes_card,
            fg_color="#1f1815",
            border_width=1,
            border_color="#433228",
            corner_radius=16,
            text_color=TEXT_SUB,
            font=ctk.CTkFont(size=13),
            wrap="word",
        )
        self.notes_box.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))
        self.notes_box.insert("1.0", self._build_release_notes())
        self.notes_box.configure(state="disabled")

        footer = ctk.CTkFrame(container, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 20))
        footer.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            footer,
            text="The app will restart automatically after the update completes.",
            wraplength=600,
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_MUTED,
        )
        self.status_label.grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(
            footer,
            height=12,
            corner_radius=999,
            fg_color="#362923",
            progress_color=ACCENT,
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        self.progress_bar.set(0)

        action_row = ctk.CTkFrame(footer, fg_color="transparent")
        action_row.grid(row=2, column=0, sticky="ew")
        action_row.grid_columnconfigure(0, weight=1)
        action_row.grid_columnconfigure(1, weight=1)

        self.later_button = ctk.CTkButton(
            action_row,
            text="Later",
            height=48,
            corner_radius=15,
            fg_color=BTN_SECONDARY,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.handle_later,
        )
        self.later_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.update_button = ctk.CTkButton(
            action_row,
            text="Update Now",
            height=48,
            corner_radius=15,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color="#261a14",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.handle_update,
        )
        self.update_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.update_button.focus_set()

        if bool(self.update_info.get("mandatory")):
            self.later_button.configure(state="disabled")
            self.status_label.configure(
                text="This update is required before you can continue.",
                text_color=ACCENT_SOFT,
            )

    def handle_later(self):
        if bool(self.update_info.get("mandatory")):
            return
        if callable(self.on_later):
            self.on_later()

    def handle_update(self):
        if callable(self.on_update):
            self.on_update()

    def set_busy(self, message):
        self.status_label.configure(text=message, text_color=TEXT_SUB)
        self.update_button.configure(state="disabled")
        if not bool(self.update_info.get("mandatory")):
            self.later_button.configure(state="disabled")

    def set_progress(self, downloaded_bytes, total_bytes):
        if total_bytes > 0:
            self.progress_bar.set(min(1, downloaded_bytes / total_bytes))
            downloaded_mb = downloaded_bytes / (1024 * 1024)
            total_mb = total_bytes / (1024 * 1024)
            self.status_label.configure(
                text=f"Downloading update... {downloaded_mb:.1f}/{total_mb:.1f} MB",
                text_color=TEXT_SUB,
            )
        else:
            self.progress_bar.set(0)
            self.status_label.configure(
                text="Downloading update...",
                text_color=TEXT_SUB,
            )

    def set_error(self, message):
        self.status_label.configure(text=message, text_color=ERROR)
        self.update_button.configure(state="normal")
        if not bool(self.update_info.get("mandatory")):
            self.later_button.configure(state="normal")

    def set_completed(self, message):
        self.progress_bar.set(1)
        self.status_label.configure(text=message, text_color=SUCCESS)
        self.update_button.configure(state="disabled")
        self.later_button.configure(state="disabled")
