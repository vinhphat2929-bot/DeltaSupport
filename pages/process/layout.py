import tkinter as tk
import customtkinter as ctk

from utils.timezone_utils import format_deadline_hint_text


SETUP_BOARD_COMPACT_WIDTH = 280


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
        if self.page.is_setup_training_section():
            wrap.grid_columnconfigure(0, weight=0, minsize=SETUP_BOARD_COMPACT_WIDTH)
            wrap.grid_columnconfigure(1, weight=1)
        else:
            wrap.grid_columnconfigure(0, weight=4)   # Task Board (slightly larger)
            wrap.grid_columnconfigure(1, weight=96)   # Detail panel
        wrap.grid_rowconfigure(1, weight=1)
        w["follow_wrap"] = wrap

        # Dummy top card (hidden – kept for backward compat with code that refs it)
        top_card = ctk.CTkFrame(wrap, fg_color="transparent")
        top_card.grid_remove()
        w["follow_top_card"] = top_card
        w["follow_scope_label"] = ctk.CTkLabel(top_card, text="")

        # Board Column (with search baked in)
        table_card = ctk.CTkFrame(wrap, fg_color="#f7efe2", corner_radius=16, border_width=1, border_color="#cda86a")
        table_card.grid(
            row=1,
            column=0,
            sticky="nsw" if self.page.is_setup_training_section() else "nsew",
            padx=(10, 6),
            pady=(16, 16),
        )
        if self.page.is_setup_training_section():
            table_card.configure(width=SETUP_BOARD_COMPACT_WIDTH)
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(1, weight=1)
        w["table_card"] = table_card

        if self.page.is_setup_training_section():
            top_panel = ctk.CTkFrame(
                table_card,
                fg_color="#f4e4ca",
                corner_radius=14,
                border_width=1,
                border_color="#c89247",
            )
            top_panel.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 10))
            top_panel.grid_columnconfigure(0, weight=1)

            title_row = ctk.CTkFrame(top_panel, fg_color="transparent")
            title_row.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 6))
            title_row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                title_row,
                text="Task Board",
                font=("Segoe UI", 18, "bold"),
                text_color=colors["TEXT_DARK"],
                anchor="center",
                justify="center",
            ).grid(row=0, column=0, sticky="ew")

            action_row = ctk.CTkFrame(top_panel, fg_color="transparent")
            action_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 6))
            action_row.grid_columnconfigure(0, weight=1)
            action_row.grid_columnconfigure(2, weight=1)

            action_controls = ctk.CTkFrame(action_row, fg_color="transparent")
            action_controls.grid(row=0, column=1)

            ctk.CTkButton(
                action_controls,
                text="+ Create",
                width=76,
                height=32,
                corner_radius=12,
                fg_color="#0f766e",
                hover_color="#115e59",
                text_color="#ffffff",
                font=("Segoe UI", 10, "bold"),
                command=callbacks["on_create"],
            ).pack(side="left", padx=(0, 6))

            w["show_all_button"] = ctk.CTkButton(
                action_controls,
                text="Show All: OFF",
                width=108,
                height=32,
                corner_radius=12,
                fg_color=colors["BTN_DARK"],
                hover_color=colors["BTN_DARK_HOVER"],
                text_color=colors["TEXT_LIGHT"],
                font=("Segoe UI", 10, "bold"),
                command=callbacks["on_toggle_show_all"],
            )
            w["show_all_button"].pack(side="left", padx=(0, 6))

            w["include_done_switch"] = ctk.CTkSwitch(
                action_controls,
                text="Done",
                width=54,
                switch_width=30,
                switch_height=16,
                font=("Segoe UI", 9, "bold"),
                text_color=colors["TEXT_DARK"],
                progress_color=colors["BTN_ACTIVE"],
                command=callbacks.get("on_toggle_include_done", lambda: None),
            )
            w["include_done_switch"].pack(side="left")

            search_row = ctk.CTkFrame(top_panel, fg_color="transparent")
            search_row.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
            search_row.grid_columnconfigure(0, weight=1)
            search_row.grid_columnconfigure(2, weight=1)

            search_controls = ctk.CTkFrame(search_row, fg_color="transparent")
            search_controls.grid(row=0, column=1)

            w["search_entry"] = ctk.CTkEntry(
                search_controls,
                width=148,
                height=32,
                placeholder_text="Search merchant...",
                fg_color=colors["INPUT_BG"],
                border_color=colors["INPUT_BORDER"],
                text_color=colors["TEXT_DARK"],
                font=("Segoe UI", 10),
            )
            w["search_entry"].pack(side="left", padx=(0, 6))

            ctk.CTkButton(
                search_controls,
                text="Search",
                width=58,
                height=32,
                corner_radius=12,
                fg_color=colors["BTN_ACTIVE"],
                hover_color=colors["BTN_ACTIVE_HOVER"],
                text_color=colors["TEXT_DARK"],
                font=("Segoe UI", 10, "bold"),
                command=callbacks["on_search"],
            ).pack(side="left", padx=(0, 6))

            ctk.CTkButton(
                search_controls,
                text="Clear",
                width=54,
                height=32,
                corner_radius=12,
                fg_color=colors["BTN_DARK"],
                hover_color=colors["BTN_DARK_HOVER"],
                text_color=colors["TEXT_LIGHT"],
                font=("Segoe UI", 10, "bold"),
                command=callbacks["on_clear"],
            ).pack(side="left")
        else:
            top_panel = ctk.CTkFrame(
                table_card,
                fg_color="#f9f1e4",
                corner_radius=14,
                border_width=1,
                border_color="#d8b57b",
            )
            top_panel.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 10))
            top_panel.grid_columnconfigure(0, weight=1)

            title_row = ctk.CTkFrame(top_panel, fg_color="transparent")
            title_row.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 4))
            title_row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                title_row,
                text="Task Board",
                font=("Segoe UI", 18, "bold"),
                text_color=colors["TEXT_DARK"],
                anchor="center",
                justify="center",
            ).grid(row=0, column=0, sticky="ew")

            toolbar_row = ctk.CTkFrame(top_panel, fg_color="transparent")
            toolbar_row.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 4))
            toolbar_row.grid_columnconfigure(0, weight=1)
            toolbar_row.grid_columnconfigure(1, weight=1)

            search_controls = ctk.CTkFrame(toolbar_row, fg_color="transparent")
            search_controls.grid(row=0, column=0, sticky="w")

            w["search_entry"] = ctk.CTkEntry(
                search_controls,
                width=220,
                height=36,
                placeholder_text="Search merchant...",
                fg_color=colors["INPUT_BG"],
                border_color=colors["INPUT_BORDER"],
                text_color=colors["TEXT_DARK"],
                font=("Segoe UI", 11),
            )
            w["search_entry"].pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                search_controls,
                text="Search",
                width=74,
                height=36,
                corner_radius=12,
                fg_color=colors["BTN_ACTIVE"],
                hover_color=colors["BTN_ACTIVE_HOVER"],
                text_color=colors["TEXT_DARK"],
                font=("Segoe UI", 11, "bold"),
                command=callbacks["on_search"],
            ).pack(side="left", padx=(0, 6))

            ctk.CTkButton(
                search_controls,
                text="Clear",
                width=68,
                height=36,
                corner_radius=12,
                fg_color=colors["BTN_DARK"],
                hover_color=colors["BTN_DARK_HOVER"],
                text_color=colors["TEXT_LIGHT"],
                font=("Segoe UI", 11, "bold"),
                command=callbacks["on_clear"],
            ).pack(side="left")

            action_controls = ctk.CTkFrame(toolbar_row, fg_color="transparent")
            action_controls.grid(row=0, column=1, sticky="e")

            ctk.CTkButton(
                action_controls,
                text="+ Create",
                width=88,
                height=36,
                corner_radius=12,
                fg_color="#0f766e",
                hover_color="#115e59",
                text_color="#ffffff",
                font=("Segoe UI", 11, "bold"),
                command=callbacks["on_create"],
            ).pack(side="left", padx=(0, 8))

            w["show_all_button"] = ctk.CTkButton(
                action_controls,
                text="All: OFF",
                width=84,
                height=36,
                corner_radius=12,
                fg_color=colors["BTN_DARK"],
                hover_color=colors["BTN_DARK_HOVER"],
                text_color=colors["TEXT_LIGHT"],
                font=("Segoe UI", 11, "bold"),
                command=callbacks["on_toggle_show_all"],
            )
            w["show_all_button"].pack(side="left", padx=(0, 10))

            w["include_done_switch"] = ctk.CTkSwitch(
                action_controls,
                text="Done",
                width=58,
                switch_width=34,
                switch_height=18,
                font=("Segoe UI", 10, "bold"),
                text_color=colors["TEXT_DARK"],
                progress_color=colors["BTN_ACTIVE"],
                command=callbacks.get("on_toggle_include_done", lambda: None),
            )
            w["include_done_switch"].pack(side="left")

            w["follow_scope_label"] = ctk.CTkLabel(
                top_panel,
                text="",
                font=("Segoe UI", 10),
                text_color=colors["TEXT_MUTED"],
                anchor="w",
                justify="left",
            )
            w["follow_scope_label"].grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))

        # --- Board canvas ---
        canvas_wrap = ctk.CTkFrame(table_card, fg_color="#fffdfa", corner_radius=14, border_width=1, border_color="#cfb081")
        canvas_row = 1
        canvas_wrap.grid(row=canvas_row, column=0, sticky="nsew", padx=10, pady=(0, 10))
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
        detail_card = ctk.CTkFrame(
            wrap,
            fg_color="#fbf5ec",
            corner_radius=16,
            border_width=1,
            border_color="#e0c79d",
            width=1 if self.page.is_setup_training_section() else 280,
        )
        detail_card.grid(row=1, column=1, sticky="nsew", padx=(12, 16), pady=(12, 16))
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
        w["tracking_number_entry"] = self.create_labeled_entry(parent, row, "UPS Tracking:", "1ZXXXXXXXXXXXXXXX", colors["TEXT_DARK"], colors["INPUT_BG"], colors["INPUT_BORDER"])
        w["tracking_number_row"] = w["tracking_number_entry"].master
        w["tracking_number_row"].grid_remove()
        row += 1
        w["track_ups_button_row"] = ctk.CTkFrame(parent, fg_color="transparent")
        w["track_ups_button_row"].grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        w["track_ups_button"] = ctk.CTkButton(w["track_ups_button_row"], text="Track UPS", width=118, height=34, corner_radius=10, fg_color="#8b5e1a", hover_color="#a06c1e", text_color="#fff7e8", font=("Segoe UI", 12, "bold"), command=callbacks.get("on_track_ups", lambda: None))
        w["track_ups_button"].pack(anchor="e")
        w["track_ups_button_row"].grid_remove()
        row += 1
        w["problem_entry"] = self.create_labeled_entry(parent, row, "Problem:", "Setup + 1st training", colors["TEXT_DARK"], colors["INPUT_BG"], colors["INPUT_BORDER"])
        row += 1
        w["handoff_from_entry"] = self.create_labeled_entry(parent, row, "Task created by:", "", colors["TEXT_DARK"], colors["INPUT_BG"], colors["INPUT_BORDER"], state="disabled")
        row += 1

        deadline_wrap = ctk.CTkFrame(parent, fg_color="transparent")
        deadline_wrap.grid(row=row, column=0, sticky="ew", padx=18, pady=(2, 10))
        deadline_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(deadline_wrap, text="Ngay gio hen", font=("Segoe UI", 12, "bold"), text_color=colors["TEXT_DARK"]).grid(row=0, column=0, sticky="w", pady=(0, 6))
        w["deadline_picker_button"] = ctk.CTkButton(deadline_wrap, text="Choose Date & Time", width=220, height=38, corner_radius=12, fg_color=colors["INPUT_BG"], hover_color="#f6ead7", border_width=1, border_color=colors["INPUT_BORDER"], text_color=colors["TEXT_DARK"], font=("Segoe UI", 11, "bold"), anchor="w", command=callbacks["on_deadline_click"])
        w["deadline_picker_button"].grid(row=1, column=0, sticky="w")
        w["deadline_value_hint"] = ctk.CTkLabel(
            deadline_wrap,
            text=format_deadline_hint_text(),
            font=("Segoe UI", 10),
            text_color=colors["TEXT_MUTED"],
            justify="left",
        )
        w["deadline_value_hint"].grid(row=2, column=0, sticky="w", pady=(8, 0))
        row += 1

        self.create_section_label(parent, row, "Assignee", colors["TEXT_DARK"])
        row += 1
        w["handoff_button_wrap"] = ctk.CTkFrame(parent, fg_color="transparent")
        w["handoff_button_wrap"].grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        row += 1

        self.create_section_label(parent, row, "Status", colors["TEXT_DARK"])
        row += 1
        status_wrap = ctk.CTkFrame(parent, fg_color="transparent")
        status_wrap.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
        status_wrap.grid_columnconfigure(0, weight=1, uniform="follow_status")
        status_wrap.grid_columnconfigure(1, weight=1, uniform="follow_status")
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
        w["history_box"] = ctk.CTkScrollableFrame(parent, height=240, fg_color="#fff7ed", border_width=1, border_color=colors["INPUT_BORDER"], corner_radius=12)
        w["history_box"].grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 18))
        row += 1

        delete_row = ctk.CTkFrame(parent, fg_color="transparent")
        delete_row.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 18))
        w["follow_delete_button"] = ctk.CTkButton(delete_row, text="Delete Task", width=118, height=40, corner_radius=12, fg_color="#9f2d2d", hover_color="#ba3a3a", text_color="#fff7f0", font=("Segoe UI", 13, "bold"), command=callbacks["on_delete"])
        w["follow_delete_button"].pack(anchor="e")
        return w

    def build_setup_training_detail_form(self, parent, colors, callbacks, titles):
        w = {}
        row = 0
        ctk.CTkLabel(parent, text=titles["detail_title"], font=("Segoe UI", 18, "bold"), text_color=colors["TEXT_DARK"]).grid(row=row, column=0, sticky="w", padx=18, pady=(16, 10))
        row += 1
        w["detail_hint"] = ctk.CTkLabel(parent, text=titles["detail_hint"], font=("Segoe UI", 12), text_color=colors["TEXT_MUTED"], justify="left")
        w["detail_hint"].grid(row=row, column=0, sticky="w", padx=18, pady=(0, 14))
        row += 1

        info_card = ctk.CTkFrame(parent, fg_color="#f3e0c0", corner_radius=12, border_width=1, border_color="#c89247")
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
        w["training_stage_badge"] = ctk.CTkLabel(row3, text="Set up & 1st Training", font=("Segoe UI", 11, "bold"), text_color="#ffffff", fg_color="#9333ea", corner_radius=8, width=170, height=26)
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
            values=["I. SET UP HARDWARE", "II. SET UP POS", "III. TRAINING"],
            font=("Segoe UI", 13, "bold"),
            fg_color="#4a372b",
            selected_color="#c58b42",
            selected_hover_color="#d49a50",
            unselected_color="#665244",
            unselected_hover_color="#745e4f",
            text_color="#f9f2e8",
            text_color_disabled="#d8c7b4",
            command=callbacks.get("on_tab_change", lambda v: None)
        )
        w["checklist_tabs"].pack(fill="x", expand=True)
        w["checklist_tabs"].set("I. SET UP HARDWARE")
        row += 1

        w["training_sections_wrap"] = ctk.CTkFrame(parent, fg_color=colors["TRAINING_CANVAS_BG"], corner_radius=12, border_width=1, border_color="#e1c393")
        w["training_sections_wrap"].grid(row=row, column=0, sticky="nsew", padx=18, pady=(0, 12))
        w["training_sections_wrap"].grid_remove()   # hidden initially
        w["training_sections_wrap"].grid_columnconfigure(0, weight=1)

        # Plain frame — outer detail_form handles scrolling, no nested scrollbar
        canvas_wrap = ctk.CTkFrame(
            w["training_sections_wrap"],
            fg_color="#ffffff",
            corner_radius=8,
            border_width=0,
        )
        canvas_wrap.pack(fill="both", expand=True, padx=4, pady=4)
        canvas_wrap.grid_columnconfigure(0, weight=1)
        canvas_wrap.grid_rowconfigure(0, weight=1)

        w["training_canvas"] = tk.Canvas(
            canvas_wrap,
            bg="#ffffff",
            highlightthickness=0,
            bd=0,
            height=420,
        )
        w["training_canvas"].grid(row=0, column=0, sticky="nsew")

        w["training_list_frame"] = canvas_wrap
        row += 1


        action_row = ctk.CTkFrame(parent, fg_color="transparent")
        w["action_row"] = action_row
        action_row.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 14))
        action_row.grid_remove()   # hidden initially
        w["follow_update_button"] = ctk.CTkButton(action_row, text="T\u1ea1m ng\u01b0ng / C\u1eadp nh\u1eadt", width=162, height=40, corner_radius=12, fg_color=colors["BTN_DARK"], hover_color=colors["BTN_DARK_HOVER"], text_color=colors["TEXT_LIGHT"], font=("Segoe UI", 13, "bold"), command=callbacks["on_update"])
        w["follow_update_button"].pack(side="left", padx=(0, 6))
        # "Complete current tab" — yellow accent button
        w["complete_tab_button"] = ctk.CTkButton(action_row, text="Complete Set I", width=168, height=40, corner_radius=12, fg_color="#ca8a04", hover_color="#a16207", text_color="#ffffff", font=("Segoe UI", 13, "bold"), command=callbacks.get("on_complete_tab", lambda: None))
        w["complete_tab_button"].pack(side="left", padx=(0, 6))
        w["follow_complete_training_button"] = ctk.CTkButton(action_row, text="Complete 1st Training", width=182, height=40, corner_radius=12, fg_color="#b8aba0", hover_color="#b8aba0", text_color=colors["TEXT_LIGHT"], font=("Segoe UI", 13, "bold"), state="disabled", command=callbacks["on_complete_training"])
        w["follow_complete_training_button"].pack(side="left")
        row += 1

        self.create_section_label(parent, row, "History / Log", colors["TEXT_DARK"])
        row += 1
        w["history_box"] = ctk.CTkScrollableFrame(parent, height=240, fg_color="#fff7ed", border_width=1, border_color=colors["INPUT_BORDER"], corner_radius=12)
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
        deadline_wrap.grid_columnconfigure(0, weight=1)
        w["popup_deadline_picker_button"] = ctk.CTkButton(deadline_wrap, text="Choose Date & Time", width=220, height=38, corner_radius=12, fg_color=colors["INPUT_BG"], hover_color="#f6ead7", border_width=1, border_color=colors["INPUT_BORDER"], text_color=colors["TEXT_DARK"], font=("Segoe UI", 11, "bold"), anchor="w", command=callbacks.get("on_popup_deadline_click", lambda: None))
        w["popup_deadline_picker_button"].grid(row=0, column=0, sticky="w")
        w["popup_deadline_value_hint"] = ctk.CTkLabel(
            deadline_wrap,
            text=format_deadline_hint_text(),
            font=("Segoe UI", 10),
            text_color=colors["TEXT_MUTED"],
            justify="left",
        )
        w["popup_deadline_value_hint"].grid(row=1, column=0, sticky="w", pady=(8, 0))
        row += 1

        self.create_section_label(main_frame, row, "Assignee", colors["TEXT_DARK"])
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
        statuses = ["FOLLOW", "FOLLOW REQUEST", "SHIP OUT", "MISS TIP / CHARGE BACK", "DONE", "CANCEL", "DEMO"]
        for idx, name in enumerate(statuses):
            btn = ctk.CTkButton(
                parent,
                text=name,
                width=124,
                height=34,
                corner_radius=12,
                fg_color=colors["BTN_IDLE"],
                hover_color=colors["BTN_IDLE_HOVER"],
                text_color=colors["TEXT_LIGHT"],
                font=("Segoe UI", 9, "bold"),
                command=lambda value=name: callback(value),
            )
            pad_x = (0, 8) if idx % 2 == 0 else (0, 0)
            btn.grid(row=idx // 2, column=idx % 2, sticky="ew", padx=pad_x, pady=4)
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
