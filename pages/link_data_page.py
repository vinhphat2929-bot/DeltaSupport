import os
import json
import webbrowser
import customtkinter as ctk
from tkinter import messagebox


# ===== LUXURY THEME =====
BG_MAIN = "#0f0b0a"
BG_PANEL = "#1a1210"
BG_CARD = "#241814"

BORDER = "#6f4b1f"
BORDER_SOFT = "#8a6330"

TEXT_MAIN = "#f4e7c1"
TEXT_SUB = "#bfa36a"
TEXT_MUTED = "#d8c39a"

BTN_PRIMARY = "#8b5a1e"
BTN_PRIMARY_HOVER = "#b07a2a"

BTN_DARK = "#2c1d14"
BTN_DARK_HOVER = "#4a2f1d"

INPUT_BG = "#f6ead2"
INPUT_TEXT = "#16110f"


class LinkDataPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.data_file = self.get_data_path()
        self.items = self.load_data()
        self.filtered_items = self.items.copy()

        self.selected_button = None
        self.selected_title = None
        self.current_item = None
        self.single_value_visible = False

        self.build_ui()

    def get_data_path(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, "..", "data", "link_data.json")

    def load_data(self):
        if not os.path.exists(self.data_file):
            return []

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
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

        self.content.grid_rowconfigure(2, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.content,
            text="Chọn một mục",
            font=("Segoe UI", 22, "bold"),
            text_color=TEXT_MAIN,
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=20, pady=(16, 6))

        self.top_action_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.top_action_frame.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))

        self.copy_button = ctk.CTkButton(
            self.top_action_frame,
            text="Copy",
            width=90,
            height=34,
            corner_radius=10,
            fg_color=BTN_DARK,
            hover_color=BTN_DARK_HOVER,
            text_color="white",
            command=self.copy_current_value,
        )
        self.copy_button.pack(side="left", padx=(0, 8))

        self.open_button = ctk.CTkButton(
            self.top_action_frame,
            text="Open",
            width=90,
            height=34,
            corner_radius=10,
            fg_color=BTN_PRIMARY,
            hover_color=BTN_PRIMARY_HOVER,
            text_color="white",
            command=self.open_current_value,
        )
        self.open_button.pack(side="left", padx=(0, 8))

        self.toggle_button = ctk.CTkButton(
            self.top_action_frame,
            text="Show",
            width=90,
            height=34,
            corner_radius=10,
            fg_color=BTN_DARK,
            hover_color=BTN_DARK_HOVER,
            text_color="white",
            command=self.toggle_single_value,
        )
        self.toggle_button.pack(side="left")

        self.detail_container = ctk.CTkFrame(
            self.content,
            fg_color="#1b1310",
            corner_radius=12,
            border_width=1,
            border_color=BORDER_SOFT,
        )
        self.detail_container.grid(
            row=2, column=0, sticky="nsew", padx=20, pady=(0, 16)
        )
        self.detail_container.grid_rowconfigure(0, weight=1)
        self.detail_container.grid_columnconfigure(0, weight=1)

        self.render_placeholder()
        self.render_list()

    def render_placeholder(self):
        for widget in self.detail_container.winfo_children():
            widget.destroy()

        placeholder = ctk.CTkLabel(
            self.detail_container,
            text="Chọn một mục bên trái để xem nội dung.",
            font=("Segoe UI", 14),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        placeholder.grid(row=0, column=0, sticky="nw", padx=16, pady=16)

        self.copy_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.toggle_button.configure(state="disabled", text="Show")

    def render_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        if not self.filtered_items:
            empty_label = ctk.CTkLabel(
                self.list_frame,
                text="Không có dữ liệu",
                text_color=TEXT_SUB,
                anchor="w",
            )
            empty_label.pack(fill="x", padx=8, pady=8)
            return

        for item in self.filtered_items:
            title = item.get("title", "No name")

            default_color = "#1b1310"
            selected_color = "#3a2418"

            btn = ctk.CTkButton(
                self.list_frame,
                text=title,
                anchor="w",
                height=40,
                fg_color=(
                    selected_color if title == self.selected_title else default_color
                ),
                hover_color="#2a1b14",
                text_color=TEXT_MAIN,
                corner_radius=10,
                border_width=0,
            )
            btn.pack(fill="x", padx=6, pady=3)
            btn.configure(command=lambda x=item, b=btn: self.select_item(x, b))

    def select_item(self, item, button):
        if self.selected_button:
            self.selected_button.configure(fg_color="#1b1310")

        button.configure(fg_color="#3a2418")
        self.selected_button = button
        self.selected_title = item.get("title")
        self.current_item = item
        self.single_value_visible = False

        self.show_detail(item)

    def show_detail(self, item):
        self.title_label.configure(text=item.get("title", ""))

        for widget in self.detail_container.winfo_children():
            widget.destroy()

        if "items" in item and isinstance(item["items"], list):
            self.copy_button.configure(state="normal")
            self.open_button.configure(state="disabled")
            self.toggle_button.configure(state="disabled", text="Show")
            self.render_multi_links(item["items"])
        else:
            value = item.get("value", "")
            is_link = isinstance(value, str) and value.startswith("http")

            self.copy_button.configure(state="normal" if value else "disabled")
            self.open_button.configure(state="normal" if is_link else "disabled")
            self.toggle_button.configure(
                state="normal" if value else "disabled", text="Show"
            )
            self.render_single_value_hidden()

    def render_single_value_hidden(self):
        for widget in self.detail_container.winfo_children():
            widget.destroy()

        hidden_label = ctk.CTkLabel(
            self.detail_container,
            text="Link đang được ẩn. Bấm Show để xem.",
            font=("Segoe UI", 14),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        hidden_label.grid(row=0, column=0, sticky="nw", padx=16, pady=16)

    def render_single_value_visible(self):
        for widget in self.detail_container.winfo_children():
            widget.destroy()

        value = self.current_item.get("value", "") if self.current_item else ""

        box = ctk.CTkTextbox(
            self.detail_container,
            font=("Segoe UI", 14),
            text_color=TEXT_MUTED,
            fg_color="#1b1310",
            corner_radius=12,
            border_width=0,
            wrap="word",
        )
        box.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        box.insert("1.0", value if value else "Không có nội dung.")
        box.configure(state="disabled")

    def toggle_single_value(self):
        if not self.current_item:
            return

        if "items" in self.current_item and isinstance(
            self.current_item["items"], list
        ):
            return

        self.single_value_visible = not self.single_value_visible

        if self.single_value_visible:
            self.toggle_button.configure(text="Hide")
            self.render_single_value_visible()
        else:
            self.toggle_button.configure(text="Show")
            self.render_single_value_hidden()

    def render_multi_links(self, items):
        list_wrap = ctk.CTkScrollableFrame(
            self.detail_container,
            fg_color="transparent",
        )
        list_wrap.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        list_wrap.grid_columnconfigure(0, weight=1)

        valid_items = [sub for sub in items if isinstance(sub, dict)]

        if not valid_items:
            empty_label = ctk.CTkLabel(
                list_wrap,
                text="Không có dữ liệu.",
                text_color=TEXT_MUTED,
                anchor="w",
            )
            empty_label.pack(fill="x", padx=6, pady=6)
            return

        for sub in valid_items:
            name = sub.get("name", "")
            value = sub.get("value", "")

            row_card = ctk.CTkFrame(
                list_wrap,
                fg_color=BG_CARD,
                corner_radius=12,
                border_width=1,
                border_color=BORDER,
            )
            row_card.pack(fill="x", padx=4, pady=6)

            top_row = ctk.CTkFrame(row_card, fg_color="transparent")
            top_row.pack(fill="x", padx=14, pady=(12, 8))

            name_label = ctk.CTkLabel(
                top_row,
                text=name if name else "Không có tên",
                font=("Segoe UI", 15, "bold"),
                text_color=TEXT_MAIN,
                anchor="w",
            )
            name_label.pack(side="left")

            value_box = ctk.CTkTextbox(
                row_card,
                height=70,
                font=("Segoe UI", 13),
                text_color=TEXT_MUTED,
                fg_color="#1b1310",
                corner_radius=10,
                border_width=1,
                border_color=BORDER_SOFT,
                wrap="word",
            )
            value_box.insert("1.0", value if value else "Không có nội dung.")
            value_box.configure(state="disabled")

            btn_row = ctk.CTkFrame(row_card, fg_color="transparent")
            btn_row.pack(anchor="w", padx=14, pady=(0, 12))

            is_link = isinstance(value, str) and value.startswith("http")

            copy_btn = ctk.CTkButton(
                btn_row,
                text="Copy",
                width=85,
                height=32,
                corner_radius=10,
                fg_color=BTN_DARK,
                hover_color=BTN_DARK_HOVER,
                text_color="white",
                command=lambda v=value: self.copy_value(v),
            )
            copy_btn.pack(side="left", padx=(0, 8))

            open_btn = ctk.CTkButton(
                btn_row,
                text="Open",
                width=85,
                height=32,
                corner_radius=10,
                fg_color=BTN_PRIMARY,
                hover_color=BTN_PRIMARY_HOVER,
                text_color="white",
                command=lambda v=value: self.open_link(v),
            )
            open_btn.pack(side="left", padx=(0, 8))

            show_btn = ctk.CTkButton(
                btn_row,
                text="Show",
                width=85,
                height=32,
                corner_radius=10,
                fg_color=BTN_DARK,
                hover_color=BTN_DARK_HOVER,
                text_color="white",
            )
            show_btn.pack(side="left")

            if not is_link:
                open_btn.configure(state="disabled")

            toggle_state = {"visible": False}

            def toggle_value(
                box=value_box,
                buttons=btn_row,
                btn=show_btn,
                state=toggle_state,
            ):
                state["visible"] = not state["visible"]

                if state["visible"]:
                    btn.configure(text="Hide")
                    box.pack(fill="x", padx=14, pady=(0, 10), before=buttons)
                else:
                    btn.configure(text="Show")
                    box.pack_forget()

            show_btn.configure(command=toggle_value)

    def filter_list(self, event=None):
        keyword = self.search_entry.get().strip().lower()

        if not keyword:
            self.filtered_items = self.items.copy()
        else:
            self.filtered_items = [
                item
                for item in self.items
                if keyword in item.get("title", "").lower()
                or keyword in json.dumps(item, ensure_ascii=False).lower()
            ]

        self.selected_button = None
        self.selected_title = None
        self.current_item = None
        self.single_value_visible = False

        self.render_list()
        self.title_label.configure(text="Chọn một mục")
        self.render_placeholder()

    def copy_current_value(self):
        if not self.current_item:
            messagebox.showwarning("Warning", "Chưa chọn mục nào.")
            return

        if "items" in self.current_item and isinstance(
            self.current_item["items"], list
        ):
            values = []
            for sub in self.current_item["items"]:
                name = sub.get("name", "")
                value = sub.get("value", "")
                values.append(f"{name}: {value}")
            text_to_copy = "\n".join(values)
        else:
            text_to_copy = self.current_item.get("value", "")

        if not text_to_copy:
            messagebox.showwarning("Warning", "Không có nội dung để copy.")
            return

        self.copy_value(text_to_copy)

    def open_current_value(self):
        if not self.current_item:
            messagebox.showwarning("Warning", "Chưa chọn mục nào.")
            return

        value = self.current_item.get("value", "")
        self.open_link(value)

    def copy_value(self, value):
        if not value:
            messagebox.showwarning("Warning", "Không có nội dung để copy.")
            return

        self.clipboard_clear()
        self.clipboard_append(value)
        messagebox.showinfo("Copied", "Đã copy")

    def open_link(self, value):
        if isinstance(value, str) and value.startswith("http"):
            webbrowser.open(value)
        else:
            messagebox.showwarning("Warning", "Không phải link hợp lệ.")
