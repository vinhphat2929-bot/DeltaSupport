from datetime import datetime
import re

FIRST_TRAINING_TEMPLATE = [
    {
        "section_key": "devices",
        "title": "I. SET UP CÁC THIẾT BỊ",
        "subtitle": "(Trước khi set up, vào ASANA check trong mục Tracking Number xem bên mình gửi ra những thiết bị gì)",
        "rows": [
            {"kind": "normal", "step": "1", "label": "PC / Duo"},
            {"kind": "normal", "step": "2", "label": "Máy cà thẻ"},
            {"kind": "normal", "step": "3", "label": "Tablet Check-In (nếu có)"},
            {"kind": "normal", "step": "4", "label": "Printer"},
            {"kind": "normal", "step": "5", "label": "Scanner."},
            {"kind": "normal", "step": "6", "label": "Cashdraw"},
            {"kind": "normal", "step": "7", "label": "Check đã Install Google Drive chưa, và check link backup trong POS đúng thư mục chưa"},
            {"kind": "normal", "step": "8", "label": "Check ATLED Cloud / ATLED Services\nSet Automatic + Restart the services"},
            {"kind": "normal", "step": "9", "label": "Check Windows Update đã dowload và update đủ file chưa\n(Khi vào Windows update thấy đã đủ thì disable Windows Update trong Services)", "default_note": "nếu chưa thì sau khi set up, training, log router (nếu có) thì cho win update xong mới stop"},
            {"kind": "normal", "step": "10", "label": "Vào Windows Security -> Virus & Threat protection\nTắt Real-time protection & Dev Drive protection (nếu có)"},
            {"kind": "normal", "step": "11", "label": "Đo tốc độ mạng của tiệm\n(nếu mạng quá yếu thì nhớ tiệm đi dây LAN ra quầy & request ship router)"},
            {"kind": "normal", "step": "12", "label": "Xem ở quầy có sợi dây LAN nào không\n(nếu không có LAN thì kết nối wifi tiệm)"},
            {"kind": "normal", "step": "13", "label": "Check xem đang dùng nhà mạng nào, log được vào router không\n(nếu login được thì ưu tiên kết nối mạng 5G, thiết bị nào không có thì kết nối 2.4Ghz,\nkhông biết cách check thì hỏi Tech khác)\n(Trường hợp log-in được vào router thì log-in và Setup IP sau khi hoàn tất buổi 1st Training)"},
            {"kind": "group", "label": "CHECK TRÊN MÁY CÀ THẺ"},
            {"kind": "normal", "step": "14", "label": "Schedule Reboot Time -> ON (set auto 5:00 AM)"},
            {"kind": "normal", "step": "", "label": "Screen time out -> Never"},
            {"kind": "normal", "step": "", "label": "Daydream -> OFF"},
            {"kind": "normal", "step": "", "label": "ON Dedicated device mode"},
        ],
    },
    {
        "section_key": "pos",
        "title": "II. SET UP POS",
        "subtitle": "(Phải check list setup xong trước khi vào bước này)",
        "rows": [
            {"kind": "normal", "step": "1", "label": "Check vào Show Waiting List\n(thông nhất 1 cách tính tiền đơn giản nhất cho tất cả các tiệm mới)"},
            {"kind": "normal", "step": "2", "label": "Set up thợ & lương thợ"},
            {"kind": "normal", "step": "3", "label": "Hỏi tiệm có thu tiền Supply/Hold tip/ hoặc bất kỳ tiền gì của thợ không ?\n(Nếu có thu thì hỏi tiệm muốn ăn hay muốn hiện phần thu đó)"},
            {"kind": "normal", "step": "3", "label": "Set up giờ đóng-mở cửa\n(hỏi thêm first & last booking trước bao nhiêu tiếng,\ngửi tin nhắn remind trước bao lâu)"},
            {"kind": "normal", "step": "4", "label": "Hỏi tiệm có thu tiền TAX (thuế bang) không\n(nếu thu thì thu trên cash - credit hay thu cả 2)\n(sẵn check lại rate trên POS - ASANA khớp chưa)"},
            {"kind": "normal", "step": "5", "label": "Hỏi tiệm tiền phần DISCOUNT cho khách sẽ do ai chịu"},
            {"kind": "normal", "step": "6", "label": "Hỏi tiệm cách chia turn"},
            {"kind": "normal", "step": "7", "label": "Hỏi tiệm cách tính điểm / redeem điểm"},
            {"kind": "normal", "step": "8", "label": "Set up promotion\nBirthday, Reminder, New Client (set up & giải thích cách hoạt động)"},
            {"kind": "normal", "step": "9", "label": "Tắt Slide ở trong phần check-in (discount 50%)"},
            {"kind": "normal", "step": "8", "label": "Giải đáp thêm các thắc mắc & các yêu cầu khác của tiệm\n(Nhớ NOTE lại)"},
        ],
    },
    {
        "section_key": "first_training",
        "title": "III. BẮT ĐẦU TRAINING",
        "subtitle": "(Training sau khi đã hoàn thành các bước trên)\n1st Training\n(Ở buổi đầu training, bảo tiệm chuẩn bị sẵn 1 cái thẻ để charge test và để hướng dẫn các thao tác sau Payment)\n(Nhớ lưu ý bảo tiệm chỉ charge $5 để test, và warning tiệm không được dùng thẻ cá nhân charge vào máy dây những số tiền lớn)",
        "rows": [
            {"kind": "normal", "step": "1", "label": "Hướng dẫn tiệm đầu ngày vào mở đúng App ATLED POS trên PC\n(Hướng dẫn từ màn hình Desktop -> Double tap vào ICON POS)"},
            {"kind": "normal", "step": "2", "label": "Hướng dẫn khách Checkin thợ"},
            {"kind": "normal", "step": "3", "label": "Hướng dẫn khách CheckIn Customer"},
            {"kind": "group", "label": "HƯỚNG DẪN CÁC THAO TÁC TRONG MỤC PAYMENT"},
            {"kind": "normal", "step": "4", "label": "Hướng dẫn khách CheckOut Payment\n(Hướng dẫn luôn cách tính tiền khi có nhiều thợ làm 1 ticket)"},
            {"kind": "normal", "step": "", "label": "Hướng dẫn cách Discount tính cho Owner hay Employee\n(đã set mặc định ở bước set up, nhưng hướng dẫn lại nếu cần thay đổi lúc tính tiền)"},
            {"kind": "normal", "step": "", "label": "Hướng dẫn khách AddTip, Sửa TIP, Chia TIP"},
            {"kind": "normal", "step": "", "label": "Hướng dẫn tiệm đổi qua thợ khác khi tính tiền sai thợ"},
            {"kind": "normal", "step": "", "label": "Hướng dẫn Sale / Redeem Gift Card"},
            {"kind": "normal", "step": "", "label": "Hướng dẫn check điểm / redeem điểm"},
            {"kind": "normal", "step": "5", "label": "Hướng dẫn đặt lịch hẹn Appointment"},
            {"kind": "normal", "step": "6", "label": "Check xem đã có Data Cus + Gift chưa"},
            {"kind": "normal", "step": "7", "label": "Hướng dẫn tiệm những cách liên hệ Technical Support:\n1: Trường hợp cần hỗ trợ gấp -> Gọi thẳng vào Hotline (có dán trên máy và ấn phím 2)\n2: Cần hỗ trợ bất kỳ thông tin nào, không gấp -> Bấm nút Support ngoài giao diện chính\nDùng lời nói để tạo sự yên tâm cho tiệm là trong quá trình đi với Công ty mình thì luôn có người hỗ trợ từ lúc tiệm mở cửa đến lúc đóng cửa. Cần hỗ trợ gì cứ liên hệ."},
            {"kind": "normal", "step": "8", "label": "Done 1st Training\nGiải đáp thêm các thắc mắc & các yêu cầu khác của tiệm\nHẹn thời gian liên hệ lại để 2nd Training\n(sau buổi đầu thì hầu như tiệm đã có thể sử dụng, tiệm làm quen thao tác dần và hướng dẫn liên hệ số HOTLINE của Tech)\n(Nhớ NOTE lại)"},
        ],
    },
]

