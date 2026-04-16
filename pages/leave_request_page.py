import customtkinter as ctk


class LeaveRequestPage(ctk.CTkFrame):
    def __init__(self, master, current_user=None, current_role=None):
        super().__init__(master, fg_color="transparent")

        self.current_user = current_user
        self.current_role = current_role

        title = ctk.CTkLabel(
            self,
            text="Create Leave Request",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#2b1d0e",
        )
        title.pack(anchor="w", padx=20, pady=(20, 10))

        note = ctk.CTkLabel(
            self,
            text="This page will be used to create leave requests in English.",
            font=ctk.CTkFont(size=14),
            text_color="#6b5a4a",
        )
        note.pack(anchor="w", padx=20, pady=(0, 20))

        form_frame = ctk.CTkFrame(self, corner_radius=16, fg_color="#f5f1ea")
        form_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.reason_entry = ctk.CTkTextbox(form_frame, height=180, corner_radius=12)
        self.reason_entry.pack(fill="x", padx=20, pady=(20, 10))

        self.preview_box = ctk.CTkTextbox(form_frame, height=220, corner_radius=12)
        self.preview_box.pack(fill="both", expand=True, padx=20, pady=(10, 10))

        self.generate_button = ctk.CTkButton(
            form_frame, text="Generate Leave Request", command=self.generate_request
        )
        self.generate_button.pack(padx=20, pady=(0, 20), anchor="e")

    def generate_request(self):
        reason = self.reason_entry.get("1.0", "end").strip()

        content = f"""Subject: Leave Request

Dear Manager,

I would like to request leave from work.

Reason:
{reason if reason else "Personal reason."}

I hope for your approval.
Thank you for your understanding.

Best regards,
{self.current_user if self.current_user else "Employee"}
"""
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", content)
