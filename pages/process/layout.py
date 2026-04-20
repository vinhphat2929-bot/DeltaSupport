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
        wrap.grid_columnconfigure(0, weight=15)   # Task Board (narrow)
        wrap.grid_columnconfigure(1, weight=85)   # Detail panel (wide)
        wrap.grid_rowconfigure(1, weight=1)
        w["follow_wrap"] = wrap

        # Dummy top card (hidden – kept for backward compat with code that refs it)
        top_card = ctk.CTkFrame(wrap, fg_color="transparent")
        top_card.grid_remove()
        w["follow_top_card"] = top_card
        w["follow_scope_label"] = ctk.CTkLabel(top_card, text="")

        # Board Column (with search baked in)
        table_card = ctk.CTkFrame(wrap, fg_color="#fbf5ec", corner_radius=16, border_width=1, border_color="#e0c79d")
        table_card.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(16, 16))
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(2, weight=1)
        w["table_card"] = table_card

        # --- Title row inside board ---
        board_header = ctk.CTkFrame(table_card, fg_color="transparent")
        board_header.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        board_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(board_header, text="Task Board", font=("Segoe UI", 16, "bold"), text_color=colors["TEXT_DARK"]).grid(row=0, column=0, sticky="w")

        # --- Search row inside board ---
        search_row = ctk.CTkFrame(table_card, fg_color="transparent")
        search_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 6))

        w["search_entry"] = ctk.CTkEntry(search_row, width=160, height=30, placeholder_text="Search merchant...", fg_color=colors["INPUT_BG"], border_color=colors["INPUT_BORDER"], text_color=colors["TEXT_DARK"], font=("Segoe UI", 11))
        w["search_entry"].pack(side="left", padx=(0, 4))

        ctk.CTkButton(search_row, text="Search", width=62, height=30, corner_radius=10, fg_color=colors["BTN_ACTIVE"], hover_color=colors["BTN_ACTIVE_HOVER"], text_color=colors["TEXT_DARK"], font=("Segoe UI", 11, "bold"), command=callbacks["on_search"]).pack(side="left", padx=(0, 4))
        ctk.CTkButton(search_row, text="Clear", width=50, height=30, corner_radius=10, fg_color=colors["BTN_DARK"], hover_color=colors["BTN_DARK_HOVER"], text_color=colors["TEXT_LIGHT"], font=("Segoe UI", 11, "bold"), command=callbacks["on_clear"]).pack(side="left", padx=(0, 4))
        ctk.CTkButton(search_row, text="+ Create", width=62, height=30, corner_radius=10, fg_color="#0f766e", hover_color="#115e59", text_color="#ffffff", font=("Segoe UI", 11, "bold"), command=callbacks["on_create"]).pack(side="left", padx=(0, 6))

        w["show_all_button"] = ctk.CTkButton(search_row, text="All: OFF", width=60, height=30, corner_radius=10, fg_color=colors["BTN_DARK"], hover_color=colors["BTN_DARK_HOVER"], text_color=colors["TEXT_LIGHT"], font=("Segoe UI", 11, "bold"), command=callbacks["on_toggle_show_all"])
        w["show_all_button"].pack(side="left", padx=(0, 6))

        w["include_done_switch"] = ctk.CTkSwitch(search_row, text="Done", width=50, font=("Segoe UI", 10, "bold"), text_color=colors["TEXT_DARK"], progress_color=colors["BTN_ACTIVE"], command=callbacks.get("on_toggle_include_done", lambda: None))
        w["include_done_switch"].pack(side="left")

        # --- Board canvas ---
        canvas_wrap = ctk.CTkFrame(table_card, fg_color="#ffffff", corner_radius=14, border_width=1, border_color=colors["BORDER_SOFT"])
        canvas_wrap.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))
        canvas_wrap.grid_columnconfigure(0, weight=1)
        canvas_wrap.grid_rowconfigure(1, weight=1)
        w["follow_canvas_wrap"] = canvas_wrap
        w["follow_board_card"] = canvas_wrap

        w["follow_header_canvas"] = tk.Canvas(canvas_wrap, bg="#ffffff", highlightthickness=0, bd=0, height=58)
        w["follow_header_canvas"].grid(row=0, column=0, sticky="ew")

        w["follow_canvas"] = tk.Canvas(canvas_wrap, bg="#ffffff", highlightthickness=0, bd=0)
        w["follow_canvas"].grid(row=1, column=0, sticky="nsew")
        w["follow_scrollbar"] = ctk.CTkScrollbar(canvas_wrap, orientation="vertical", command=w["follow_canvas"].yview)
        w["follow_scrollbar"].grid(row=1, column=1, sticky="ns", padx=(0, 4), pady=4)
        w["follow_canvas"].configure(yscrollcommand=w["follow_scrollbar"].set)

        # Detail Column
        detail_card = ctk.CTkFrame(wrap, fg_color="#fbf5ec", corner_radius=16, border_width=1, border_color="#e0c79d", width=280)
        detail_card.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=(16, 16))
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

        # Start button — visible before training begins (also contains View Info for DONE tasks)
        start_wrap = ctk.CTkFrame(parent, fg_color="transparent")
        start_wrap.grid(row=row, column=0, sticky="ew", padx=18, pady=(14, 4))
        w["start_training_button"] = ctk.CTkButton(
            start_wrap, text="\u25b6  Start 1st Training", width=240, height=46, corner_radius=12,
            fg_color=colors["BTN_ACTIVE"], hover_color=colors["BTN_ACTIVE_HOVER"],
            text_color=colors["TEXT_DARK"], font=("Segoe UI", 14, "bold"),
            command=callbacks.get("on_start_training", lambda: None)
        )
        w["start_training_button"].pack(side="left", padx=(0, 8), pady=6)
        # View Info button — shown only for DONE tasks (hidden by default)
        w["view_training_info_button"] = ctk.CTkButton(
            start_wrap, text="\U0001f4cb  View Setup & Training Info", width=260, height=46, corner_radius=12,
            fg_color="#475569", hover_color="#334155",
            text_color="#ffffff", font=("Segoe UI", 13, "bold"),
            command=callbacks.get("on_view_training_info", lambda: None)
        )
        # Don't pack yet — shown conditionally in update_follow_form_mode
        row += 1

        # Tabs for Checklist (hidden until Start is clicked)
        tab_wrap = ctk.CTkFrame(parent, fg_color="transparent")
        tab_wrap.grid(row=row, column=0, sticky="ew", padx=18, pady=(4, 6))
        tab_wrap.grid_remove()   # hidden initially
        w["tab_wrap"] = tab_wrap

        w["checklist_tabs"] = ctk.CTkSegmentedButton(
            tab_wrap,
            values=["I. SET UP", "II. HƯỚNG DẪN", "III. THEO DÕI"],
            font=("Segoe UI", 13, "bold"),
            fg_color="#6b6057",
            selected_color=colors["BTN_ACTIVE"],
            selected_hover_color=colors["BTN_ACTIVE_HOVER"],
            unselected_color="#6b6057",
            unselected_hover_color="#8a7a6d",
            text_color=colors["TEXT_DARK"],
            text_color_disabled="#e8ddd4",
            command=callbacks.get("on_tab_change", lambda v: None)
        )
        w["checklist_tabs"].pack(fill="x", expand=True)
        w["checklist_tabs"].set("I. SET UP")
        row += 1

        w["training_sections_wrap"] = ctk.CTkFrame(parent, fg_color=colors["TRAINING_CANVAS_BG"], corner_radius=12, border_width=1, border_color="#e1c393")
        w["training_sections_wrap"].grid(row=row, column=0, sticky="nsew", padx=18, pady=(0, 12))
        w["training_sections_wrap"].grid_remove()   # hidden initially
        w["training_sections_wrap"].grid_columnconfigure(0, weight=1)

        # Plain frame — outer detail_form handles scrolling, no nested scrollbar
        w["training_list_frame"] = ctk.CTkFrame(
            w["training_sections_wrap"],
            fg_color="#ffffff",
            corner_radius=8,
            border_width=0,
        )
        w["training_list_frame"].pack(fill="both", expand=True, padx=4, pady=4)
        w["training_list_frame"].grid_columnconfigure(0, minsize=38)
        w["training_list_frame"].grid_columnconfigure(1, weight=1)
        w["training_list_frame"].grid_columnconfigure(2, minsize=72)
        # Keep training_canvas as None for compat
        w["training_canvas"] = None
        row += 1


        action_row = ctk.CTkFrame(parent, fg_color="transparent")
        w["action_row"] = action_row
        action_row.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 14))
        action_row.grid_remove()   # hidden initially
        w["follow_update_button"] = ctk.CTkButton(action_row, text="T\u1ea1m ng\u01b0ng / C\u1eadp nh\u1eadt", width=162, height=40, corner_radius=12, fg_color=colors["BTN_DARK"], hover_color=colors["BTN_DARK_HOVER"], text_color=colors["TEXT_LIGHT"], font=("Segoe UI", 13, "bold"), command=callbacks["on_update"])
        w["follow_update_button"].pack(side="left", padx=(0, 6))
        # "Complete current tab" — yellow accent button
        w["complete_tab_button"] = ctk.CTkButton(action_row, text="\u2714 Ho\u00e0n th\u00e0nh m\u1ee5c n\u00e0y", width=168, height=40, corner_radius=12, fg_color="#ca8a04", hover_color="#a16207", text_color="#ffffff", font=("Segoe UI", 13, "bold"), command=callbacks.get("on_complete_tab", lambda: None))
        w["complete_tab_button"].pack(side="left", padx=(0, 6))
        w["follow_complete_training_button"] = ctk.CTkButton(action_row, text="Complete 1st Training", width=182, height=40, corner_radius=12, fg_color="#b8aba0", hover_color="#b8aba0", text_color=colors["TEXT_LIGHT"], font=("Segoe UI", 13, "bold"), state="disabled", command=callbacks["on_complete_training"])
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
        w["time_combo"].set(time_slots[0] if time_slots else "")
        w["time_combo"].grid(row=3, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 16))

        # Action Buttons
        action_row = ctk.CTkFrame(popup, fg_color="transparent")
        action_row.grid(row=4, column=0, columnspan=3, sticky="ew", padx=12, pady=(12, 12))
        ctk.CTkButton(action_row, text="Cancel", width=108, height=34, corner_radius=10, fg_color=colors["BTN_DARK"], hover_color=colors["BTN_DARK_HOVER"], text_color=colors["TEXT_LIGHT"], command=callbacks["on_cancel"]).pack(side="left", padx=(0, 8))
        ctk.CTkButton(action_row, text="Confirm", width=108, height=34, corner_radius=10, fg_color=colors["BTN_ACTIVE"], hover_color=colors["BTN_ACTIVE_HOVER"], text_color=colors["TEXT_DARK"], command=callbacks["on_confirm"]).pack(side="left")

        return w

    def build_training_completion_popup(self, parent, colors, callbacks, time_slots):
        w = {}
        popup = ctk.CTkToplevel(parent)
        popup.title("Training Completion Details")
        popup.geometry("400x520")
        popup.resizable(False, False)
        popup.configure(fg_color="#fbf5ec")
        popup.attributes('-topmost', 'true')
        popup.transient(parent)
        
        popup.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (400 // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (520 // 2)
        popup.geometry(f"+{x}+{y}")
        
        w["popup_window"] = popup

        main_frame = ctk.CTkFrame(popup, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        row = 0
        self.create_section_label(main_frame, row, "Ngay gio hen (Next Appointment)", colors["TEXT_DARK"])
        row += 1
        deadline_wrap = ctk.CTkFrame(main_frame, fg_color="transparent")
        deadline_wrap.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        w["popup_deadline_picker_button"] = ctk.CTkButton(deadline_wrap, text="Choose Date & Time", width=220, height=38, corner_radius=12, fg_color=colors["INPUT_BG"], hover_color="#f6ead7", border_width=1, border_color=colors["INPUT_BORDER"], text_color=colors["TEXT_DARK"], font=("Segoe UI", 11, "bold"), anchor="w", command=callbacks.get("on_popup_deadline_click", lambda: None))
        w["popup_deadline_picker_button"].grid(row=0, column=0, sticky="w")
        w["popup_deadline_value_hint"] = ctk.CTkLabel(deadline_wrap, text="Chua chon ngay gio hen.", font=("Segoe UI", 10), text_color=colors["TEXT_MUTED"])
        w["popup_deadline_value_hint"].grid(row=0, column=1, sticky="w", padx=(12, 0))
        row += 1

        self.create_section_label(main_frame, row, "Assign to", colors["TEXT_DARK"])
        row += 1
        w["popup_handoff_button_wrap"] = ctk.CTkFrame(main_frame, fg_color="transparent")
        w["popup_handoff_button_wrap"].grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        row += 1

        self.create_section_label(main_frame, row, "Training Summary Note", colors["TEXT_DARK"])
        row += 1
        w["popup_note_box"] = ctk.CTkTextbox(main_frame, height=120, fg_color=colors["INPUT_BG"], border_color=colors["INPUT_BORDER"], border_width=1, text_color=colors["TEXT_DARK"], corner_radius=12, font=("Segoe UI", 12))
        w["popup_note_box"].grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 20))
        row += 1

        action_wrap = ctk.CTkFrame(main_frame, fg_color="transparent")
        action_wrap.grid(row=row, column=0, sticky="ew", padx=18, pady=(10, 0))
        
        w["popup_cancel_button"] = ctk.CTkButton(action_wrap, text="Cancel", width=100, height=40, corner_radius=12, fg_color=colors["BTN_DARK"], hover_color=colors["BTN_DARK_HOVER"], text_color=colors["TEXT_LIGHT"], font=("Segoe UI", 13, "bold"), command=callbacks.get("on_popup_cancel", lambda: None))
        w["popup_cancel_button"].pack(side="left", padx=(0, 10))
        
        w["popup_confirm_button"] = ctk.CTkButton(action_wrap, text="Confirm", width=120, height=40, corner_radius=12, fg_color=colors["BTN_ACTIVE"], hover_color=colors["BTN_ACTIVE_HOVER"], text_color=colors["TEXT_DARK"], font=("Segoe UI", 13, "bold"), command=callbacks.get("on_popup_confirm", lambda: None))
        w["popup_confirm_button"].pack(side="right")

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