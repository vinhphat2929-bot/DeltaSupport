import customtkinter as ctk


class TaskReportPage(ctk.CTkFrame):
    def __init__(self, parent, title, text_dark, text_muted, panel_bg, panel_inner, border, border_soft):
        super().__init__(
            parent,
            fg_color=panel_bg,
            corner_radius=22,
            border_width=1,
            border_color=border,
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        content = ctk.CTkFrame(
            self,
            fg_color=panel_inner,
            corner_radius=18,
            border_width=1,
            border_color=border_soft,
        )
        content.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        content.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            content,
            text=title,
            font=("Segoe UI", 22, "bold"),
            text_color=text_dark,
        ).pack(anchor="w", padx=22, pady=(22, 8))

        ctk.CTkLabel(
            content,
            text=(
                "Function nay se duoc build tiep theo.\n"
                "Tam thoi minh giu san khung de sau nay gan API, bang SQL va giao dien chi tiet."
            ),
            font=("Segoe UI", 14),
            text_color=text_muted,
            justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 18))
