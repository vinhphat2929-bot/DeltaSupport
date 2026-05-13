# pages/pin_verify_dialog.py

import customtkinter as ctk

from utils.window_icon_utils import apply_app_window_icon


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
    def __init__(
        self,
        master=None,
        title="Enter 4-digit PIN",
        on_success=None,
        digits=4,
        message_text="",
        secondary_text="",
        on_secondary=None,
    ):
        super().__init__(master)

        self.title(title)
        self.geometry("430x780")
        self.minsize(430, 780)
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)
        apply_app_window_icon(self, master)

        self.transient(master)
        self.lift()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))

        self.pin_value = ""
        self.digits = digits
        self.on_success = on_success
        self.on_secondary = on_secondary

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

        self.message_label = None
        if message_text:
            self.message_label = ctk.CTkLabel(
                container,
                text=message_text,
                font=ctk.CTkFont(size=13),
                text_color=TEXT_SUB,
                wraplength=330,
                justify="center",
            )
            self.message_label.pack(pady=(0, 12))

        self.display_label = ctk.CTkLabel(
            container,
            text=" ".join(["○"] * self.digits),
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color=TEXT_SUB,
        )
        self.display_label.pack(pady=(0, 20))

        keypad = ctk.CTkFrame(container, fg_color="transparent")
        keypad.pack(pady=(12, 12))

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
                width=108,
                height=82,
                corner_radius=16,
                fg_color=fg,
                hover_color=hover,
                text_color=TEXT_MAIN,
                font=ctk.CTkFont(size=20, weight="bold"),
                command=lambda t=text: self.on_key_press(t),
            )
            btn.grid(row=row, column=col, padx=8, pady=8)

        action_row = ctk.CTkFrame(container, fg_color="transparent", height=88)
        action_row.pack(fill="x", padx=20, pady=(18, 26))
        action_row.pack_propagate(False)

        column_count = 3 if secondary_text and on_secondary else 2
        for col in range(column_count):
            action_row.grid_columnconfigure(col, weight=1)

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

        next_column = 1
        if secondary_text and on_secondary:
            secondary_btn = ctk.CTkButton(
                action_row,
                text=secondary_text,
                height=56,
                corner_radius=14,
                fg_color=BG_BTN,
                hover_color=BG_BTN_HOVER,
                text_color=TEXT_MAIN,
                font=ctk.CTkFont(size=16, weight="bold"),
                command=self.on_secondary,
            )
            secondary_btn.grid(row=0, column=1, sticky="nsew", padx=8)
            next_column = 2

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
        confirm_btn.grid(row=0, column=next_column, sticky="nsew", padx=(8, 0))

    def on_key_press(self, key):
        if key == "Clear":
            self.pin_value = ""
        elif key == "⌫":
            self.pin_value = self.pin_value[:-1]
        else:
            if len(self.pin_value) < self.digits:
                self.pin_value += key

        self.update_display()

    def update_display(self):
        circles = ["●" if i < len(self.pin_value) else "○" for i in range(self.digits)]
        self.display_label.configure(text=" ".join(circles))

    def confirm_pin(self):
        if len(self.pin_value) != self.digits:
            return

        if self.on_success:
            self.on_success(self.pin_value)

    def set_dialog_title(self, new_title):
        self.title(new_title)
        self.title_label.configure(text=new_title)

    def set_message(self, message_text):
        if self.message_label is None:
            self.message_label = ctk.CTkLabel(
                self.title_label.master,
                text=message_text,
                font=ctk.CTkFont(size=13),
                text_color=TEXT_SUB,
                wraplength=330,
                justify="center",
            )
            self.message_label.pack(pady=(0, 12), after=self.title_label)
            return

        self.message_label.configure(text=message_text)

    def set_input_mode(self, title, digits, message_text=""):
        self.digits = digits
        self.pin_value = ""
        self.set_dialog_title(title)
        self.set_message(message_text)
        self.update_display()
