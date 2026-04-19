import tkinter as tk
import customtkinter as ctk

class ProcessLayout:
    def __init__(self, page):
        self.page = page

    def create_labeled_entry(self, parent, row, label_text, placeholder, text_dark, input_bg, input_border, width=None, state="normal"):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        wrap.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            wrap,
            text=label_text,
            font=("Segoe UI", 12, "bold"),
            text_color=text_dark,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        entry = ctk.CTkEntry(
            wrap,
            height=38,
            width=width if width is not None else 360,
            placeholder_text=placeholder,
            fg_color=input_bg,
            border_color=input_border,
            text_color=text_dark,
            state=state,
        )
        entry.grid(row=1, column=0, sticky="ew")
        return entry

    def create_section_label(self, parent, row, text, text_dark):
        ctk.CTkLabel(
            parent,
            text=text,
            font=("Segoe UI", 12, "bold"),
            text_color=text_dark,
        ).grid(row=row, column=0, sticky="w", padx=18, pady=(2, 6))

    def create_info_value(self, parent, row, column, label_text, text_dark, text_muted):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=column, sticky="ew", padx=12, pady=10)
        wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            wrap,
            text=label_text,
            font=("Segoe UI", 11, "bold"),
            text_color=text_dark,
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        value_label = ctk.CTkLabel(
            wrap,
            text="-",
            font=("Segoe UI", 11),
            text_color=text_muted,
            anchor="w",
            justify="left",
        )
        value_label.grid(row=1, column=0, sticky="ew")
        return value_label

    def build_main_layout(self, parent, colors, callbacks):
        """
        Dựng khung Search và Board chính đầy đủ widget cho ProcessPage
        """
        w = {}
        wrap = ctk.CTkFrame(parent, fg_color=colors["BG_PANEL_INNER"], corner_radius=18, border_width=1, border_color=colors["BORDER_SOFT"])
        wrap.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        wrap.grid_columnconfigure(0, weight=85)
        wrap.grid_columnconfigure(1, weight=15)
        wrap.grid_rowconfigure(1, weight=1)
        wrap.grid_rowconfigure(2, weight=1)
        w["follow_wrap"] = wrap

        # Top Card (Search/Filter)
        top_card = ctk.CTkFrame(wrap, fg_color="#fbf5ec", corner_radius=16, border_width=1, border_color="#e0c79d")
        top_card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 12))
        top_card.grid_columnconfigure(1, weight=1)
        top_card.grid_columnconfigure(7, weight=1)
        top_card.grid_columnconfigure(8, weight=1)
        w["follow_top_card"] = top_card

        ctk.CTkLabel(top_card, text="Search merchant", font=("Segoe UI", 12), text_color=colors["TEXT_MUTED"]).grid(row=0, column=0, sticky="w", padx=(18, 8), pady=16)
        w["search_entry"] = ctk.CTkEntry(top_card, width=240, height=34, placeholder_text="Merchant name...", fg_color=colors["INPUT_BG"], border_color=colors["INPUT_BORDER"], text_color=colors["TEXT_DARK"])
        w["search_entry"].grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=16)
        
        ctk.CTkButton(top_card, text="Search", width=82, height=34, corner_radius=12, fg_color=colors["BTN_ACTIVE"], hover_color=colors["BTN_ACTIVE_HOVER"], text_color=colors["TEXT_DARK"], font=("Segoe UI", 12, "bold"), command=callbacks["on_search"]).grid(row=0, column=2, sticky="w", padx=(0, 8), pady=16)
        ctk.CTkButton(top_card, text="Clear", width=82, height=34, corner_radius=12, fg_color=colors["BTN_DARK"], hover_color=colors["BTN_DARK_HOVER"], text_color=colors["TEXT_LIGHT"], font=("Segoe UI", 12, "bold"), command=callbacks["on_clear"]).grid(row=0, column=3, sticky="w", padx=(0, 16), pady=16)
        ctk.CTkButton(top_card, text="Create Task", width=104, height=34, corner_radius=12, fg_color=colors["BTN_DARK"], hover_color=colors["BTN_DARK_HOVER"], text_color=colors["TEXT_LIGHT"], font=("Segoe UI", 12, "bold"), command=callbacks["on_create"]).grid(row=0, column=4, sticky="w", padx=(0, 16), pady=16)
        
        w["show_all_button"] = ctk.CTkButton(top_card, text="Show All: OFF", width=110, height=34, corner_radius=12, fg_color=colors["BTN_DARK"], hover_color=colors["BTN_DARK_HOVER"], text_color=colors["TEXT_LIGHT"], font=("Segoe UI", 12, "bold"), command=callbacks["on_toggle_show_all"])
        w["show_all_button"].grid(row=0, column=5, sticky="w", padx=(0, 16), pady=16)

        w["follow_scope_label"] = ctk.CTkLabel(top_card, text="Only active task | Done hidden | Deadline in 3 days", font=("Segoe UI", 10, "italic"), text_color=colors["TEXT_MUTED"])
        w["follow_scope_label"].grid(row=0, column=7, columnspan=2, sticky="w", padx=(0, 10), pady=16)

        # Board Column
        table_card = ctk.CTkFrame(wrap, fg_color="#fbf5ec", corner_radius=16, border_width=1, border_color="#e0c79d")
        table_card.grid(row=1, column=0, sticky="new", padx=(16, 8), pady=(0, 16))
        table_card.grid_columnconfigure(0, weight=1)
        w["table_card"] = table_card

        ctk.CTkLabel(table_card, text="Task Board", font=("Segoe UI", 18, "bold"), text_color=colors["TEXT_DARK"]).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 10))

        canvas_wrap = ctk.CTkFrame(table_card, fg_color="#ffffff", corner_radius=14, border_width=1, border_color=colors["BORDER_SOFT"], height=600)
        canvas_wrap.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        canvas_wrap.grid_propagate(False)
        canvas_wrap.grid_columnconfigure(0, weight=1)
        canvas_wrap.grid_rowconfigure(1, weight=1)
        w["follow_canvas_wrap"] = canvas_wrap
        w["follow_board_card"] = canvas_wrap # ProcessPage expects this as the parent of canvas

        w["follow_header_canvas"] = tk.Canvas(canvas_wrap, bg="#ffffff", highlightthickness=0, bd=0, height=58)
        w["follow_header_canvas"].grid(row=0, column=0, sticky="ew", padx=(0, 0), pady=(0, 4))

        w["follow_canvas"] = tk.Canvas(canvas_wrap, bg="#ffffff", highlightthickness=0, bd=0)
        w["follow_canvas"].grid(row=1, column=0, sticky="nsew")
        w["follow_scrollbar"] = ctk.CTkScrollbar(canvas_wrap, orientation="vertical", command=w["follow_canvas"].yview)
        w["follow_scrollbar"].grid(row=1, column=1, sticky="ns", padx=(0, 6), pady=6)
        w["follow_canvas"].configure(yscrollcommand=w["follow_scrollbar"].set)

        # Detail Column
        detail_card = ctk.CTkFrame(wrap, fg_color="#fbf5ec", corner_radius=16, border_width=1, border_color="#e0c79d", width=280)
        detail_card.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))
        detail_card.grid_columnconfigure(0, weight=1)
        detail_card.grid_rowconfigure(0, weight=1)
        w["detail_card"] = detail_card

        w["detail_form"] = ctk.CTkScrollableFrame(detail_card, fg_color="#fbf5ec", corner_radius=16, border_width=0)
        w["detail_form"].grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        w["detail_form"].grid_columnconfigure(0, weight=1)

        return w

    def build_follow_detail_form(self, parent, colors, callbacks, titles):
        w = {}
        row = 0
        ctk.CTkLabel(parent, text=titles["detail_title"], font=("Segoe UI", 18, "bold"), text_color=colors["TEXT_DARK"]).grid(row=row, column=0, sticky="w", padx=18, pady=(16, 10))
        row += 1
        w["detail_hint"] = ctk.CTkLabel(parent, text=titles["detail_hint"], font=("Segoe UI", 12), text_color=colors["TEXT_MUTED"], justify="left")
        w["detail_hint"].grid(row=row, column=0, sticky="w", padx=18, pady=(0, 14))
        row += 1

        w["merchant_name_entry"] = self.create_labeled_entry(parent, row, "Merchant Name:", "SAPPHIRE NAILS 45805", colors["TEXT_DARK"], colors["INPUT_BG"], colors["INPUT_BORDER"])
        row += 1
        w["phone_entry"] = self.create_labeled_entry(parent, row, "Phone:", "(012) 345-6789", colors["TEXT_DARK"], colors["INPUT_BG"], colors["INPUT_BORDER"])
        row += 1
        w["problem_entry"] = self.create_labeled_entry(parent, row, "Problem:", "Setup + 1st training", colors["TEXT_DARK"], colors["INPUT_BG"], colors["INPUT_BORDER"])
        row += 1
        w["handoff_from_entry"] = self.create_labeled_entry(parent, row, "Task created by:", "", colors["TEXT_DARK"], colors["INPUT_BG"], colors["INPUT_BORDER"], state="disabled")
        row += 1

        deadline_wrap = ctk.CTkFrame(parent, fg_color="transparent")
        deadline_wrap.grid(row=row, column=0, sticky="ew", padx=18, pady=(2, 10))
        ctk.CTkLabel(deadline_wrap, text="Ngay gio hen", font=("Segoe UI", 12, "bold"), text_color=colors["TEXT_DARK"]).grid(row=0, column=0, sticky="w", pady=(0, 6))
        w["deadline_picker_button"] = ctk.CTkButton(deadline_wrap, text="Choose Date & Time", width=220, height=38, corner_radius=12, fg_color=colors["INPUT_BG"], hover_color="#f6ead7", border_width=1, border_color=colors["INPUT_BORDER"], text_color=colors["TEXT_DARK"], font=("Segoe UI", 11, "bold"), anchor="w", command=callbacks["on_deadline_click"])
        w["deadline_picker_button"].grid(row=1, column=0, sticky="w")
        w["deadline_value_hint"] = ctk.CTkLabel(deadline_wrap, text="Chua chon ngay gio hen.", font=("Segoe UI", 10), text_color=colors["TEXT_MUTED"])
        w["deadline_value_hint"].grid(row=1, column=1, sticky="w", padx=(12, 0))
        row += 1

        self.create_section_label(parent, row, "Assign to", colors["TEXT_DARK"])
        row += 1
        w["handoff_button_wrap"] = ctk.CTkFrame(parent, fg_color="transparent")
        w["handoff_button_wrap"].grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        row += 1

        self.create_section_label(parent, row, "Status", colors["TEXT_DARK"])
        row += 1
        status_wrap = ctk.CTkFrame(parent, fg_color="transparent")
        status_wrap.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        w["status_buttons"] = self.render_status_buttons(status_wrap, callbacks["on_status_change"], colors)
        row += 1

        self.create_section_label(parent, row, "Note", colors["TEXT_DARK"])
        row += 1
        w["note_box"] = ctk.CTkTextbox(parent, height=110, fg_color=colors["INPUT_BG"], border_color=colors["INPUT_BORDER"], border_width=1, text_color=colors["TEXT_DARK"], corner_radius=12, font=("Segoe UI", 12))
        w["note_box"].grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        row += 1

        action_row = ctk.CTkFrame(parent, fg_color="transparent")
        action_row.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 14))
        w["follow_save_button"] = ctk.CTkButton(action_row, text="Save", width=110, height=40, corner_radius=12, fg_color=colors["BTN_ACTIVE"], hover_color=colors["BTN_ACTIVE_HOVER"], text_color=colors["TEXT_DARK"], font=("Segoe UI", 13, "bold"), command=callbacks["on_save"])
        w["follow_save_button"].pack(side="left", padx=(0, 8))
        w["follow_update_button"] = ctk.CTkButton(action_row, text="Update", width=110, height=40, corner_radius=12, fg_color=colors["BTN_DARK"], hover_color=colors["BTN_DARK_HOVER"], text_color=colors["TEXT_LIGHT"], font=("Segoe UI", 13, "bold"), command=callbacks["on_update"])
        w["follow_update_button"].pack(side="left")
        w["follow_start_training_button"] = ctk.CTkButton(action_row, text="Start 1st Setup & Training", width=196, height=40, corner_radius=12, fg_color="#0f766e", hover_color="#115e59", text_color=colors["TEXT_LIGHT"], font=("Segoe UI", 12, "bold"), command=callbacks["on_start_training"])
        w["follow_start_training_button"].pack(side="left", padx=(8, 0))
        row += 1

        self.create_section_label(parent, row, "History / Log", colors["TEXT_DARK"])
        row += 1
        w["history_box"] = ctk.CTkScrollableFrame(parent, height=180, fg_color="#fff7ed", border_width=1, border_color=colors["INPUT_BORDER"], corner_radius=12)
        w["history_box"].grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 18))
        return w

    def build_setup_training_detail_form(self, parent, colors, callbacks, titles):
        w = {}
        row = 0
        ctk.CTkLabel(parent, text=titles["detail_title"], font=("Segoe UI", 18, "bold"), text_color=colors["TEXT_DARK"]).grid(row=row, column=0, sticky="w", padx=18, pady=(16, 10))
        row += 1
        w["detail_hint"] = ctk.CTkLabel(parent, text=titles["detail_hint"], font=("Segoe UI", 12), text_color=colors["TEXT_MUTED"], justify="left")
        w["detail_hint"].grid(row=row, column=0, sticky="w", padx=18, pady=(0, 14))
        row += 1

        info_card = ctk.CTkFrame(parent, fg_color="#fff8ef", corner_radius=12, border_width=1, border_color="#e2c89f")
        info_card.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        info_card.grid_columnconfigure(0, weight=1)
        row += 1

        row1 = ctk.CTkFrame(info_card, fg_color="transparent")
        row1.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
        row1.grid_columnconfigure(0, weight=1)
        w["training_merchant_label"] = ctk.CTkLabel(row1, text="-", font=("Segoe UI", 14, "bold"), text_color=colors["TEXT_DARK"], anchor="w", justify="left")
        w["training_merchant_label"].grid(row=0, column=0, sticky="w")

        row2 = ctk.CTkFrame(info_card, fg_color="transparent")
        row2.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 2))
        row2.grid_columnconfigure(0, weight=1)
        w["training_date_label"] = ctk.CTkLabel(row2, text="-", font=("Segoe UI", 12), text_color=colors["TEXT_MUTED"], anchor="w", justify="left")
        w["training_date_label"].grid(row=0, column=0, sticky="w")

        row3 = ctk.CTkFrame(info_card, fg_color="transparent")
        row3.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
        w["training_stage_badge"] = ctk.CTkLabel(row3, text="1st Setup & Training", font=("Segoe UI", 11, "bold"), text_color="#ffffff", fg_color="#9333ea", corner_radius=8, width=160, height=26)
        w["training_stage_badge"].pack(side="left", ipadx=4)

        self.create_section_label(parent, row, "Assign to", colors["TEXT_DARK"])
        row += 1
        w["handoff_button_wrap"] = ctk.CTkFrame(parent, fg_color="transparent")
        w["handoff_button_wrap"].grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        row += 1

        self.create_section_label(parent, row, "Training Summary Note", colors["TEXT_DARK"])
        row += 1
        w["note_box"] = ctk.CTkTextbox(parent, height=230, fg_color=colors["INPUT_BG"], border_color=colors["INPUT_BORDER"], border_width=1, text_color=colors["TEXT_DARK"], corner_radius=12, font=("Segoe UI", 12))
        w["note_box"].grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        row += 1

        self.create_section_label(parent, row, "Checklist", colors["TEXT_DARK"])
        row += 1
        w["training_sections_wrap"] = ctk.CTkFrame(parent, fg_color=colors["TRAINING_CANVAS_BG"], corner_radius=12, border_width=1, border_color="#e1c393", height=430)
        w["training_sections_wrap"].grid(row=row, column=0, sticky="nsew", padx=18, pady=(0, 12))
        w["training_sections_wrap"].grid_propagate(False)
        w["training_sections_wrap"].grid_columnconfigure(0, weight=1)
        w["training_sections_wrap"].grid_rowconfigure(0, weight=1)

        w["training_canvas"] = tk.Canvas(w["training_sections_wrap"], bg=colors["TRAINING_CANVAS_BG"], highlightthickness=0, bd=0)
        w["training_canvas"].grid(row=0, column=0, sticky="nsew")
        w["training_canvas_scrollbar"] = ctk.CTkScrollbar(w["training_sections_wrap"], orientation="vertical", command=callbacks["on_canvas_yview"])
        w["training_canvas_scrollbar"].grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=6)
        w["training_canvas"].configure(yscrollcommand=w["training_canvas_scrollbar"].set)
        row += 1

        action_row = ctk.CTkFrame(parent, fg_color="transparent")
        action_row.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 14))
        w["follow_update_button"] = ctk.CTkButton(action_row, text="Save Training", width=132, height=40, corner_radius=12, fg_color=colors["BTN_DARK"], hover_color=colors["BTN_DARK_HOVER"], text_color=colors["TEXT_LIGHT"], font=("Segoe UI", 13, "bold"), command=callbacks["on_update"])
        w["follow_update_button"].pack(side="left", padx=(0, 8))
        w["follow_complete_training_button"] = ctk.CTkButton(action_row, text="Complete 1st Training", width=182, height=40, corner_radius=12, fg_color=colors["BTN_ACTIVE"], hover_color=colors["BTN_ACTIVE_HOVER"], text_color=colors["TEXT_DARK"], font=("Segoe UI", 13, "bold"), command=callbacks["on_complete_training"])
        w["follow_complete_training_button"].pack(side="left")
        row += 1

        self.create_section_label(parent, row, "History / Log", colors["TEXT_DARK"])
        row += 1
        w["history_box"] = ctk.CTkScrollableFrame(parent, height=180, fg_color="#fff7ed", border_width=1, border_color=colors["INPUT_BORDER"], corner_radius=12)
        w["history_box"].grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 18))
        return w

    def build_deadline_popup(self, parent, anchor_widget, colors, callbacks, time_slots):
        """
        Dựng giao diện Deadline Popup
        """
        w = {}
        popup = ctk.CTkFrame(parent, fg_color="#fff7ed", corner_radius=14, border_width=1, border_color=colors["INPUT_BORDER"], width=292, height=344)
        popup.place(in_=anchor_widget, relx=0, rely=1.0, x=0, y=8, anchor="nw")
        popup.lift()
        popup.grid_columnconfigure(1, weight=1)
        w["popup_frame"] = popup

        # Month Navigation
        ctk.CTkButton(popup, text="<", width=34, height=30, corner_radius=10, fg_color=colors["BTN_DARK"], hover_color=colors["BTN_DARK_HOVER"], text_color=colors["TEXT_LIGHT"], command=callbacks["on_prev_month"]).grid(row=0, column=0, sticky="w", padx=(12, 6), pady=(12, 8))
        w["month_label"] = ctk.CTkLabel(popup, text="", font=("Segoe UI", 12, "bold"), text_color=colors["TEXT_DARK"])
        w["month_label"].grid(row=0, column=1, sticky="ew", pady=(12, 8))
        ctk.CTkButton(popup, text=">", width=34, height=30, corner_radius=10, fg_color=colors["BTN_DARK"], hover_color=colors["BTN_DARK_HOVER"], text_color=colors["TEXT_LIGHT"], command=callbacks["on_next_month"]).grid(row=0, column=2, sticky="e", padx=(6, 12), pady=(12, 8))

        # Calendar Canvas
        w["calendar_canvas"] = tk.Canvas(popup, width=266, height=198, bg="#fff7ed", highlightthickness=0, bd=0)
        w["calendar_canvas"].grid(row=1, column=0, columnspan=3, padx=12)

        # Time Selector
        ctk.CTkLabel(popup, text="Time", font=("Segoe UI", 11, "bold"), text_color=colors["TEXT_DARK"]).grid(row=2, column=0, columnspan=3, sticky="w", padx=12, pady=(4, 6))
        w["time_combo"] = ctk.CTkComboBox(popup, values=time_slots, height=36, fg_color=colors["INPUT_BG"], border_color=colors["INPUT_BORDER"], button_color=colors["BTN_ACTIVE"], button_hover_color=colors["BTN_ACTIVE_HOVER"], text_color=colors["TEXT_DARK"], dropdown_fg_color=colors["INPUT_BG"], dropdown_text_color=colors["TEXT_DARK"])
        w["time_combo"].grid(row=3, column=0, columnspan=3, sticky="ew", padx=12)

        # Action Buttons
        action_row = ctk.CTkFrame(popup, fg_color="transparent")
        action_row.grid(row=4, column=0, columnspan=3, sticky="ew", padx=12, pady=(12, 12))
        ctk.CTkButton(action_row, text="Cancel", width=108, height=34, corner_radius=10, fg_color=colors["BTN_DARK"], hover_color=colors["BTN_DARK_HOVER"], text_color=colors["TEXT_LIGHT"], command=callbacks["on_cancel"]).pack(side="left", padx=(0, 8))
        ctk.CTkButton(action_row, text="Confirm", width=108, height=34, corner_radius=10, fg_color=colors["BTN_ACTIVE"], hover_color=colors["BTN_ACTIVE_HOVER"], text_color=colors["TEXT_DARK"], command=callbacks["on_confirm"]).pack(side="left")

        return w

    def render_status_buttons(self, parent, callback, colors):
        buttons = {}
        statuses = ["FOLLOW", "FOLLOW REQUEST", "CHECK TRACKING NUMBER", "MISS TIP / CHARGE BACK", "DONE", "CANCEL", "DEMO"]
        for idx, name in enumerate(statuses):
            btn = ctk.CTkButton(parent, text=name, width=142, height=34, corner_radius=12, fg_color=colors["BTN_IDLE"], hover_color=colors["BTN_IDLE_HOVER"], text_color=colors["TEXT_LIGHT"], font=("Segoe UI", 10, "bold"), command=lambda value=name: callback(value))
            btn.grid(row=idx // 2, column=idx % 2, sticky="w", padx=(0, 8), pady=4)
            buttons[name] = btn
        return buttons

    def render_handoff_buttons(self, parent, options, selected_targets, callback, colors):
        buttons = {}
        for idx, name in enumerate(options):
            is_selected = name in selected_targets
            btn = ctk.CTkButton(parent, text=name, height=32, corner_radius=12, font=("Segoe UI", 11, "bold" if is_selected else "normal"), fg_color=colors["BTN_ACTIVE"] if is_selected else colors["BTN_INACTIVE"], text_color=colors["TEXT_DARK"], hover_color="#f6ead7", command=lambda n=name: callback(n))
            btn.grid(row=idx // 2, column=idx % 2, sticky="ew", padx=4, pady=4)
            parent.grid_columnconfigure(idx % 2, weight=1)
            buttons[name] = btn
        return buttons
