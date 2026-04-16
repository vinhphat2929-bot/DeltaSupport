import customtkinter as ctk


class SQLPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        label = ctk.CTkLabel(self, text="SQL Page (Coming Soon)")
        label.pack(pady=20)
