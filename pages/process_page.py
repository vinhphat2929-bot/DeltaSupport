import customtkinter as ctk


class ProcessPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        label = ctk.CTkLabel(
            self, text="Cách xử lý (Coming Soon)", font=("Segoe UI", 20, "bold")
        )
        label.pack(pady=20)