SECOND_TRAINING_TEMPLATE = [
    {
        "section_key": "second_training",
        "title": "2nd Training",
        "subtitle": "",
        "rows": [
            {"kind": "normal", "step": "1", "label": "Hướng dẫn khách tạo Promotion"},
            {"kind": "normal", "step": "2", "label": "Booking Online"},
            {"kind": "normal", "step": "3", "label": "Mua SMS"},
            {"kind": "normal", "step": "4", "label": "Xem Report, tính lương cho thợ"},
            {"kind": "normal", "step": "5", "label": "Hỏi lại những thao tác ở buổi đầu xem có lấn cấn ở đâu không"},
            {"kind": "normal", "step": "6", "label": "Hướng dẫn tải app và sử dụng app ATLED REPORT"},
            {"kind": "normal", "step": "7", "label": "Done 2nd Training\nGiải đáp thêm các thắc mắc & các yêu cầu khác của tiệm\n(Nhớ NOTE lại)"},
        ],
    },
]

STATUS_META = {
    "FOLLOW": {"bg": "#2d6cdf", "text": "#ffffff"},
    "FOLLOW REQUEST": {"bg": "#2563eb", "text": "#ffffff"},
    "CHECK TRACKING NUMBER": {"bg": "#0f766e", "text": "#ffffff"},
    "SET UP & TRAINING": {"bg": "#9333ea", "text": "#ffffff"},
    "2ND TRAINING": {"bg": "#0ea5a3", "text": "#ffffff"},
    "MISS TIP / CHARGE BACK": {"bg": "#f59e0b", "text": "#2a221d"},
    "DONE": {"bg": "#ef4444", "text": "#ffffff"},
    "DEMO": {"bg": "#ec4899", "text": "#ffffff"},
}

