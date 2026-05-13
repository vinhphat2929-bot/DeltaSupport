import difflib
import unicodedata
from datetime import date
from tkinter import messagebox

import customtkinter as ctk

from services.schedule_config_service import DAY_ORDER
from services.schedule_setup_api_service import (
    get_schedule_setup_employees_api,
    save_schedule_setup_employee_api,
    set_schedule_setup_active_api,
)
from utils.window_icon_utils import apply_app_window_icon


BG_MAIN = "transparent"
BG_CARD = "#fffaf3"
BG_PANEL = "#f5ede0"
BORDER = "#c8a97a"
TEXT_MAIN = "#2a1d10"
TEXT_SUB = "#8a6b4a"
BTN_PRIMARY = "#b87d3a"
BTN_PRIMARY_HOVER = "#d49a50"
BTN_DARK = "#3a2a1c"
BTN_DARK_HOVER = "#4e3925"
BTN_DANGER = "#b45a4f"
BTN_DANGER_HOVER = "#cc6c60"

DEPARTMENTS = [
    "Technical Support",
    "Sale Team",
    "Office",
    "Management",
    "Customer Service",
    "Marketing Team",
]

SHIFT_VALUES = ["Shift 1", "Shift 2", "Shift 3"]


def uses_shift_setup(department):
    return str(department or "").strip() == "Technical Support"


def parse_time_range(value):
    text = str(value or "").strip()
    default = (8, 0, "AM", 5, 0, "PM")
    if " - " not in text:
        return default
    try:
        start_text, end_text = [part.strip() for part in text.split(" - ", 1)]

        def parse_piece(piece):
            time_part, ampm = piece.split()
            hour_text, minute_text = time_part.split(":")
            return int(hour_text), int(minute_text), ampm.upper()

        sh, sm, sap = parse_piece(start_text)
        eh, em, eap = parse_piece(end_text)
        return sh, sm, sap, eh, em, eap
    except Exception:
        return default


def format_time_range(start_hour, start_minute, start_ampm, end_hour, end_minute, end_ampm):
    return (
        f"{int(start_hour)}:{int(start_minute):02d} {str(start_ampm).upper()} - "
        f"{int(end_hour)}:{int(end_minute):02d} {str(end_ampm).upper()}"
    )


def normalize_search_text(text):
    value = str(text or "").strip().lower()
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    return " ".join(value.split())


def fuzzy_matches(query, *candidates):
    normalized_query = normalize_search_text(query)
    if not normalized_query:
        return True

    normalized_candidates = [normalize_search_text(item) for item in candidates if item]
    if any(normalized_query in item for item in normalized_candidates):
        return True

    query_parts = normalized_query.split()
    for item in normalized_candidates:
        item_parts = item.split()
        if all(
            any(
                part in token
                or difflib.SequenceMatcher(None, part, token).ratio() >= 0.72
                for token in item_parts
            )
            for part in query_parts
        ):
            return True

    return any(
        difflib.SequenceMatcher(None, normalized_query, item).ratio() >= 0.62
        for item in normalized_candidates
    )


