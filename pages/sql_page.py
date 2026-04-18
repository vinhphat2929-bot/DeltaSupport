import json
import os
import re
import uuid

import customtkinter as ctk

from services.sql_tool_service import create_sync_card_to_ticket_log_api


BG_PAGE = "#f3ede4"
BG_PANEL = "#fffaf3"
BG_PANEL_ALT = "#f7efe4"
BG_SIDEBAR = "#2b231e"
BG_SIDEBAR_INNER = "#332923"
BORDER = "#6e5102"
TEXT_DARK = "#2a221d"
TEXT_MUTED = "#705d4f"
TEXT_LIGHT = "#f5efe6"
TEXT_SUB = "#cab9a6"
BTN_IDLE = "#4a3b32"
BTN_IDLE_HOVER = "#5a483d"
BTN_ACTIVE = "#c58b42"
BTN_ACTIVE_HOVER = "#d49a50"
BTN_DANGER = "#a95a3a"
BTN_DANGER_HOVER = "#bc6947"
SUCCESS = "#2f7d4b"

GUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
SHOP_ZIP_RE = re.compile(r"^(.*\S)\s+(\d{5})$")


def get_data_file_path():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "tampos_guid_helper_data.json")


def is_guid(value: str) -> bool:
    return bool(GUID_RE.match(value.strip()))


def normalize_shop_name(value: str) -> str:
    return " ".join(value.strip().split()).lower()


def parse_shop_input(raw_text: str):
    text = " ".join(str(raw_text or "").strip().split())
    if not text:
        return None, None

    match = SHOP_ZIP_RE.match(text)
    if not match:
        return None, None

    return match.group(1).strip(), match.group(2).strip()


