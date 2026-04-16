# pages/admin_approval_page.py

import customtkinter as ctk
from tkinter import messagebox
import requests

API_BASE_URL = "https://underline-steersman-crepe.ngrok-free.dev"

# ===== THEME =====
BG_MAIN = "#1a0f0b"
BG_PANEL = "#2a1812"
BG_CARD = "#40261d"
BG_INPUT = "#f6ead2"

BORDER = "#6f4b1f"
TEXT_MAIN = "#ffffff"
TEXT_SUB = "#d8c2a8"
TEXT_DARK = "#1e140f"

BTN_PRIMARY = "#a36a1f"
BTN_PRIMARY_HOVER = "#d4a64a"

BTN_APPROVE = "#2f7d32"
BTN_APPROVE_HOVER = "#3f9b44"

BTN_BLOCK = "#b23a2f"
BTN_BLOCK_HOVER = "#d24a3d"

BTN_EDIT = "#3c6ea8"
BTN_EDIT_HOVER = "#4f88cc"

BTN_LOG = "#6b4ea2"
BTN_LOG_HOVER = "#8663c7"

BTN_NEUTRAL = "#4a2f23"
BTN_NEUTRAL_HOVER = "#5f3d2e"


DEPARTMENTS = [
    "Technical Support",
    "Sale Team",
    "Office",
    "Management",
    "Customer Service",
    "Marketing Team",
]

DEFAULT_TEAMS = ["General", "Team 1", "Team 2", "Team 3"]

DEPARTMENT_ROLE_MAP = {
    "Technical Support": [
        "TS Leader",
        "TS Senior",
        "TS Junior",
        "TS Probation",
    ],
    "Sale Team": [
        "Sale Leader",
        "Sale Staff",
        "Sale Admin",
    ],
    "Office": [
        "HR",
        "Accountant",
    ],
    "Management": [
        "Management",
        "Admin",
    ],
    "Customer Service": [
        "CS Leader",
        "CS Staff",
    ],
    "Marketing Team": [
        "MT Leader",
        "MT Staff",
    ],
}