class ScheduleSetupPage(ctk.CTkFrame):
    def __init__(
        self,
        master,
        current_user=None,
        current_role=None,
        current_department=None,
        current_team=None,
    ):
        super().__init__(master, fg_color=BG_MAIN)

        self.current_user = current_user or ""
        self.current_role = str(current_role or "").strip().lower()
        self.current_department = current_department or "Technical Support"
        self.current_team = current_team or "General"

        self.selected_department = (
            self.current_department
            if self.current_department in DEPARTMENTS
            else "Technical Support"
        )
        self.selected_team = self.current_team if self.current_team else "General"

        self.employee_data = []
        self.filtered_data = []
        self.data_loaded = False

        self.build_ui()
        self.render_empty_hint()

    def can_manage_setup(self):
        return self.current_role in [
            "admin",
            "management",
            "hr",
            "leader",
            "ts leader",
            "sale leader",
            "mt leader",
            "cs leader",
        ]

    def can_manage_target(self, department, team):
        role = self.current_role
        cur_dept = str(self.current_department).strip().lower()
        cur_team = str(self.current_team).strip()
        tgt_dept = str(department).strip().lower()
        tgt_team = str(team).strip()

        if role in ["admin", "management", "hr", "leader"]:
            return True
        if role in ["ts leader", "sale leader", "mt leader", "cs leader"]:
            if cur_dept != tgt_dept:
                return False
            if tgt_dept == "sale team":
                return cur_team == tgt_team
            return True
        return False

    def _get_team_values(self, department):
        if department == "Sale Team":
            return ["Team 1", "Team 2", "Team 3"]
        return ["General"]

    def build_ui(self):
        self.pack(fill="both", expand=True)

        top_card = ctk.CTkFrame(
            self,
            fg_color=BG_CARD,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
        )
        top_card.pack(fill="x", padx=8, pady=(0, 10))

        ctk.CTkLabel(
            top_card,
            text="Schedule Setup",
            font=("Segoe UI", 22, "bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, padx=18, pady=(14, 4), sticky="w")

        ctk.CTkLabel(
            top_card,
            text="Manage employee schedule configuration, display names, and active status.",
            font=("Segoe UI", 12),
            text_color=TEXT_SUB,
        ).grid(row=1, column=0, columnspan=10, padx=18, pady=(0, 12), sticky="w")

        ctk.CTkLabel(top_card, text="Department", text_color=TEXT_SUB).grid(
            row=2, column=0, padx=(18, 6), pady=(0, 10), sticky="w"
        )
        self.department_combo = ctk.CTkComboBox(
            top_card,
            values=DEPARTMENTS,
            width=180,
            command=self._on_department_change,
            fg_color="#f0e8d8",
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            text_color=TEXT_MAIN,
        )
        self.department_combo.grid(row=2, column=1, padx=(0, 14), pady=(0, 10), sticky="w")
        self.department_combo.set(self.selected_department)

        ctk.CTkLabel(top_card, text="Team", text_color=TEXT_SUB).grid(
            row=2, column=2, padx=(0, 6), pady=(0, 10), sticky="w"
        )
        self.team_combo = ctk.CTkComboBox(
            top_card,
            values=self._get_team_values(self.selected_department),
            width=120,
            fg_color="#f0e8d8",
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            text_color=TEXT_MAIN,
        )
        self.team_combo.grid(row=2, column=3, padx=(0, 14), pady=(0, 10), sticky="w")
        self.team_combo.set(self.selected_team)

        self.load_button = ctk.CTkButton(
            top_card,
            text="Load Employees",
            width=130,
            fg_color=BTN_PRIMARY,
            hover_color=BTN_PRIMARY_HOVER,
            command=self.load_data,
        )
        self.load_button.grid(row=2, column=4, padx=(0, 10), pady=(0, 10))

        self.add_button = ctk.CTkButton(
            top_card,
            text="Add Employee",
            width=140,
            fg_color=BTN_DARK,
            hover_color=BTN_DARK_HOVER,
            command=self.open_add_window,
        )
        self.add_button.grid(row=2, column=5, padx=(0, 18), pady=(0, 10))

        ctk.CTkLabel(top_card, text="Search", text_color=TEXT_SUB).grid(
            row=3, column=0, padx=(18, 6), pady=(0, 14), sticky="w"
        )
        self.search_entry = ctk.CTkEntry(
            top_card,
            width=220,
            height=34,
            fg_color="#f0e8d8",
            border_color=BORDER,
            text_color=TEXT_MAIN,
            placeholder_text="Bao / Bảo / bo / hao ...",
        )
        self.search_entry.grid(row=3, column=1, padx=(0, 14), pady=(0, 14), sticky="w")
        self.search_entry.bind("<KeyRelease>", lambda e: self.apply_filters())

        ctk.CTkLabel(top_card, text="Status", text_color=TEXT_SUB).grid(
            row=3, column=2, padx=(0, 6), pady=(0, 14), sticky="w"
        )
        self.status_segment = ctk.CTkSegmentedButton(
            top_card,
            values=["Active", "Inactive", "All"],
            fg_color="#ead8bd",
            selected_color=BTN_PRIMARY,
            selected_hover_color=BTN_PRIMARY_HOVER,
            unselected_color="#f0e8d8",
            unselected_hover_color="#e8dcc7",
            text_color=TEXT_MAIN,
            command=lambda _: self.apply_filters(),
        )
        self.status_segment.grid(row=3, column=3, columnspan=2, padx=(0, 14), pady=(0, 14), sticky="w")
        self.status_segment.set("All")

        body = ctk.CTkFrame(
            self,
            fg_color=BG_CARD,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
        )
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0)
        body.grid_rowconfigure(0, weight=1)

        self.list_frame = ctk.CTkScrollableFrame(body, fg_color="transparent")
        self.list_frame.grid(row=0, column=0, sticky="nsew", padx=(12, 8), pady=12)

        note_frame = ctk.CTkFrame(
            body,
            fg_color=BG_PANEL,
            corner_radius=16,
            border_width=1,
            border_color=BORDER,
            width=290,
        )
        note_frame.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
        note_frame.grid_propagate(False)

        notes = [
            "Use Load Employees to retrieve the latest employee list on demand.",
            "Search supports approximate matching and does not require exact spelling.",
            "Newly approved user accounts appear here first as Inactive for schedule setup.",
            "Only Active employees are available in Work Schedule and other schedule views.",
            "Display Name is prioritized for schedule rendering and accented name formatting.",
        ]

        ctk.CTkLabel(
            note_frame,
            text="Notes",
            font=("Segoe UI", 16, "bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w", padx=16, pady=(16, 10))

        for note in notes:
            ctk.CTkLabel(
                note_frame,
                text=f"- {note}",
                justify="left",
                wraplength=245,
                text_color=TEXT_SUB,
                font=("Segoe UI", 12),
            ).pack(anchor="w", padx=16, pady=4)

        if not self.can_manage_setup():
            self.add_button.configure(state="disabled")

    def _on_department_change(self, value):
        self.selected_department = value
        teams = self._get_team_values(value)
        self.team_combo.configure(values=teams)
        self.team_combo.set(teams[0])

    def load_data(self):
        self.selected_department = self.department_combo.get().strip()
        self.selected_team = self.team_combo.get().strip()

        result = get_schedule_setup_employees_api(
            action_by=self.current_user,
            department=self.selected_department,
            team=self.selected_team,
        )
        if not result.get("success"):
            messagebox.showerror(
                "Load Error",
                result.get("message", "Unable to load employees."),
            )
            return

        self.employee_data = sorted(
            result.get("data", []),
            key=lambda item: str(item.get("username", "")).lower(),
        )
        self.data_loaded = True
        self.apply_filters()

    def apply_filters(self):
        if not self.data_loaded:
            self.render_empty_hint()
            return

        self.selected_department = self.department_combo.get().strip()
        self.selected_team = self.team_combo.get().strip()
        search_value = self.search_entry.get().strip()
        status_value = self.status_segment.get().strip()

        filtered = []
        for item in self.employee_data:
            dept = str(item.get("department", "Technical Support")).strip()
            team = str(item.get("team", "General")).strip() or "General"
            active = bool(item.get("active", True))

            if status_value == "Active" and not active:
                continue
            if status_value == "Inactive" and active:
                continue
            if dept != self.selected_department:
                continue
            if dept == "Sale Team" and team != self.selected_team:
                continue
            if not self.can_manage_target(dept, team):
                continue
            if not fuzzy_matches(
                search_value,
                item.get("username", ""),
                item.get("display_name", ""),
                item.get("full_name", ""),
                dept,
                team,
            ):
                continue
            filtered.append(item)

        self.filtered_data = filtered
        self.render_list()

    def clear_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

    def render_empty_hint(self):
        self.clear_list()
        ctk.CTkLabel(
            self.list_frame,
            text="Select a department, then click 'Load Employees' to retrieve the employee list.",
            text_color=TEXT_SUB,
            font=("Segoe UI", 14),
        ).pack(pady=30)

    def render_list(self):
        self.clear_list()

        if not self.can_manage_setup():
            ctk.CTkLabel(
                self.list_frame,
                text="You do not have permission to access Schedule Setup.",
                text_color=TEXT_SUB,
                font=("Segoe UI", 14),
            ).pack(pady=30)
            return

        if not self.filtered_data:
            ctk.CTkLabel(
                self.list_frame,
                text="No employees match the current filters.",
                text_color=TEXT_SUB,
                font=("Segoe UI", 14),
            ).pack(pady=30)
            return

        for item in self.filtered_data:
            self._create_employee_card(item)

    def _create_meta_chip(self, parent, text, fg="#efe4d2", text_color=TEXT_SUB):
        chip = ctk.CTkLabel(
            parent,
            text=text,
            fg_color=fg,
            text_color=text_color,
            corner_radius=10,
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=4,
        )
        chip.pack(side="left", padx=(0, 8))

    def _create_employee_card(self, item):
        card = ctk.CTkFrame(
            self.list_frame,
            fg_color="#f7f0e6",
            corner_radius=16,
            border_width=1,
            border_color=BORDER,
        )
        card.pack(fill="x", padx=6, pady=6)
        card.grid_columnconfigure(0, weight=1)

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        top_row.grid_columnconfigure(0, weight=1)

        name_block = ctk.CTkFrame(top_row, fg_color="transparent")
        name_block.grid(row=0, column=0, sticky="w")

        username = item.get("username", "")
        display_name = item.get("display_name", "")
        full_name = item.get("full_name", "")
        active = bool(item.get("active", True))

        primary_name = display_name or full_name or username
        secondary_name = username if primary_name != username else (full_name or "")

        ctk.CTkLabel(
            name_block,
            text=primary_name,
            text_color=TEXT_MAIN,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")

        if secondary_name:
            ctk.CTkLabel(
                name_block,
                text=secondary_name,
                text_color=TEXT_SUB,
                font=("Segoe UI", 11),
            ).pack(anchor="w", pady=(2, 0))

        action_frame = ctk.CTkFrame(top_row, fg_color="transparent")
        action_frame.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(
            action_frame,
            text="Edit",
            width=96,
            height=32,
            fg_color=BTN_PRIMARY,
            hover_color=BTN_PRIMARY_HOVER,
            command=lambda data=item: self.open_edit_window(data),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            action_frame,
            text="Inactive" if active else "Active",
            width=96,
            height=32,
            fg_color=BTN_DANGER,
            hover_color=BTN_DANGER_HOVER,
            command=lambda user=username, is_active=active: self.toggle_employee_active(user, is_active),
        ).pack(side="left")

        meta_row = ctk.CTkFrame(card, fg_color="transparent")
        meta_row.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 6))

        self._create_meta_chip(meta_row, item.get("department", "Technical Support"))
        self._create_meta_chip(meta_row, item.get("team", "General"))
        self._create_meta_chip(meta_row, item.get("shift_name", "Shift 1"))
        self._create_meta_chip(
            meta_row,
            "Active" if active else "Inactive",
            fg="#dcebd7" if active else "#f2d9d5",
            text_color="#2d6b1f" if active else "#8b2525",
        )

        detail_text = (
            f"VN: {item.get('vn_time_range') or '-'}    "
            f"US: {item.get('us_time_range') or '-'}    "
            f"Off: {', '.join(item.get('off_days', [])) if item.get('off_days') else '-'}"
        )
        ctk.CTkLabel(
            card,
            text=detail_text,
            text_color=TEXT_SUB,
            font=("Segoe UI", 11),
        ).grid(row=2, column=0, sticky="w", padx=14, pady=(0, 12))

    def open_add_window(self):
        self.open_edit_window(None)

    def open_edit_window(self, item=None):
        if not self.can_manage_setup():
            messagebox.showwarning("Access Denied", "You do not have permission to use this feature.")
            return

        win = ctk.CTkToplevel(self)
        win.title("Schedule Setup")
        win.geometry("620x860")
        win.minsize(600, 780)
        win.configure(fg_color="#f5ede0")
        apply_app_window_icon(win, self)
        win.transient(self)
        win.grab_set()

        outer = ctk.CTkFrame(
            win,
            fg_color=BG_CARD,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
        )
        outer.pack(fill="both", expand=True, padx=14, pady=14)

        card = ctk.CTkScrollableFrame(
            outer,
            fg_color="transparent",
            corner_radius=0,
        )
        card.pack(fill="both", expand=True, padx=4, pady=4)

        fields = {}
        time_controls = {}

        def create_label(text):
            ctk.CTkLabel(
                card,
                text=text,
                text_color=TEXT_SUB,
                font=("Segoe UI", 12),
            ).pack(anchor="w", padx=20, pady=(12, 4))

        def create_entry(key, value="", state="normal"):
            entry = ctk.CTkEntry(
                card,
                height=36,
                fg_color="#f0e8d8",
                border_color=BORDER,
                text_color=TEXT_MAIN,
            )
            entry.pack(fill="x", padx=20)
            entry.insert(0, value)
            entry.configure(state=state)
            fields[key] = entry
            return entry

        def create_time_picker(key, value=""):
            container = ctk.CTkFrame(card, fg_color="transparent")
            container.pack(fill="x", padx=20)

            sh, sm, sap, eh, em, eap = parse_time_range(value)

            start_hour = ctk.CTkComboBox(container, values=[str(i) for i in range(1, 13)], width=72, fg_color="#f0e8d8", border_color=BORDER, button_color=BTN_PRIMARY, button_hover_color=BTN_PRIMARY_HOVER, text_color=TEXT_MAIN)
            start_minute = ctk.CTkComboBox(container, values=["00", "15", "30", "45"], width=72, fg_color="#f0e8d8", border_color=BORDER, button_color=BTN_PRIMARY, button_hover_color=BTN_PRIMARY_HOVER, text_color=TEXT_MAIN)
            start_ampm = ctk.CTkComboBox(container, values=["AM", "PM"], width=72, fg_color="#f0e8d8", border_color=BORDER, button_color=BTN_PRIMARY, button_hover_color=BTN_PRIMARY_HOVER, text_color=TEXT_MAIN)
            end_hour = ctk.CTkComboBox(container, values=[str(i) for i in range(1, 13)], width=72, fg_color="#f0e8d8", border_color=BORDER, button_color=BTN_PRIMARY, button_hover_color=BTN_PRIMARY_HOVER, text_color=TEXT_MAIN)
            end_minute = ctk.CTkComboBox(container, values=["00", "15", "30", "45"], width=72, fg_color="#f0e8d8", border_color=BORDER, button_color=BTN_PRIMARY, button_hover_color=BTN_PRIMARY_HOVER, text_color=TEXT_MAIN)
            end_ampm = ctk.CTkComboBox(container, values=["AM", "PM"], width=72, fg_color="#f0e8d8", border_color=BORDER, button_color=BTN_PRIMARY, button_hover_color=BTN_PRIMARY_HOVER, text_color=TEXT_MAIN)

            start_hour.set(str(sh))
            start_minute.set(f"{sm:02d}")
            start_ampm.set(sap)
            end_hour.set(str(eh))
            end_minute.set(f"{em:02d}")
            end_ampm.set(eap)

            start_hour.pack(side="left")
            start_minute.pack(side="left", padx=(6, 0))
            start_ampm.pack(side="left", padx=(6, 12))
            ctk.CTkLabel(container, text="to", text_color=TEXT_SUB).pack(side="left", padx=(0, 12))
            end_hour.pack(side="left")
            end_minute.pack(side="left", padx=(6, 0))
            end_ampm.pack(side="left", padx=(6, 0))

            time_controls[key] = {
                "start_hour": start_hour,
                "start_minute": start_minute,
                "start_ampm": start_ampm,
                "end_hour": end_hour,
                "end_minute": end_minute,
                "end_ampm": end_ampm,
            }

        def get_time_picker_value(key):
            parts = time_controls[key]
            return format_time_range(
                parts["start_hour"].get(),
                parts["start_minute"].get(),
                parts["start_ampm"].get(),
                parts["end_hour"].get(),
                parts["end_minute"].get(),
                parts["end_ampm"].get(),
            )

        create_label("Username")
        create_entry(
            "username",
            "" if not item else item.get("username", ""),
            state="disabled" if item else "normal",
        )

        create_label("Display Name")
        create_entry("display_name", "" if not item else item.get("display_name", ""))

        create_label("Current Name")
        create_entry("backend_full_name", "" if not item else item.get("full_name", ""), state="disabled")

        create_label("Department")
        department_combo = ctk.CTkComboBox(
            card,
            values=DEPARTMENTS,
            fg_color="#f0e8d8",
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            text_color=TEXT_MAIN,
        )
        department_combo.pack(fill="x", padx=20)
        department_combo.set(item.get("department", self.selected_department) if item else self.selected_department)

        create_label("Team")
        team_combo = ctk.CTkComboBox(
            card,
            values=self._get_team_values(department_combo.get()),
            fg_color="#f0e8d8",
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            text_color=TEXT_MAIN,
        )
        team_combo.pack(fill="x", padx=20)
        team_combo.set(item.get("team", "General") if item else self.selected_team)

        def on_department_change(selected_department):
            teams = self._get_team_values(selected_department)
            team_combo.configure(values=teams)
            if team_combo.get() not in teams:
                team_combo.set(teams[0])
        
        shift_label = ctk.CTkLabel(
            card,
            text="Shift",
            text_color=TEXT_SUB,
            font=("Segoe UI", 12),
        )
        shift_combo = ctk.CTkComboBox(
            card,
            values=SHIFT_VALUES,
            fg_color="#f0e8d8",
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            text_color=TEXT_MAIN,
        )
        shift_combo.set(item.get("shift_name", "Shift 1") if item else "Shift 1")

        def render_shift_visibility(selected_department):
            shift_label.pack_forget()
            shift_combo.pack_forget()
            if uses_shift_setup(selected_department):
                shift_label.pack(anchor="w", padx=20, pady=(12, 4))
                shift_combo.pack(fill="x", padx=20)

        def on_department_change(selected_department):
            teams = self._get_team_values(selected_department)
            team_combo.configure(values=teams)
            if team_combo.get() not in teams:
                team_combo.set(teams[0])
            render_shift_visibility(selected_department)

        department_combo.configure(command=on_department_change)
        on_department_change(department_combo.get())

        create_label("VN Time")
        create_time_picker("vn_time_range", "" if not item else item.get("vn_time_range", ""))

        create_label("US Time")
        create_time_picker("us_time_range", "" if not item else item.get("us_time_range", ""))

        create_label("Off Days")
        off_day_frame = ctk.CTkFrame(card, fg_color="transparent")
        off_day_frame.pack(fill="x", padx=20)
        off_day_vars = {}
        existing_off_days = set(item.get("off_days", [])) if item else set()

        for idx, day in enumerate(DAY_ORDER):
            var = ctk.BooleanVar(value=day in existing_off_days)
            off_day_vars[day] = var
            ctk.CTkCheckBox(
                off_day_frame,
                text=day,
                variable=var,
                text_color=TEXT_MAIN,
                fg_color=BTN_PRIMARY,
                hover_color=BTN_PRIMARY_HOVER,
            ).grid(row=idx // 4, column=idx % 4, padx=8, pady=6, sticky="w")

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(22, 18))

        def save_employee():
            username = fields["username"].get().strip()
            display_name = fields["display_name"].get().strip()
            department = department_combo.get().strip()
            team = team_combo.get().strip()
            off_days = [day for day, var in off_day_vars.items() if var.get()]

            if not username:
                messagebox.showerror("Error", "Username is required.")
                return
            if len(off_days) != 2:
                messagebox.showerror("Error", "Please select exactly 2 fixed off days.")
                return
            if not self.can_manage_target(department, team):
                messagebox.showerror("Access Denied", "You do not have permission to configure this employee.")
                return

            result = save_schedule_setup_employee_api(
                {
                    "username": username,
                    "display_name": display_name,
                    "department": department,
                    "team": team,
                    "shift_name": shift_combo.get().strip() if shift_combo is not None else "Shift 1",
                    "vn_time_range": get_time_picker_value("vn_time_range"),
                    "us_time_range": get_time_picker_value("us_time_range"),
                    "off_days": off_days,
                    "action_by": self.current_user,
                }
            )
            if not result.get("success"):
                messagebox.showerror(
                    "Save Error",
                    result.get("message", "Unable to save employee setup."),
                )
                return

            win.destroy()
            messagebox.showinfo(
                "Saved",
                result.get("message", "Employee schedule setup has been saved successfully."),
            )
            self.load_data()

        ctk.CTkButton(
            btn_row,
            text="Save",
            width=120,
            fg_color=BTN_PRIMARY,
            hover_color=BTN_PRIMARY_HOVER,
            command=save_employee,
        ).pack(side="left")

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=120,
            fg_color=BTN_DARK,
            hover_color=BTN_DARK_HOVER,
            command=win.destroy,
        ).pack(side="right")

    def toggle_employee_active(self, username, currently_active):
        item = next(
            (row for row in self.employee_data if str(row.get("username", "")).strip() == username),
            None,
        )
        if not item:
            return
        if not self.can_manage_target(item.get("department", ""), item.get("team", "General")):
            messagebox.showerror("Access Denied", "You do not have permission to update this employee.")
            return

        action_text = "disable" if currently_active else "enable"
        if not messagebox.askyesno("Confirm", f"Do you want to set '{username}' to {action_text}?"):
            return

        result = set_schedule_setup_active_api(username, not currently_active, self.current_user)
        if not result.get("success"):
            messagebox.showerror(
                "Update Error",
                result.get("message", "Unable to update employee status."),
            )
            return

        self.load_data()