def load_data():
    data_file = get_data_file_path()
    if not os.path.exists(data_file):
        return {"shops": {}, "global_used_guids": []}

    try:
        with open(data_file, "r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            return {"shops": {}, "global_used_guids": []}
        data.setdefault("shops", {})
        data.setdefault("global_used_guids", [])
        return data
    except Exception:
        return {"shops": {}, "global_used_guids": []}


def save_data(data):
    data_file = get_data_file_path()
    with open(data_file, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def ensure_shop_record(data, shop_name: str):
    key = normalize_shop_name(shop_name)
    shops = data.setdefault("shops", {})
    if key not in shops:
        shops[key] = {
            "display_name": shop_name.strip(),
            "used_guids": [],
            "removed_guids": [],
        }
    return shops[key]


def generate_guid_pool(data, shop_name: str, size: int = 50):
    shop = ensure_shop_record(data, shop_name)
    blocked = set(g.lower() for g in data.get("global_used_guids", []))
    blocked.update(g.lower() for g in shop.get("used_guids", []))
    blocked.update(g.lower() for g in shop.get("removed_guids", []))

    pool = []
    seen = set()
    while len(pool) < size:
        guid = str(uuid.uuid4()).lower()
        if guid in blocked or guid in seen:
            continue
        pool.append(guid)
        seen.add(guid)
    return pool


def build_single_check_sql(guid: str) -> str:
    return (
        "SELECT *\n"
        "FROM dbo.TAMPOS\n"
        f"WHERE CardID = '{guid}';\n\n"
        "SELECT COUNT(*) AS Cnt\n"
        "FROM dbo.TAMPOS\n"
        f"WHERE CardID = '{guid}';"
    )


def build_update_case1(card_amount: str, tip: str, l4: str, refnum: str, card_dbh_id: str) -> str:
    return (
        "UPDATE dbo.TAMPOS\n"
        f"SET CardDBHId = '{card_dbh_id}'\n"
        f"WHERE CardAmount = {card_amount}\n"
        f"  AND CardTipAmount = {tip}\n"
        f"  AND CardL4 = '{l4}'\n"
        f"  AND CardRefNum = '{refnum}';"
    )


def build_update_case2(card_id: str, tip: str, amount: str, l4: str, card_dbh_id: str, refnum: str) -> str:
    return (
        "UPDATE dbo.TAMPOS\n"
        f"SET CardAmount = {amount},\n"
        f"    CardL4 = '{l4}',\n"
        f"    CardDBHId = '{card_dbh_id}',\n"
        f"    CardRefNum = '{refnum}'\n"
        f"WHERE CardID = '{card_id}'\n"
        f"  AND CardTipAmount = {tip};"
    )


def build_select_check_case1(card_amount: str, tip: str, l4: str, refnum: str) -> str:
    return (
        "SELECT *\n"
        "FROM dbo.TAMPOS\n"
        f"WHERE CardAmount = {card_amount}\n"
        f"  AND CardTipAmount = {tip}\n"
        f"  AND CardL4 = '{l4}'\n"
        f"  AND CardRefNum = '{refnum}';"
    )


def build_select_check_case2(card_id: str, tip: str) -> str:
    return (
        "SELECT *\n"
        "FROM dbo.TAMPOS\n"
        f"WHERE CardID = '{card_id}'\n"
        f"  AND CardTipAmount = {tip};"
    )


def mark_guid_used(data, shop_name: str, guid: str):
    shop = ensure_shop_record(data, shop_name)
    used_shop = set(g.lower() for g in shop.get("used_guids", []))
    used_global = set(g.lower() for g in data.get("global_used_guids", []))
    used_shop.add(guid.lower())
    used_global.add(guid.lower())
    shop["used_guids"] = sorted(used_shop)
    data["global_used_guids"] = sorted(used_global)
    save_data(data)


def mark_guid_removed(data, shop_name: str, guid: str):
    shop = ensure_shop_record(data, shop_name)
    removed = set(g.lower() for g in shop.get("removed_guids", []))
    removed.add(guid.lower())
    shop["removed_guids"] = sorted(removed)
    save_data(data)


class TamposGuidHelperFrame(ctk.CTkFrame):
    def __init__(self, parent, current_user=None):
        super().__init__(parent, fg_color="transparent")

        self.current_user = current_user or {}
        self.data = load_data()

        self.current_selected_guid = ""
        self.current_shop_raw_text = ""
        self.current_shop_name = ""
        self.current_zip_code = ""
        self.current_ticket_number = ""
        self.current_ticket_total_amount = ""
        self.current_case_type = ""
        self.case1_form_data = {}
        self.case2_form_data = {}

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.build_ui()
        self.render_intro()

    def build_ui(self):
        self.wrapper = ctk.CTkFrame(
            self,
            fg_color=BG_PANEL,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
        )
        self.wrapper.grid(row=0, column=0, sticky="nsew")
        self.wrapper.grid_rowconfigure(1, weight=1)
        self.wrapper.grid_columnconfigure(0, weight=1)

        self.header = ctk.CTkFrame(
            self.wrapper,
            fg_color=BG_PANEL_ALT,
            corner_radius=14,
            border_width=1,
            border_color="#d8c2a6",
            height=78,
        )
        self.header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        self.header.grid_columnconfigure(0, weight=1)
        self.header.grid_propagate(False)

        self.title_label = ctk.CTkLabel(
            self.header,
            text="Sync Card to Ticket",
            font=("Segoe UI", 25, "bold"),
            text_color=TEXT_DARK,
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=18, pady=(12, 0))

        self.subtitle_label = ctk.CTkLabel(
            self.header,
            text="Paste đúng tên tiệm từ ASANA, nhập ticket number, rồi tiếp tục từng bước.",
            font=("Segoe UI", 2),
            text_color=TEXT_MUTED,
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 10))

        self.body = ctk.CTkScrollableFrame(self.wrapper, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self.body.grid_columnconfigure(0, weight=1)

    def clear_body(self):
        for widget in self.body.winfo_children():
            widget.destroy()

    def create_card(self, title, subtitle=""):
        card = ctk.CTkFrame(
            self.body,
            fg_color=BG_PANEL_ALT,
            corner_radius=16,
            border_width=1,
            border_color="#dbc9b0",
        )
        card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT_DARK,
        ).pack(anchor="w", padx=18, pady=(16, 4))

        if subtitle:
            ctk.CTkLabel(
                card,
                text=subtitle,
                font=("Segoe UI", 12),
                text_color=TEXT_MUTED,
                wraplength=860,
                justify="left",
            ).pack(anchor="w", padx=18, pady=(0, 12))

        return card

    def create_entry(self, parent, label_text, placeholder="", width=300):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 10))

        ctk.CTkLabel(
            row,
            text=label_text,
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT_DARK,
        ).pack(anchor="w", pady=(0, 6))

        entry = ctk.CTkEntry(
            row,
            width=width,
            height=40,
            placeholder_text=placeholder,
            fg_color=BG_PANEL,
            text_color=TEXT_DARK,
            border_color="#cdb89a",
        )
        entry.pack(anchor="w")
        return entry

    def create_text_entry(self, parent, label_text, placeholder="", height=72):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 10))

        ctk.CTkLabel(
            row,
            text=label_text,
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT_DARK,
        ).pack(anchor="w", pady=(0, 6))

        box = ctk.CTkTextbox(
            row,
            height=height,
            font=("Segoe UI", 13),
            fg_color=BG_PANEL,
            text_color=TEXT_DARK,
            border_width=1,
            border_color="#cdb89a",
        )
        box.pack(fill="x")
        if placeholder:
            box.insert("1.0", placeholder)
            box.configure(text_color="#8d7867")

            def handle_focus_in(event=None):
                current = box.get("1.0", "end").strip()
                if current == placeholder:
                    box.delete("1.0", "end")
                    box.configure(text_color=TEXT_DARK)

            box.bind("<FocusIn>", handle_focus_in)
        return box

    def create_sql_box(self, parent, title, content):
        box = ctk.CTkFrame(
            parent,
            fg_color=BG_PANEL,
            corner_radius=14,
            border_width=1,
            border_color="#cdb89a",
        )
        box.pack(fill="x", padx=18, pady=(0, 12))

        ctk.CTkLabel(
            box,
            text=title,
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT_DARK,
        ).pack(anchor="w", padx=14, pady=(12, 8))

        text_box = ctk.CTkTextbox(
            box,
            height=140,
            font=("Consolas", 12),
            fg_color="#fcf8f2",
            text_color=TEXT_DARK,
            border_width=1,
            border_color="#d9c8ae",
        )
        text_box.pack(fill="x", padx=14, pady=(0, 14))
        text_box.insert("1.0", content)
        text_box.configure(state="disabled")
        return text_box

    def create_summary_rows(self, parent, rows):
        summary_box = ctk.CTkFrame(
            parent,
            fg_color=BG_PANEL,
            corner_radius=14,
            border_width=1,
            border_color="#cdb89a",
        )
        summary_box.pack(fill="x", padx=18, pady=(0, 14))

        for label_text, value in rows:
            row = ctk.CTkFrame(summary_box, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=(10, 0))

            ctk.CTkLabel(
                row,
                text=f"{label_text}:",
                font=("Segoe UI", 12, "bold"),
                text_color=TEXT_DARK,
                width=150,
                anchor="w",
            ).pack(side="left")

            ctk.CTkLabel(
                row,
                text=str(value),
                font=("Segoe UI", 12),
                text_color=TEXT_MUTED,
                anchor="w",
                justify="left",
            ).pack(side="left", fill="x", expand=True)

        ctk.CTkFrame(summary_box, fg_color="transparent", height=10).pack()

    def show_message(self, parent, text, color=TEXT_MUTED):
        label = ctk.CTkLabel(
            parent,
            text=text,
            font=("Segoe UI", 12, "bold"),
            text_color=color,
            wraplength=860,
            justify="left",
        )
        label.pack(anchor="w", padx=18, pady=(0, 12))
        return label

    def validate_decimal(self, value):
        try:
            float(str(value or "").strip())
            return True
        except ValueError:
            return False

    def get_logged_in_username(self):
        return str(self.current_user.get("username", "")).strip()

    def create_log_when_get_sql(
        self,
        case_type="",
        final_guid="",
        card_dbh_id="",
        card_ref_num="",
        card_amount="",
        card_tip_amount="",
        card_l4="",
    ):
        return create_sync_card_to_ticket_log_api(
            username=self.get_logged_in_username(),
            shop_raw_text=self.current_shop_raw_text,
            shop_name=self.current_shop_name,
            zip_code=self.current_zip_code,
            ticket_number=self.current_ticket_number,
            ticket_total_amount=self.current_ticket_total_amount,
            case_type=case_type,
            final_guid=final_guid,
            card_dbh_id=card_dbh_id,
            card_ref_num=card_ref_num,
            card_amount=card_amount,
            card_tip_amount=card_tip_amount,
            card_l4=card_l4,
        )

    def render_intro(self):
        self.clear_body()

        intro = self.create_card(
            "Bắt đầu",
            "CHECK THẬT KỸ THÔNG TIN VÀ NHẬP ĐÚNG.",
        )

        flow_box = ctk.CTkTextbox(
            intro,
            height=142,
            font=("Segoe UI", 12),
            fg_color=BG_PANEL,
            text_color=TEXT_DARK,
            border_width=1,
            border_color="#d9c8ae",
        )
        flow_box.pack(fill="x", padx=18, pady=(0, 14))
        flow_box.insert(
            "1.0",
            "1. Phải nhập đúng Tên tiệm & Zipcode theo mẫu copy từ ASANA.\n"
            "2. Nhập Ticket number và tổng tiền ticket match với POS.\n"
            "3. Check và nhập thật kỹ, nếu nhập sai sẽ dẫn đến lỗi DATABASE.\n",
        )
        flow_box.configure(state="disabled")

        ctk.CTkButton(
            intro,
            text="Bắt đầu",
            width=180,
            height=42,
            corner_radius=12,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 14, "bold"),
            command=self.render_setup_form,
        ).pack(anchor="w", padx=18, pady=(0, 18))

    def render_setup_form(self):
        self.clear_body()

        card = self.create_card(
            "Thông tin ticket",
            "Paste đúng full tên tiệm copy từ Asana.",
        )

        self.shop_text_box = self.create_text_entry(
            card,
            "TÊN TIỆM",
            "Ví dụ: INSPIRE NAIL BAR Alexandria 22314",
        )
        self.ticket_number_entry = self.create_entry(card, "Ticket number", "Ví dụ: 1")
        self.ticket_total_entry = self.create_entry(card, "Tổng tiền ticket", "Ví dụ: 125.50")

        ctk.CTkButton(
            card,
            text="Đi tiếp",
            width=240,
            height=42,
            corner_radius=12,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 14, "bold"),
            command=self.handle_setup_continue,
        ).pack(anchor="w", padx=18, pady=(0, 18))

    def handle_setup_continue(self):
        shop_raw_text = " ".join(self.shop_text_box.get("1.0", "end").strip().split())
        ticket_number = self.ticket_number_entry.get().strip()
        ticket_total_amount = self.ticket_total_entry.get().strip()
        shop_name, zip_code = parse_shop_input(shop_raw_text)
        username = self.get_logged_in_username()

        errors = []
        if not username:
            errors.append("- Không lấy được username đang login")
        if not shop_raw_text:
            errors.append("- Bạn cần paste FULL TÊN & ZIP CODE tiệm")
        if not shop_name or not zip_code:
            errors.append("- Thông tin tên tiệm không hợp lệ")
        if not ticket_number:
            errors.append("- Ticket number không được để trống")
        if not self.validate_decimal(ticket_total_amount):
            errors.append("- Tổng tiền ticket phải là số")

        if errors:
            self.render_setup_form()
            error_card = self.create_card("Dữ liệu chưa đúng")
            self.show_message(error_card, "\n".join(errors), BTN_DANGER)
            return

        self.current_shop_raw_text = shop_raw_text
        self.current_shop_name = shop_name
        self.current_zip_code = zip_code
        self.current_ticket_number = ticket_number
        self.current_ticket_total_amount = ticket_total_amount

        self.render_case_picker()

    def render_case_picker(self):
        self.clear_body()

        card = self.create_card(
            "LÀM THEO CÁC BƯỚC SAU",
            "Đây là phần hướng dẫn nhanh để user biết nên xử lý theo thứ tự nào.",
        )

        self.show_message(
            card,
            f"User: {self.get_logged_in_username()} | Tiệm: {self.current_shop_name} | Zip: {self.current_zip_code} | Ticket: {self.current_ticket_number} | Total: {self.current_ticket_total_amount}",
            SUCCESS,
        )

        guide_box = ctk.CTkTextbox(
            card,
            height=110,
            font=("Segoe UI", 12),
            fg_color=BG_PANEL,
            text_color=TEXT_DARK,
            border_width=1,
            border_color="#d9c8ae",
        )
        guide_box.pack(fill="x", padx=18, pady=(0, 14))
        guide_box.insert(
            "1.0",
            "Check thông tin thẻ (filter theo CardTipAmount, CardAmount hoặc CardL4) trong TAMPOS đã có chưa.\n\n"
            "SAU ĐÓ CHỌN 1 TRONG 2 TRƯỜNG HỢP:\n"
            "- Nếu đã tìm thấy thẻ trong TAMPOS -> Qua bước tiếp theo.\n"
            "- Nếu đã đúng thông tin mà không thấy trans trong TAMPOS -> chọn 'Chưa tìm thấy trong TAMPOS' -> bấm 'Tiếp tục' -> Check GUID theo hướng dẫn.\n",
        )
        guide_box.configure(state="disabled")

        self.case_segment = ctk.CTkSegmentedButton(
            card,
            values=["Đã tìm thấy trong TAMPOS", "Chưa tìm thấy trong TAMPOS"],
            fg_color="#ddcfba",
            selected_color=BTN_ACTIVE,
            selected_hover_color=BTN_ACTIVE_HOVER,
            unselected_color="#d7c6ae",
            unselected_hover_color="#ccb797",
            text_color=TEXT_DARK,
            font=("Segoe UI", 12, "bold"),
        )
        self.case_segment.pack(anchor="w", padx=18, pady=(0, 18))
        self.case_segment.set("Đã tìm thấy trong TAMPOS")

        action_row = ctk.CTkFrame(card, fg_color="transparent")
        action_row.pack(anchor="w", padx=18, pady=(0, 18))

        ctk.CTkButton(
            action_row,
            text="Tiếp tục",
            width=160,
            height=42,
            corner_radius=12,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 14, "bold"),
            command=self.handle_case_continue,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            action_row,
            text="Back",
            width=130,
            height=42,
            corner_radius=12,
            fg_color=BTN_IDLE,
            hover_color=BTN_IDLE_HOVER,
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 14, "bold"),
            command=self.render_setup_form,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            action_row,
            text="Ticket mới",
            width=160,
            height=42,
            corner_radius=12,
            fg_color=BTN_IDLE,
            hover_color=BTN_IDLE_HOVER,
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 14, "bold"),
            command=self.reset_ticket_session,
        ).pack(side="left")

    def handle_case_continue(self):
        selected_case = self.case_segment.get()
        if selected_case == "Đã tìm thấy trong TAMPOS":
            self.current_case_type = "found_in_tampos"
            self.render_case_found_form()
        else:
            self.current_case_type = "need_new_guid"
            self.render_case_need_guid()

    def render_case_found_form(self, initial_values=None):
        self.clear_body()

        info = self.create_card(
            "Case 1: Đã tìm thấy thông tin thẻ trong TAMPOS",
            "Nhập 4 thông tin từ Credit Report trên POS, sau đó nhập CardDBHId lấy từ TAMDBH. Nếu CardDBHId sai format GUID thì không cho qua bước.",
        )
        self.show_message(
            info,
            f"Tiệm: {self.current_shop_name} | Ticket: {self.current_ticket_number} | Total: {self.current_ticket_total_amount}",
        )

        self.case1_amount = self.create_entry(info, "CardAmount", "Ví dụ: 120.50")
        self.case1_tip = self.create_entry(info, "CardTipAmount", "Ví dụ: 10")
        self.case1_l4 = self.create_entry(info, "CardL4", "4 số cuối thẻ")
        self.case1_refnum = self.create_entry(info, "CardRefNum", "Trans # trên máy cà thẻ")
        self.case1_dbhid = self.create_entry(info, "CardDBHId", "GUID DBH_MaSo")

        if initial_values:
            self.case1_amount.insert(0, initial_values.get("card_amount", ""))
            self.case1_tip.insert(0, initial_values.get("tip", ""))
            self.case1_l4.insert(0, initial_values.get("l4", ""))
            self.case1_refnum.insert(0, initial_values.get("refnum", ""))
            self.case1_dbhid.insert(0, initial_values.get("card_dbh_id", ""))

        action_row = ctk.CTkFrame(info, fg_color="transparent")
        action_row.pack(anchor="w", padx=18, pady=(0, 18))

        ctk.CTkButton(
            action_row,
            text="Review Info",
            width=180,
            height=42,
            corner_radius=12,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 14, "bold"),
            command=self.generate_case1_sql,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            action_row,
            text="Back",
            width=130,
            height=42,
            corner_radius=12,
            fg_color=BTN_IDLE,
            hover_color=BTN_IDLE_HOVER,
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 14, "bold"),
            command=self.render_case_picker,
        ).pack(side="left")

    def generate_case1_sql(self):
        card_amount = self.case1_amount.get().strip()
        tip = self.case1_tip.get().strip()
        l4 = self.case1_l4.get().strip()
        refnum = self.case1_refnum.get().strip()
        card_dbh_id = self.case1_dbhid.get().strip().lower()

        errors = []
        if not self.validate_decimal(card_amount):
            errors.append("- CardAmount phải là số")
        if not self.validate_decimal(tip):
            errors.append("- CardTipAmount phải là số")
        if not l4:
            errors.append("- CardL4 không được để trống")
        if not refnum:
            errors.append("- CardRefNum không được để trống")
        if not is_guid(card_dbh_id):
            errors.append("- CardDBHId phải đúng format GUID")

        if errors:
            self.render_case_found_form(
                {
                    "card_amount": card_amount,
                    "tip": tip,
                    "l4": l4,
                    "refnum": refnum,
                    "card_dbh_id": card_dbh_id,
                }
            )
            error_card = self.create_card("Dữ liệu chưa đúng")
            self.show_message(error_card, "\n".join(errors), BTN_DANGER)
            return

        self.case1_form_data = {
            "card_amount": card_amount,
            "tip": tip,
            "l4": l4,
            "refnum": refnum,
            "card_dbh_id": card_dbh_id,
        }
        self.render_case1_review()

    def render_case1_review(self):
        self.clear_body()

        review = self.create_card(
            "Review Before GET SQL Code",
            "Kiểm tra lại toàn bộ thông tin. Nếu đúng hết thì mới bấm GET SQL Code.",
        )

        self.show_message(
            review,
            f"Tiệm: {self.current_shop_name} | Ticket: {self.current_ticket_number} | Total: {self.current_ticket_total_amount}",
            SUCCESS,
        )
        self.create_summary_rows(
            review,
            [
                ("Case", "Found in TAMPOS"),
                ("CardAmount", self.case1_form_data.get("card_amount", "")),
                ("CardTipAmount", self.case1_form_data.get("tip", "")),
                ("CardL4", self.case1_form_data.get("l4", "")),
                ("CardRefNum", self.case1_form_data.get("refnum", "")),
                ("CardDBHId", self.case1_form_data.get("card_dbh_id", "")),
            ],
        )

        action_row = ctk.CTkFrame(review, fg_color="transparent")
        action_row.pack(anchor="w", padx=18, pady=(0, 18))

        ctk.CTkButton(
            action_row,
            text="GET SQL Code",
            width=180,
            height=42,
            corner_radius=12,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 14, "bold"),
            command=self.confirm_case1_sql,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            action_row,
            text="Back",
            width=130,
            height=42,
            corner_radius=12,
            fg_color=BTN_IDLE,
            hover_color=BTN_IDLE_HOVER,
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 14, "bold"),
            command=lambda: self.render_case_found_form(self.case1_form_data),
        ).pack(side="left")

    def confirm_case1_sql(self):
        card_amount = self.case1_form_data.get("card_amount", "")
        tip = self.case1_form_data.get("tip", "")
        l4 = self.case1_form_data.get("l4", "")
        refnum = self.case1_form_data.get("refnum", "")
        card_dbh_id = self.case1_form_data.get("card_dbh_id", "")

        log_result = self.create_log_when_get_sql(
            case_type=self.current_case_type,
            card_dbh_id=card_dbh_id,
            card_ref_num=refnum,
            card_amount=card_amount,
            card_tip_amount=tip,
            card_l4=l4,
        )

        self.clear_body()
        result = self.create_card(
            "Kết quả SQL",
            "Đây là flow UPDATE + SELECT check lại cho case đã tìm thấy thông tin thẻ trong TAMPOS.",
        )
        self.show_message(
            result,
            f"Tiệm: {self.current_shop_name} | Ticket: {self.current_ticket_number} | Total: {self.current_ticket_total_amount}",
            SUCCESS,
        )

        if not log_result.get("success"):
            self.show_message(
                result,
                f"Cảnh báo log: {log_result.get('message', 'Không ghi được log GET SQL Code.')}",
                BTN_DANGER,
            )

        self.create_sql_box(
            result,
            "UPDATE",
            build_update_case1(card_amount, tip, l4, refnum, card_dbh_id),
        )
        self.create_sql_box(
            result,
            "GET SQL Code",
            build_select_check_case1(card_amount, tip, l4, refnum),
        )
        self.render_result_actions(result)

    def render_case_need_guid(self):
        self.current_selected_guid = generate_guid_pool(self.data, self.current_shop_name, size=1)[0]
        self.render_guid_check_screen()

    def render_guid_check_screen(self):
        self.clear_body()

        card = self.create_card(
            "Check GUID",
            "COPY 2 lệnh này chạy trên SQL -> Sau đó sẽ hiện ra 2 khung kết quả.\n"
            "Khung ở trên trả dữ liệu trống và khung ở dưới trả CNT = 0 thì GUID đó DÙNG ĐƯỢC.\n"
            "KHÁC kết quả trên thì CHỌN 'KHÔNG DÙNG ĐƯỢC', tiếp tục check đến khi DÙNG ĐƯỢC.",
        )

        self.show_message(
            card,
            f"Tiệm: {self.current_shop_name} | Ticket: {self.current_ticket_number} | GUID đang check: {self.current_selected_guid}",
            SUCCESS,
        )
        self.create_sql_box(card, "SQL check GUID", build_single_check_sql(self.current_selected_guid))

        action_row = ctk.CTkFrame(card, fg_color="transparent")
        action_row.pack(anchor="w", padx=18, pady=(0, 18))

        ctk.CTkButton(
            action_row,
            text="Không dùng được",
            width=170,
            height=40,
            corner_radius=12,
            fg_color=BTN_DANGER,
            hover_color=BTN_DANGER_HOVER,
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 13, "bold"),
            command=self.handle_guid_duplicate,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            action_row,
            text="Dùng được",
            width=170,
            height=40,
            corner_radius=12,
            fg_color=SUCCESS,
            hover_color="#3f8f59",
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 13, "bold"),
            command=self.handle_guid_accepted,
        ).pack(side="left")

        ctk.CTkButton(
            action_row,
            text="Back",
            width=120,
            height=40,
            corner_radius=12,
            fg_color=BTN_IDLE,
            hover_color=BTN_IDLE_HOVER,
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 13, "bold"),
            command=self.render_case_picker,
        ).pack(side="left", padx=(8, 0))

    def handle_guid_duplicate(self):
        old_guid = self.current_selected_guid
        mark_guid_removed(self.data, self.current_shop_name, old_guid)
        self.data = load_data()

        self.current_selected_guid = generate_guid_pool(self.data, self.current_shop_name, size=1)[0]
        self.render_guid_check_screen()

        note = self.create_card("GUID đã đổi")
        self.show_message(
            note,
            f"GUID cũ {old_guid} đã bị loại. App đã tự cấp GUID mới để bạn check tiếp.",
            BTN_DANGER,
        )

    def handle_guid_accepted(self):
        self.render_case2_form()

    def render_case2_form(self, initial_values=None):
        self.clear_body()

        card = self.create_card(
            "Nhập dữ liệu để UPDATE TAMPOS",
            "GUID hợp lệ đã chọn xong, tiếp theo:\n"
            "Xổ all trans trong TAMPOS, chọn đại 1 trans, chuột phải vào ô trống đầu trang chọn COPY, sau đó kéo xuống hàng NULL, chuột phải vào ô trống đầu tiên để PASTE (tạo trans mới).\n"
            "Copy GUID đang hiện bên dưới, paste vào ô CardID của trans vừa tạo và nhập ĐÚNG SỐ TIỀN TIP vào ô CardTipAmount. Sau đó nhập các thông tin còn lại.",
        )

        self.show_message(
            card,
            f"Tiệm: {self.current_shop_name} | Ticket: {self.current_ticket_number} | GUID đã chọn: {self.current_selected_guid}",
            SUCCESS,
        )

        self.case2_card_id = self.create_entry(card, "CardID", "GUID sẽ đưa vào TAMPOS")
        self.case2_card_id.insert(0, self.current_selected_guid)
        self.case2_tip = self.create_entry(card, "CardTipAmount", "Tip hiện có trong TAMPOS")
        self.case2_amount = self.create_entry(card, "CardAmount", "Tổng tiền charge thẻ")
        self.case2_l4 = self.create_entry(card, "CardL4", "4 số cuối thẻ")
        self.case2_dbhid = self.create_entry(card, "CardDBHId", "GUID DBH_MaSo")
        self.case2_refnum = self.create_entry(card, "CardRefNum", "Trans # trên máy cà thẻ")

        if initial_values:
            self.case2_card_id.delete(0, "end")
            self.case2_card_id.insert(0, initial_values.get("card_id", self.current_selected_guid))
            self.case2_tip.insert(0, initial_values.get("tip", ""))
            self.case2_amount.insert(0, initial_values.get("amount", ""))
            self.case2_l4.insert(0, initial_values.get("l4", ""))
            self.case2_dbhid.insert(0, initial_values.get("card_dbh_id", ""))
            self.case2_refnum.insert(0, initial_values.get("refnum", ""))

        helper = ctk.CTkTextbox(
            card,
            height=92,
            font=("Segoe UI", 12),
            fg_color=BG_PANEL,
            text_color=TEXT_DARK,
            border_width=1,
            border_color="#d9c8ae",
        )
        helper.pack(fill="x", padx=18, pady=(0, 14))
        helper.insert(
            "1.0",
            "Gợi ý lấy dữ liệu:\n"
            "- Mở Credit Report trên POS để lấy CardAmount, CardL4, CardRefNum\n"
            "- Vào TAMDBH tìm thông tin ticket, sau khi filter đúng ticket thì COPY thông tin trong cột DBH_MaSo để nhập vào cột CardDBHId\n"
            "- CardRefNum là số Trans đang nằm trên máy (check trong Credit Report)",
        )
        helper.configure(state="disabled")

        action_row = ctk.CTkFrame(card, fg_color="transparent")
        action_row.pack(anchor="w", padx=18, pady=(0, 18))

        ctk.CTkButton(
            action_row,
            text="Review Info",
            width=180,
            height=42,
            corner_radius=12,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 14, "bold"),
            command=self.generate_case2_sql,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            action_row,
            text="Back",
            width=130,
            height=42,
            corner_radius=12,
            fg_color=BTN_IDLE,
            hover_color=BTN_IDLE_HOVER,
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 14, "bold"),
            command=self.render_guid_check_screen,
        ).pack(side="left")

    def generate_case2_sql(self):
        card_id = self.case2_card_id.get().strip().lower()
        tip = self.case2_tip.get().strip()
        amount = self.case2_amount.get().strip()
        l4 = self.case2_l4.get().strip()
        card_dbh_id = self.case2_dbhid.get().strip().lower()
        refnum = self.case2_refnum.get().strip()

        errors = []
        if not is_guid(card_id):
            errors.append("- CardID phải đúng format GUID")
        if not self.validate_decimal(tip):
            errors.append("- CardTipAmount phải là số")
        if not self.validate_decimal(amount):
            errors.append("- CardAmount phải là số")
        if not l4:
            errors.append("- CardL4 không được để trống")
        if not is_guid(card_dbh_id):
            errors.append("- CardDBHId phải đúng format GUID")
        if not refnum:
            errors.append("- CardRefNum không được để trống")

        if errors:
            self.render_case2_form(
                {
                    "card_id": card_id,
                    "tip": tip,
                    "amount": amount,
                    "l4": l4,
                    "card_dbh_id": card_dbh_id,
                    "refnum": refnum,
                }
            )
            error_card = self.create_card("Dữ liệu chưa đúng")
            self.show_message(error_card, "\n".join(errors), BTN_DANGER)
            return

        self.case2_form_data = {
            "card_id": card_id,
            "tip": tip,
            "amount": amount,
            "l4": l4,
            "card_dbh_id": card_dbh_id,
            "refnum": refnum,
        }
        self.render_case2_review()

    def render_case2_review(self):
        self.clear_body()

        review = self.create_card(
            "Review Before GET SQL Code",
            "Kiểm tra lại toàn bộ thông tin. Nếu đúng hết thì mới bấm GET SQL Code.",
        )

        self.show_message(
            review,
            f"Tiệm: {self.current_shop_name} | Ticket: {self.current_ticket_number} | Total: {self.current_ticket_total_amount}",
            SUCCESS,
        )
        self.create_summary_rows(
            review,
            [
                ("Case", "Need new GUID"),
                ("CardID", self.case2_form_data.get("card_id", "")),
                ("CardAmount", self.case2_form_data.get("amount", "")),
                ("CardTipAmount", self.case2_form_data.get("tip", "")),
                ("CardL4", self.case2_form_data.get("l4", "")),
                ("CardRefNum", self.case2_form_data.get("refnum", "")),
                ("CardDBHId", self.case2_form_data.get("card_dbh_id", "")),
            ],
        )

        action_row = ctk.CTkFrame(review, fg_color="transparent")
        action_row.pack(anchor="w", padx=18, pady=(0, 18))

        ctk.CTkButton(
            action_row,
            text="GET SQL Code",
            width=180,
            height=42,
            corner_radius=12,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 14, "bold"),
            command=self.confirm_case2_sql,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            action_row,
            text="Back",
            width=130,
            height=42,
            corner_radius=12,
            fg_color=BTN_IDLE,
            hover_color=BTN_IDLE_HOVER,
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 14, "bold"),
            command=lambda: self.render_case2_form(self.case2_form_data),
        ).pack(side="left")

    def confirm_case2_sql(self):
        card_id = self.case2_form_data.get("card_id", "")
        tip = self.case2_form_data.get("tip", "")
        amount = self.case2_form_data.get("amount", "")
        l4 = self.case2_form_data.get("l4", "")
        card_dbh_id = self.case2_form_data.get("card_dbh_id", "")
        refnum = self.case2_form_data.get("refnum", "")

        mark_guid_used(self.data, self.current_shop_name, card_id)
        self.data = load_data()

        log_result = self.create_log_when_get_sql(
            case_type=self.current_case_type,
            final_guid=card_id,
            card_dbh_id=card_dbh_id,
            card_ref_num=refnum,
            card_amount=amount,
            card_tip_amount=tip,
            card_l4=l4,
        )

        self.clear_body()
        result = self.create_card(
            "Kết quả SQL",
        )

        self.show_message(
            result,
            f"Tiệm: {self.current_shop_name} | Ticket: {self.current_ticket_number} | Total: {self.current_ticket_total_amount} | GUID đã lưu: {card_id}",
            SUCCESS,
        )

        if not log_result.get("success"):
            self.show_message(
                result,
                f"Cảnh báo log: {log_result.get('message', 'Không ghi được log GET SQL Code.')}",
                BTN_DANGER,
            )

        self.create_sql_box(
            result,
            "UPDATE",
            build_update_case2(card_id, tip, amount, l4, card_dbh_id, refnum),
        )
        self.create_sql_box(
            result,
            "CHẠY TIẾP LỆNH NÀY ĐỂ KIỂM TRA SYNC DATABASE THÀNH CÔNG CHƯA",
            build_select_check_case2(card_id, tip),
        )
        self.render_result_actions(result)

    def render_result_actions(self, parent):
        action_row = ctk.CTkFrame(parent, fg_color="transparent")
        action_row.pack(anchor="w", padx=18, pady=(0, 18))

        ctk.CTkButton(
            action_row,
            text="Thêm thẻ khác cho ticket này",
            width=220,
            height=42,
            corner_radius=12,
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
            font=("Segoe UI", 14, "bold"),
            command=self.render_case_picker,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            action_row,
            text="Ticket mới",
            width=160,
            height=42,
            corner_radius=12,
            fg_color=BTN_IDLE,
            hover_color=BTN_IDLE_HOVER,
            text_color=TEXT_LIGHT,
            font=("Segoe UI", 14, "bold"),
            command=self.reset_ticket_session,
        ).pack(side="left")

    def reset_ticket_session(self):
        self.current_selected_guid = ""
        self.current_shop_raw_text = ""
        self.current_shop_name = ""
        self.current_zip_code = ""
        self.current_ticket_number = ""
        self.current_ticket_total_amount = ""
        self.current_case_type = ""
        self.render_intro()


