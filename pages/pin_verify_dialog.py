# pages/pin_verify_dialog.py

import customtkinter as ctk


BG_MAIN = "#1a0f0b"
BG_PANEL = "#2a1812"
BG_BTN = "#3a241a"
BG_BTN_HOVER = "#5a3726"
BG_CONFIRM = "#a36a1f"
BG_CONFIRM_HOVER = "#d4a64a"
BG_DANGER = "#8f3434"
BG_DANGER_HOVER = "#a84242"
BORDER = "#6f4b1f"
TEXT_MAIN = "#f4e7c1"
TEXT_SUB = "#d8c2a8"


class PinVerifyDialog(ctk.CTkToplevel):
    def __init__(self, master=None, title="Enter 4-digit PIN", on_success=None):
        super().__init__(master)

        self.title(title)
        self.geometry("390x660")
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)

        self.transient(master)
        self.lift()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))

        self.pin_value = ""
        self.on_success = on_success

        container = ctk.CTkFrame(
            self,
            fg_color=BG_PANEL,
            corner_radius=22,
            border_width=1,
            border_color=BORDER,
        )
        container.pack(fill="both", expand=True, padx=16, pady=16)

        self.title_label = ctk.CTkLabel(
            container,
            text=title,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=TEXT_MAIN,
        )
        self.title_label.pack(pady=(22, 12))

        self.display_label = ctk.CTkLabel(
            container,
            text="○ ○ ○ ○",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color=TEXT_SUB,
        )
        self.display_label.pack(pady=(0, 20))

        keypad = ctk.CTkFrame(container, fg_color="transparent")
        keypad.pack(pady=16)

        buttons = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "Clear", "0", "⌫"]

        for i, text in enumerate(buttons):
            row = i // 3
            col = i % 3

            if text == "Clear":
                fg = BG_DANGER
                hover = BG_DANGER_HOVER
            else:
                fg = BG_BTN
                hover = BG_BTN_HOVER

            btn = ctk.CTkButton(
                keypad,
                text=text,
                width=96,
                height=76,
                corner_radius=16,
                fg_color=fg,
                hover_color=hover,
                text_color=TEXT_MAIN,
                font=ctk.CTkFont(size=20, weight="bold"),
                command=lambda t=text: self.on_key_press(t),
            )
            btn.grid(row=row, column=col, padx=8, pady=8)

        action_row = ctk.CTkFrame(container, fg_color="transparent", height=80)
        action_row.pack(fill="x", padx=20, pady=(18, 22))
        action_row.pack_propagate(False)
        action_row.grid_columnconfigure(0, weight=1)
        action_row.grid_columnconfigure(1, weight=1)

        cancel_btn = ctk.CTkButton(
            action_row,
            text="Cancel",
            height=56,
            corner_radius=14,
            fg_color=BG_DANGER,
            hover_color=BG_DANGER_HOVER,
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.destroy,
        )
        cancel_btn.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        confirm_btn = ctk.CTkButton(
            action_row,
            text="Confirm",
            height=56,
            corner_radius=14,
            fg_color=BG_CONFIRM,
            hover_color=BG_CONFIRM_HOVER,
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.confirm_pin,
        )
        confirm_btn.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    def on_key_press(self, key):
        if key == "Clear":
            self.pin_value = ""
        elif key == "⌫":
            self.pin_value = self.pin_value[:-1]
        else:
            if len(self.pin_value) < 4:
                self.pin_value += key

        self.update_display()

    def update_display(self):
        circles = ["●" if i < len(self.pin_value) else "○" for i in range(4)]
        self.display_label.configure(text=" ".join(circles))

    def confirm_pin(self):
        if len(self.pin_value) != 4:
            return

        if self.on_success:
            self.on_success(self.pin_value)

    def set_dialog_title(self, new_title):
        self.title(new_title)
        self.title_label.configure(text=new_title)
