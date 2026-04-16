# pages/pos_page.py

import json
import os
import customtkinter as ctk


# ===== LUXURY THEME =====
BG_PANEL = "#1a1210"
BG_CARD = "#241814"

BORDER = "#6f4b1f"
BORDER_SOFT = "#8a6330"

TEXT_MAIN = "#f4e7c1"
TEXT_SUB = "#bfa36a"
TEXT_MUTED = "#d8c39a"

BTN_PRIMARY = "#8b5a1e"
BTN_PRIMARY_HOVER = "#b07a2a"

INPUT_BG = "#f6ead2"
INPUT_TEXT = "#16110f"


class POSPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.data = self.load_data()
        self.filtered_data = self.data.copy()
        self.selected_button = None
        self.selected_keyword = None

        self.build_ui()

    def get_base_path(self):
        return os.path.dirname(os.path.abspath(__file__))

    def load_data(self):
        base_path = self.get_base_path()
        file_path = os.path.join(base_path, "..", "data", "pos.json")

        if not os.path.exists(file_path):
            print("Không tìm thấy pos.json:", file_path)
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            print("Lỗi đọc pos.json:", e)
            return []

    def build_ui(self):
        # ===== MAIN LAYOUT =====
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ===== SIDEBAR =====
        self.sidebar = ctk.CTkFrame(
            self,
            width=280,
            fg_color=BG_CARD,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
        )
        self.sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 10), pady=4)
        self.sidebar.grid_propagate(False)

        self.search_entry = ctk.CTkEntry(
            self.sidebar,
            placeholder_text="Search...",
            height=36,
            fg_color="#1b1310",
            text_color=TEXT_MAIN,
            border_color=BORDER_SOFT,
        )
        self.search_entry.pack(fill="x", padx=12, pady=(12, 8))
        self.search_entry.bind("<KeyRelease>", self.filter_list)

        self.list_frame = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
        )
        self.list_frame.pack(fill="both", expand=True, padx=6, pady=(0, 8))

        # ===== CONTENT =====
        self.content = ctk.CTkFrame(
            self,
            fg_color=BG_CARD,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
        )
        self.content.grid(row=0, column=1, sticky="nsew", pady=4)

        self.content.grid_rowconfigure(1, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.content,
            text="Chọn một mục",
            font=("Segoe UI", 22, "bold"),
            text_color=TEXT_MAIN,
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=20, pady=(16, 6))

        self.detail_box = ctk.CTkTextbox(
            self.content,
            font=("Segoe UI", 14),
            text_color=TEXT_MUTED,
            fg_color="#1b1310",
            border_color=BORDER_SOFT,
        )
        self.detail_box.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 16))
        self.detail_box.insert("1.0", "Chọn một mục bên trái để xem nội dung.")
        self.detail_box.configure(state="disabled")

        self.render_list()

    def render_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        for item in self.filtered_data:
            keyword = item.get("keyword", "No name")

            default_color = "#1b1310"
            selected_color = "#3a2418"

            btn = ctk.CTkButton(
                self.list_frame,
                text=keyword,
                anchor="w",
                height=36,
                fg_color=(
                    selected_color
                    if keyword == self.selected_keyword
                    else default_color
                ),
                hover_color="#2a1b14",
                text_color=TEXT_MAIN,
                border_width=0,
            )
            btn.pack(fill="x", padx=6, pady=2)
            btn.configure(command=lambda x=item, b=btn: self.select_item(x, b))

    def select_item(self, item, button):
        if self.selected_button:
            self.selected_button.configure(fg_color="#1b1310")

        button.configure(fg_color="#3a2418")
        self.selected_button = button
        self.selected_keyword = item.get("keyword")

        self.show_detail(item)

    def show_detail(self, item):
        self.title_label.configure(text=item.get("keyword", ""))

        self.detail_box.configure(state="normal")
        self.detail_box.delete("1.0", "end")
        self.detail_box.insert("1.0", item.get("content", "Không có nội dung."))
        self.detail_box.configure(state="disabled")

    def filter_list(self, event=None):
        keyword = self.search_entry.get().strip().lower()

        if not keyword:
            self.filtered_data = self.data.copy()
        else:
            self.filtered_data = [
                item for item in self.data if keyword in item.get("keyword", "").lower()
            ]

        self.selected_button = None
        self.selected_keyword = None
        self.render_list()

        self.title_label.configure(text="Chọn một mục")
        self.detail_box.configure(state="normal")
        self.detail_box.delete("1.0", "end")
        self.detail_box.insert("1.0", "Chọn một mục bên trái để xem nội dung.")
        self.detail_box.configure(state="disabled")