class SQLPage(ctk.CTkFrame):
    def __init__(self, parent, current_user=None):
        super().__init__(parent, fg_color="transparent")

        self.current_user = current_user or {}
        self.active_tool_button = None
        self.current_tool_frame = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.build_layout()
        self.show_tampos_guid_helper()

    def build_layout(self):
        self.sidebar = ctk.CTkFrame(
            self,
            width=220,
            fg_color=BG_SIDEBAR,
            corner_radius=18,
            border_width=1,
            border_color="#8b6b4a",
        )
        self.sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        self.sidebar.grid_propagate(False)

        sidebar_inner = ctk.CTkFrame(
            self.sidebar,
            fg_color=BG_SIDEBAR_INNER,
            corner_radius=16,
            border_width=1,
            border_color="#5f4934",
        )
        sidebar_inner.pack(fill="both", expand=True, padx=8, pady=8)

        ctk.CTkLabel(
            sidebar_inner,
            text="SQL Functions",
            font=("Segoe UI", 20, "bold"),
            text_color=TEXT_LIGHT,
        ).pack(anchor="w", padx=16, pady=(20, 6))

        ctk.CTkLabel(
            sidebar_inner,
            text="Choose function you want to use",
            font=("Segoe UI", 12),
            text_color=TEXT_SUB,
        ).pack(anchor="w", padx=16, pady=(0, 16))

        self.tampos_btn = ctk.CTkButton(
            sidebar_inner,
            text="Sync Card to Ticket",
            height=42,
            corner_radius=12,
            font=("Segoe UI", 13, "bold"),
            fg_color=BTN_IDLE,
            hover_color=BTN_IDLE_HOVER,
            text_color=TEXT_LIGHT,
            command=self.show_tampos_guid_helper,
        )
        self.tampos_btn.pack(fill="x", padx=16, pady=(0, 10))

        self.content_host = ctk.CTkFrame(
            self,
            fg_color=BG_PAGE,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
        )
        self.content_host.grid(row=0, column=1, sticky="nsew")
        self.content_host.grid_rowconfigure(0, weight=1)
        self.content_host.grid_columnconfigure(0, weight=1)

    def set_active_tool_button(self, button):
        if self.active_tool_button is not None:
            self.active_tool_button.configure(
                fg_color=BTN_IDLE,
                hover_color=BTN_IDLE_HOVER,
                text_color=TEXT_LIGHT,
            )

        button.configure(
            fg_color=BTN_ACTIVE,
            hover_color=BTN_ACTIVE_HOVER,
            text_color=TEXT_DARK,
        )
        self.active_tool_button = button

    def clear_tool_content(self):
        if self.current_tool_frame is not None:
            self.current_tool_frame.destroy()
            self.current_tool_frame = None

    def show_tampos_guid_helper(self):
        self.set_active_tool_button(self.tampos_btn)
        self.clear_tool_content()
        self.current_tool_frame = TamposGuidHelperFrame(
            self.content_host,
            current_user=self.current_user,
        )
        self.current_tool_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