class ProcessLogic:
    def __init__(self):
        self.status_meta = STATUS_META
        self.first_template = FIRST_TRAINING_TEMPLATE
        self.second_template = SECOND_TRAINING_TEMPLATE

    @staticmethod
    def format_phone(digits):
        if not digits: return ""
        if len(digits) <= 3: return f"({digits}"
        if len(digits) <= 6: return f"({digits[:3]}) {digits[3:]}"
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:10]}"

    @staticmethod
    def is_valid_deadline_date(date_text):
        try:
            datetime.strptime(date_text, "%d-%m-%Y")
            return True
        except ValueError: return False

    @staticmethod
    def get_confirmed_deadline_parts(date_str, time_str):
        if not time_str: return date_str, "", ""
        try:
            parsed_time = datetime.strptime(time_str, "%I:%M %p")
            return date_str, parsed_time.strftime("%I:%M"), parsed_time.strftime("%p")
        except ValueError: return date_str, "", ""

    @staticmethod
    def get_training_stage_key(task_status):
        status_value = str(task_status or "").strip().upper()
        if status_value == "2ND TRAINING": return "second"
        return "first"

    def get_training_template_sections(self, stage_key):
        normalized_stage = str(stage_key or "").strip().lower()
        if normalized_stage == "second": return self.first_template + self.second_template
        return self.first_template

    def merge_training_form_with_template(self, saved_sections, templates):
        saved_map = {}
        for section in saved_sections or []:
            section_key = str((section or {}).get("section_key", "")).strip()
            if section_key: saved_map[section_key] = section or {}
        merged_sections = []
        for template in templates:
            saved_section = saved_map.get(template["section_key"], {})
            saved_rows = saved_section.get("rows") or []
            saved_row_map = {(str((row or {}).get("step", "")).strip(), str((row or {}).get("label", "")).strip()): row or {} for row in saved_rows}
            merged_rows = []
            for template_row in template.get("rows", []):
                step_key, label_key = str(template_row.get("step", "")).strip(), str(template_row.get("label", "")).strip()
                saved_row = saved_row_map.get((step_key, label_key), {})
                merged_rows.append({"kind": str(template_row.get("kind", "normal")).strip() or "normal", "step": step_key, "label": label_key, "result": str(saved_row.get("result", "")).strip(), "note": str(saved_row.get("note", "")).strip() or str(template_row.get("default_note", "")).strip()})
            merged_sections.append({"section_key": template["section_key"], "title": template["title"], "subtitle": template.get("subtitle", ""), "rows": merged_rows})
        return merged_sections

    @staticmethod
    def get_deadline_time_slots():
        slots = []
        for hour in range(20, 24):
            for minute in (0, 30):
                slots.append(datetime(2000, 1, 1, hour, minute).strftime("%I:%M %p"))
        for hour in range(0, 11):
            for minute in (0, 30):
                slots.append(datetime(2000, 1, 1, hour, minute).strftime("%I:%M %p"))
        slots.append(datetime(2000, 1, 1, 11, 0).strftime("%I:%M %p"))
        return slots
