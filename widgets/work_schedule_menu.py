import customtkinter as ctk


class WorkScheduleMenu(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_work_schedule=None,
        on_leave_summary=None,
        on_leave_request=None,
        current_role=None,
        width=180,
    ):
        super().__init__(master, fg_color="transparent")

        self.on_work_schedule = on_work_schedule
        self.on_leave_summary = on_leave_summary
        self.on_leave_request = on_leave_request
        self.current_role = current_role
        self.menu_width = width

        self.popup = None

        self.main_button = ctk.CTkButton(
            self,
            text="Work Schedule",
            width=self.menu_width,
            height=42,
            corner_radius=14,
            fg_color="#4a3b32",
            hover_color="#5a483d",
            text_color="white",
            border_width=1,
            border_color="#4a3b32",
            font=("Segoe UI", 13, "bold"),
            command=self.toggle_menu,
        )
        self.main_button.pack()

    def toggle_menu(self):
        if self.popup is not None and self.popup.winfo_exists():
            self.close_menu()
        else:
            self.open_menu()

    def open_menu(self):
        self.close_menu()

        root = self.winfo_toplevel()

        btn_x = self.main_button.winfo_rootx()
        btn_y = self.main_button.winfo_rooty()
        btn_h = self.main_button.winfo_height()

        self.popup = ctk.CTkToplevel(root)
        self.popup.overrideredirect(True)
        self.popup.attributes("-topmost", True)
        self.popup.configure(fg_color="transparent")

        x = btn_x
        y = btn_y + btn_h + 6
        self.popup.geometry(f"+{x}+{y}")

        menu_frame = ctk.CTkFrame(
            self.popup,
            width=self.menu_width,
            corner_radius=12,
            fg_color="#d8cfb0",
            border_width=1,
            border_color="#7a5a3a",
        )
        menu_frame.pack()

        btn_work_schedule = ctk.CTkButton(
            menu_frame,
            text="Work Schedule",
            width=self.menu_width - 16,
            height=34,
            corner_radius=10,
            fg_color="#bfb58f",
            hover_color="#a89e79",
            text_color="#2b1d0e",
            anchor="w",
            command=self.handle_work_schedule,
        )
        btn_work_schedule.pack(padx=8, pady=(8, 4), fill="x")

        if self.current_role in ["Admin", "Management", "HR", "Accountant", "Leader"]:
            btn_leave_summary = ctk.CTkButton(
                menu_frame,
                text="Monthly Leave Summary",
                width=self.menu_width - 16,
                height=34,
                corner_radius=10,
                fg_color="#bfb58f",
                hover_color="#a89e79",
                text_color="#2b1d0e",
                anchor="w",
                command=self.handle_leave_summary,
            )
            btn_leave_summary.pack(padx=8, pady=4, fill="x")

        btn_leave_request = ctk.CTkButton(
            menu_frame,
            text="Create Leave Request",
            width=self.menu_width - 16,
            height=34,
            corner_radius=10,
            fg_color="#bfb58f",
            hover_color="#a89e79",
            text_color="#2b1d0e",
            anchor="w",
            command=self.handle_leave_request,
        )
        btn_leave_request.pack(padx=8, pady=(4, 8), fill="x")

        self.popup.bind("<FocusOut>", lambda e: self.close_menu())

        try:
            self.popup.focus_force()
        except Exception:
            pass

    def close_menu(self):
        if self.popup is not None:
            try:
                self.popup.destroy()
            except Exception:
                pass
            self.popup = None

    def handle_work_schedule(self):
        self.close_menu()
        if self.on_work_schedule:
            self.on_work_schedule()

    def handle_leave_summary(self):
        self.close_menu()
        if self.on_leave_summary:
            self.on_leave_summary()

    def handle_leave_request(self):
        self.close_menu()
        if self.on_leave_request:
            self.on_leave_request()