class AdminApprovalPage(ctk.CTkToplevel):
    def __init__(self, master=None, admin_name="admin"):
        super().__init__(master)

        self.admin_name = admin_name
        self.users_data = []
        self.filtered_users = []

        self.title("Admin Manager")
        self.geometry("1020x680")
        self.minsize(920, 620)
        self.configure(fg_color=BG_MAIN)

        self.transient(master)
        self.lift()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))

        self.build_ui()
        self.load_users()

    # =========================================================
    # UI
    # =========================================================
    def build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(
            self,
            fg_color=BG_PANEL,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
        )
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text="Admin Manager",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=TEXT_MAIN,
        )
        title.grid(row=0, column=0, sticky="w", padx=20, pady=(16, 4))

        subtitle = ctk.CTkLabel(
            header,
            text=f"Đăng nhập bởi admin: {self.admin_name}",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SUB,
        )
        subtitle.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 14))

        toolbar = ctk.CTkFrame(
            self,
            fg_color=BG_PANEL,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
        )
        toolbar.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        toolbar.grid_rowconfigure(1, weight=1)
        toolbar.grid_columnconfigure(0, weight=1)

        top_tools = ctk.CTkFrame(toolbar, fg_color="transparent")
        top_tools.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        top_tools.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            top_tools,
            text="Search User:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, padx=(0, 10), pady=6, sticky="w")

        self.search_entry = ctk.CTkEntry(
            top_tools,
            height=40,
            fg_color=BG_INPUT,
            text_color=TEXT_DARK,
            border_color=BORDER,
            placeholder_text="Nhập username / full name / email...",
        )
        self.search_entry.grid(row=0, column=1, padx=(0, 10), pady=6, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.apply_filters())

        self.status_filter = ctk.CTkComboBox(
            top_tools,
            values=["All", "pending", "approved", "blocked"],
            width=140,
            height=40,
            fg_color=BG_INPUT,
            text_color=TEXT_DARK,
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            dropdown_fg_color=BG_INPUT,
            dropdown_text_color=TEXT_DARK,
            command=lambda _: self.apply_filters(),
        )
        self.status_filter.set("All")
        self.status_filter.grid(row=0, column=2, padx=(0, 10), pady=6)

        self.role_filter = ctk.CTkComboBox(
            top_tools,
            values=["All"] + self.get_all_roles(),
            width=170,
            height=40,
            fg_color=BG_INPUT,
            text_color=TEXT_DARK,
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            dropdown_fg_color=BG_INPUT,
            dropdown_text_color=TEXT_DARK,
            command=lambda _: self.apply_filters(),
        )
        self.role_filter.set("All")
        self.role_filter.grid(row=0, column=3, padx=(0, 10), pady=6)

        ctk.CTkButton(
            top_tools,
            text="Reload",
            width=110,
            height=40,
            corner_radius=12,
            fg_color=BTN_PRIMARY,
            hover_color=BTN_PRIMARY_HOVER,
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.load_users,
        ).grid(row=0, column=4, pady=6)

        self.user_list_frame = ctk.CTkScrollableFrame(
            toolbar, fg_color=BG_PANEL, corner_radius=16
        )
        self.user_list_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 16))

    # =========================================================
    # HELPERS
    # =========================================================
    def get_all_roles(self):
        roles = []
        for role_list in DEPARTMENT_ROLE_MAP.values():
            roles.extend(role_list)
        return roles

    def get_roles_by_department(self, department):
        return DEPARTMENT_ROLE_MAP.get(department, ["Pending"])

    def normalize_team(self, department, team_value):
        team_value = str(team_value if team_value is not None else "").strip()
        if department == "Sale Team":
            return (
                team_value if team_value in ["Team 1", "Team 2", "Team 3"] else "Team 1"
            )
        return team_value if team_value else "General"

    def get_team_values_by_department(self, department):
        if department == "Sale Team":
            return ["Team 1", "Team 2", "Team 3"]
        return ["General"]

    # =========================================================
    # API
    # =========================================================
    def api_get(self, endpoint):
        url = f"{API_BASE_URL}{endpoint}"
        return requests.get(url, timeout=15)

    def api_put(self, endpoint, payload=None):
        url = f"{API_BASE_URL}{endpoint}"
        return requests.put(url, json=payload or {}, timeout=15)

    # =========================================================
    # DATA
    # =========================================================
    def load_users(self):
        self.clear_list()

        try:
            response = self.api_get("/admin/users")

            if response.status_code != 200:
                messagebox.showerror(
                    "API Error",
                    f"Không load được danh sách user.\nStatus: {response.status_code}\n\n{response.text}",
                )
                return

            data = response.json()
            self.users_data = data.get("users", []) if isinstance(data, dict) else []
            self.apply_filters()

        except requests.exceptions.Timeout:
            messagebox.showerror("Timeout", "API load users bị timeout.")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Connection Error", f"Lỗi kết nối API:\n{e}")
        except Exception as e:
            messagebox.showerror("Error", f"Lỗi khi load user:\n{e}")

    def apply_filters(self):
        keyword = self.search_entry.get().strip().lower()
        status_value = self.status_filter.get().strip().lower()
        role_value = self.role_filter.get().strip().lower()

        self.filtered_users = []

        for user in self.users_data:
            username = str(user.get("username", "")).lower()
            full_name = str(user.get("full_name", "")).lower()
            email = str(user.get("email", "")).lower()
            role = str(user.get("role", "")).lower()
            status = str(user.get("status", "")).lower()

            text_ok = (
                keyword in username
                or keyword in full_name
                or keyword in email
                or keyword == ""
            )

            status_ok = status_value == "all" or status == status_value
            role_ok = role_value == "all" or role == role_value.lower()

            if text_ok and status_ok and role_ok:
                self.filtered_users.append(user)

        self.render_users()

    def clear_list(self):
        for widget in self.user_list_frame.winfo_children():
            widget.destroy()

    def render_users(self):
        self.clear_list()

        if not self.filtered_users:
            ctk.CTkLabel(
                self.user_list_frame,
                text="Không có user nào phù hợp.",
                text_color=TEXT_SUB,
                font=ctk.CTkFont(size=14),
            ).pack(pady=30)
            return

        for user in self.filtered_users:
            self.create_user_card(user)

    # =========================================================
    # USER CARD
    # =========================================================
    def create_user_card(self, user):
        username = user.get("username", "")
        full_name = user.get("full_name", "")
        email = user.get("email", "")
        role = user.get("role", "")
        status = user.get("status", "pending")
        department = user.get("department", "")
        team = user.get("team", "General")
        approved_by = user.get("approved_by", "")
        approved_at = user.get("approved_at", "")

        card = ctk.CTkFrame(
            self.user_list_frame,
            fg_color=BG_CARD,
            corner_radius=16,
            border_width=1,
            border_color=BORDER,
        )
        card.pack(fill="x", padx=8, pady=8)

        card.grid_columnconfigure(0, weight=1)

        info_text = (
            f"Username: {username}\n"
            f"Full Name: {full_name}\n"
            f"Email: {email}\n"
            f"Department: {department}\n"
            f"Team: {team}\n"
            f"Role: {role}\n"
            f"Status: {status}\n"
            f"Approved By: {approved_by}\n"
            f"Approved At: {approved_at}"
        )

        info_label = ctk.CTkLabel(
            card,
            text=info_text,
            justify="left",
            anchor="w",
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(size=14),
        )
        info_label.grid(row=0, column=0, rowspan=2, sticky="w", padx=16, pady=16)

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=0, column=1, rowspan=2, sticky="e", padx=16, pady=16)

        ctk.CTkButton(
            btn_frame,
            text="View / Edit",
            width=130,
            height=36,
            corner_radius=10,
            fg_color=BTN_EDIT,
            hover_color=BTN_EDIT_HOVER,
            text_color=TEXT_MAIN,
            command=lambda u=user: self.open_edit_user_window(u),
        ).pack(pady=(0, 8))

        ctk.CTkButton(
            btn_frame,
            text="View Log",
            width=130,
            height=36,
            corner_radius=10,
            fg_color=BTN_LOG,
            hover_color=BTN_LOG_HOVER,
            text_color=TEXT_MAIN,
            command=lambda u=username: self.open_user_log_window(u),
        ).pack(pady=(0, 8))

        if str(status).lower() == "pending":
            ctk.CTkButton(
                btn_frame,
                text="Approve",
                width=130,
                height=36,
                corner_radius=10,
                fg_color=BTN_APPROVE,
                hover_color=BTN_APPROVE_HOVER,
                text_color=TEXT_MAIN,
                command=lambda u=user: self.approve_user(u),
            ).pack(pady=(0, 8))

        if str(status).lower() == "blocked":
            ctk.CTkButton(
                btn_frame,
                text="Unblock",
                width=130,
                height=36,
                corner_radius=10,
                fg_color=BTN_PRIMARY,
                hover_color=BTN_PRIMARY_HOVER,
                text_color=TEXT_MAIN,
                command=lambda u=username: self.unblock_user(u),
            ).pack()
        else:
            ctk.CTkButton(
                btn_frame,
                text="Block",
                width=130,
                height=36,
                corner_radius=10,
                fg_color=BTN_BLOCK,
                hover_color=BTN_BLOCK_HOVER,
                text_color=TEXT_MAIN,
                command=lambda u=username: self.block_user(u),
            ).pack()

    # =========================================================
    # ACTIONS
    # =========================================================
    def approve_user(self, user):
        username = user.get("username", "")
        full_name = user.get("full_name", "")
        current_department = user.get("department", "Technical Support")
        current_team = user.get("team", "General")
        current_role = user.get("role", "Pending")

        approve_win = ctk.CTkToplevel(self)
        approve_win.title(f"Approve User - {username}")
        approve_win.geometry("500x420")
        approve_win.configure(fg_color=BG_MAIN)
        approve_win.transient(self)
        approve_win.lift()
        approve_win.attributes("-topmost", True)
        approve_win.after(300, lambda: approve_win.attributes("-topmost", False))

        outer = ctk.CTkFrame(
            approve_win,
            fg_color=BG_PANEL,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
        )
        outer.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(
            outer,
            text=f"Approve User: {username}",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w", padx=20, pady=(18, 10))

        ctk.CTkLabel(
            outer,
            text=f"Full Name: {full_name}",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_SUB,
        ).pack(anchor="w", padx=20, pady=(0, 10))

        def create_label(parent, text):
            ctk.CTkLabel(
                parent,
                text=text,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=TEXT_SUB,
            ).pack(anchor="w", padx=20, pady=(8, 4))

        create_label(outer, "Department")
        department_combo = ctk.CTkComboBox(
            outer,
            values=DEPARTMENTS,
            height=40,
            fg_color=BG_INPUT,
            text_color=TEXT_DARK,
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            dropdown_fg_color=BG_INPUT,
            dropdown_text_color=TEXT_DARK,
        )
        department_combo.pack(fill="x", padx=20)

        create_label(outer, "Team")
        team_combo = ctk.CTkComboBox(
            outer,
            values=DEFAULT_TEAMS,
            height=40,
            fg_color=BG_INPUT,
            text_color=TEXT_DARK,
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            dropdown_fg_color=BG_INPUT,
            dropdown_text_color=TEXT_DARK,
        )
        team_combo.pack(fill="x", padx=20)

        create_label(outer, "Role")
        role_combo = ctk.CTkComboBox(
            outer,
            values=["Pending"],
            height=40,
            fg_color=BG_INPUT,
            text_color=TEXT_DARK,
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            dropdown_fg_color=BG_INPUT,
            dropdown_text_color=TEXT_DARK,
        )
        role_combo.pack(fill="x", padx=20)

        def on_department_change(selected_department):
            team_values = self.get_team_values_by_department(selected_department)
            team_combo.configure(values=team_values)
            team_combo.set(self.normalize_team(selected_department, current_team))

            role_values = self.get_roles_by_department(selected_department)
            role_combo.configure(values=role_values)
            if current_role in role_values:
                role_combo.set(current_role)
            else:
                role_combo.set(role_values[0])

        department_combo.set(
            current_department
            if current_department in DEPARTMENTS
            else "Technical Support"
        )
        on_department_change(department_combo.get())
        department_combo.configure(command=on_department_change)

        def do_approve():
            payload = {
                "approved_by": self.admin_name,
                "department": department_combo.get().strip(),
                "team": team_combo.get().strip(),
                "role": role_combo.get().strip(),
            }

            try:
                response = self.api_put(f"/admin/users/{username}/approve", payload)

                if response.status_code == 200:
                    messagebox.showinfo("Success", f"Đã duyệt user '{username}'.")
                    approve_win.destroy()
                    self.load_users()
                else:
                    messagebox.showerror(
                        "Approve Failed",
                        f"Không thể duyệt user.\nStatus: {response.status_code}\n\n{response.text}",
                    )
            except requests.exceptions.Timeout:
                messagebox.showerror("Timeout", "Approve user bị timeout.")
            except requests.exceptions.RequestException as e:
                messagebox.showerror("Connection Error", f"Lỗi kết nối API:\n{e}")
            except Exception as e:
                messagebox.showerror("Error", f"Lỗi khi duyệt user:\n{e}")

        btn_row = ctk.CTkFrame(outer, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(20, 12))

        ctk.CTkButton(
            btn_row,
            text="Approve User",
            height=42,
            corner_radius=12,
            fg_color=BTN_APPROVE,
            hover_color=BTN_APPROVE_HOVER,
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=do_approve,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row,
            text="Close",
            height=42,
            corner_radius=12,
            fg_color=BTN_NEUTRAL,
            hover_color=BTN_NEUTRAL_HOVER,
            text_color=TEXT_MAIN,
            command=approve_win.destroy,
        ).pack(side="left")

    def block_user(self, username):
        if not messagebox.askyesno("Confirm", f"Block user '{username}'?"):
            return

        try:
            response = self.api_put(
                f"/admin/users/{username}/block", {"blocked_by": self.admin_name}
            )

            if response.status_code == 200:
                messagebox.showinfo("Success", f"Đã block user '{username}'.")
                self.load_users()
            else:
                messagebox.showerror(
                    "Block Failed",
                    f"Không thể block user.\nStatus: {response.status_code}\n\n{response.text}",
                )
        except requests.exceptions.Timeout:
            messagebox.showerror("Timeout", "Block user bị timeout.")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Connection Error", f"Lỗi kết nối API:\n{e}")
        except Exception as e:
            messagebox.showerror("Error", f"Lỗi khi block user:\n{e}")

    def unblock_user(self, username):
        if not messagebox.askyesno("Confirm", f"Unblock user '{username}'?"):
            return

        try:
            response = self.api_put(
                f"/admin/users/{username}/unblock", {"updated_by": self.admin_name}
            )

            if response.status_code == 200:
                messagebox.showinfo("Success", f"Đã unblock user '{username}'.")
                self.load_users()
            else:
                messagebox.showerror(
                    "Unblock Failed",
                    f"Không thể unblock user.\nStatus: {response.status_code}\n\n{response.text}",
                )
        except requests.exceptions.Timeout:
            messagebox.showerror("Timeout", "Unblock user bị timeout.")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Connection Error", f"Lỗi kết nối API:\n{e}")
        except Exception as e:
            messagebox.showerror("Error", f"Lỗi khi unblock user:\n{e}")

    # =========================================================
    # EDIT USER WINDOW
    # =========================================================
    def open_edit_user_window(self, user):
        edit_win = ctk.CTkToplevel(self)
        edit_win.title(f"Edit User - {user.get('username', '')}")
        edit_win.geometry("560x760")
        edit_win.minsize(520, 640)
        edit_win.configure(fg_color=BG_MAIN)

        edit_win.transient(self)
        edit_win.lift()
        edit_win.attributes("-topmost", True)
        edit_win.after(300, lambda: edit_win.attributes("-topmost", False))

        outer = ctk.CTkFrame(
            edit_win,
            fg_color=BG_PANEL,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
        )
        outer.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(
            outer,
            text="Edit User",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w", padx=20, pady=(18, 10))

        scroll_frame = ctk.CTkScrollableFrame(
            outer, fg_color="transparent", corner_radius=0
        )
        scroll_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        content = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=4, pady=4)

        def create_label(parent, text):
            ctk.CTkLabel(
                parent,
                text=text,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=TEXT_SUB,
            ).pack(anchor="w", pady=(8, 4))

        def create_entry(parent, default_value=""):
            entry = ctk.CTkEntry(
                parent,
                height=40,
                fg_color=BG_INPUT,
                text_color=TEXT_DARK,
                border_color=BORDER,
            )
            entry.pack(fill="x")
            entry.insert(0, str(default_value if default_value is not None else ""))
            return entry

        create_label(content, "Username")
        username_entry = create_entry(content, user.get("username", ""))
        username_entry.configure(state="disabled")

        create_label(content, "Full Name")
        full_name_entry = create_entry(content, user.get("full_name", ""))

        create_label(content, "Email")
        email_entry = create_entry(content, user.get("email", ""))

        create_label(content, "Department")
        department_combo = ctk.CTkComboBox(
            content,
            values=DEPARTMENTS,
            height=40,
            fg_color=BG_INPUT,
            text_color=TEXT_DARK,
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            dropdown_fg_color=BG_INPUT,
            dropdown_text_color=TEXT_DARK,
        )
        department_combo.pack(fill="x")

        create_label(content, "Team")
        team_combo = ctk.CTkComboBox(
            content,
            values=DEFAULT_TEAMS,
            height=40,
            fg_color=BG_INPUT,
            text_color=TEXT_DARK,
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            dropdown_fg_color=BG_INPUT,
            dropdown_text_color=TEXT_DARK,
        )
        team_combo.pack(fill="x")

        create_label(content, "Role")
        role_combo = ctk.CTkComboBox(
            content,
            values=["Pending"],
            height=40,
            fg_color=BG_INPUT,
            text_color=TEXT_DARK,
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            dropdown_fg_color=BG_INPUT,
            dropdown_text_color=TEXT_DARK,
        )
        role_combo.pack(fill="x")

        create_label(content, "Status")
        status_combo = ctk.CTkComboBox(
            content,
            values=["pending", "approved", "blocked"],
            height=40,
            fg_color=BG_INPUT,
            text_color=TEXT_DARK,
            border_color=BORDER,
            button_color=BTN_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            dropdown_fg_color=BG_INPUT,
            dropdown_text_color=TEXT_DARK,
        )
        status_combo.pack(fill="x")
        status_combo.set(str(user.get("status", "pending")))

        create_label(content, "Approved By")
        approved_by_entry = create_entry(content, user.get("approved_by", ""))

        create_label(content, "Notes / Extra Info")
        notes_box = ctk.CTkTextbox(
            content,
            height=120,
            fg_color=BG_INPUT,
            text_color=TEXT_DARK,
            border_color=BORDER,
            border_width=1,
            corner_radius=10,
        )
        notes_box.pack(fill="x")
        notes_box.insert("1.0", str(user.get("notes", "")))

        current_department = user.get("department", "Technical Support")
        current_team = user.get("team", "General")
        current_role = user.get("role", "Pending")

        def on_department_change(selected_department):
            team_values = self.get_team_values_by_department(selected_department)
            team_combo.configure(values=team_values)
            team_combo.set(self.normalize_team(selected_department, current_team))

            role_values = self.get_roles_by_department(selected_department)
            role_combo.configure(values=role_values)
            if current_role in role_values:
                role_combo.set(current_role)
            else:
                role_combo.set(role_values[0])

        department_combo.set(
            current_department
            if current_department in DEPARTMENTS
            else "Technical Support"
        )
        on_department_change(department_combo.get())
        department_combo.configure(command=on_department_change)

        def save_user_changes():
            username = user.get("username", "")

            payload = {
                "full_name": full_name_entry.get().strip(),
                "email": email_entry.get().strip(),
                "department": department_combo.get().strip(),
                "team": team_combo.get().strip(),
                "role": role_combo.get().strip(),
                "status": status_combo.get().strip(),
                "approved_by": approved_by_entry.get().strip(),
                "notes": notes_box.get("1.0", "end").strip(),
                "updated_by": self.admin_name,
            }

            try:
                response = self.api_put(f"/admin/users/{username}", payload)

                if response.status_code == 200:
                    messagebox.showinfo("Success", f"Đã cập nhật user '{username}'.")
                    edit_win.destroy()
                    self.load_users()
                else:
                    messagebox.showerror(
                        "Update Failed",
                        f"Không thể cập nhật user.\nStatus: {response.status_code}\n\n{response.text}",
                    )
            except requests.exceptions.Timeout:
                messagebox.showerror("Timeout", "Update user bị timeout.")
            except requests.exceptions.RequestException as e:
                messagebox.showerror("Connection Error", f"Lỗi kết nối API:\n{e}")
            except Exception as e:
                messagebox.showerror("Error", f"Lỗi khi cập nhật user:\n{e}")

        btn_row = ctk.CTkFrame(content, fg_color="transparent")
        btn_row.pack(fill="x", pady=(16, 10))

        ctk.CTkButton(
            btn_row,
            text="Save Changes",
            height=42,
            corner_radius=12,
            fg_color=BTN_PRIMARY,
            hover_color=BTN_PRIMARY_HOVER,
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=save_user_changes,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row,
            text="Close",
            height=42,
            corner_radius=12,
            fg_color=BTN_NEUTRAL,
            hover_color=BTN_NEUTRAL_HOVER,
            text_color=TEXT_MAIN,
            command=edit_win.destroy,
        ).pack(side="left")

    # =========================================================
    # VIEW USER LOG WINDOW
    # =========================================================
    def open_user_log_window(self, username):
        log_win = ctk.CTkToplevel(self)
        log_win.title(f"User Log - {username}")
        log_win.geometry("950x620")
        log_win.configure(fg_color=BG_MAIN)

        log_win.transient(self)
        log_win.lift()
        log_win.attributes("-topmost", True)
        log_win.after(300, lambda: log_win.attributes("-topmost", False))

        wrapper = ctk.CTkFrame(
            log_win,
            fg_color=BG_PANEL,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
        )
        wrapper.pack(fill="both", expand=True, padx=18, pady=18)
        wrapper.grid_rowconfigure(1, weight=1)
        wrapper.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(wrapper, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=f"User Audit Log - {username}",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header,
            text="Reload Log",
            width=110,
            height=38,
            corner_radius=10,
            fg_color=BTN_LOG,
            hover_color=BTN_LOG_HOVER,
            text_color=TEXT_MAIN,
            command=lambda: load_logs(),
        ).grid(row=0, column=1, sticky="e")

        log_list_frame = ctk.CTkScrollableFrame(
            wrapper, fg_color=BG_PANEL, corner_radius=16
        )
        log_list_frame.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

        def clear_log_list():
            for widget in log_list_frame.winfo_children():
                widget.destroy()

        def render_log_card(log):
            action_type = log.get("action_type", "")
            field_name = log.get("field_name", "")
            old_value = log.get("old_value", "")
            new_value = log.get("new_value", "")
            action_by = log.get("action_by", "")
            action_at = log.get("action_at", "")
            note = log.get("note", "")
            log_id = log.get("log_id", "")

            card = ctk.CTkFrame(
                log_list_frame,
                fg_color=BG_CARD,
                corner_radius=14,
                border_width=1,
                border_color=BORDER,
            )
            card.pack(fill="x", padx=6, pady=6)

            content = (
                f"Log ID: {log_id}\n"
                f"Action: {action_type}\n"
                f"Field: {field_name}\n"
                f"Old Value: {old_value}\n"
                f"New Value: {new_value}\n"
                f"Action By: {action_by}\n"
                f"Action At: {action_at}\n"
                f"Note: {note}"
            )

            ctk.CTkLabel(
                card,
                text=content,
                justify="left",
                anchor="w",
                text_color=TEXT_MAIN,
                font=ctk.CTkFont(size=13),
            ).pack(fill="x", padx=14, pady=14)

        def load_logs():
            clear_log_list()

            try:
                response = self.api_get(f"/user-logs/{username}")

                if response.status_code != 200:
                    messagebox.showerror(
                        "Log Error",
                        f"Không load được log.\nStatus: {response.status_code}\n\n{response.text}",
                    )
                    return

                data = response.json()
                logs = data.get("logs", []) if isinstance(data, dict) else []

                if not logs:
                    ctk.CTkLabel(
                        log_list_frame,
                        text="User này chưa có log nào.",
                        text_color=TEXT_SUB,
                        font=ctk.CTkFont(size=14),
                    ).pack(pady=30)
                    return

                for log in logs:
                    render_log_card(log)

            except requests.exceptions.Timeout:
                messagebox.showerror("Timeout", "Load user log bị timeout.")
            except requests.exceptions.RequestException as e:
                messagebox.showerror("Connection Error", f"Lỗi kết nối API:\n{e}")
            except Exception as e:
                messagebox.showerror("Error", f"Lỗi khi load log:\n{e}")

        load_logs()
