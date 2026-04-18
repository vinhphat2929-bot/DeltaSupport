from decimal import Decimal, InvalidOperation

from fastapi import APIRouter

from database import get_connection
from models import SyncCardToTicketLogRequest

router = APIRouter()


def normalize_text(value):
    return str(value or "").strip()


def parse_decimal_or_none(value):
    text = normalize_text(value)
    if not text:
        return None

    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


@router.post("/sync-card-to-ticket/log")
def create_sync_card_to_ticket_log(data: SyncCardToTicketLogRequest):
    conn = None
    try:
        username = normalize_text(data.username)
        shop_raw_text = normalize_text(data.shop_raw_text)
        shop_name = normalize_text(data.shop_name)
        zip_code = normalize_text(data.zip_code)
        ticket_number = normalize_text(data.ticket_number)
        ticket_total_amount = parse_decimal_or_none(data.ticket_total_amount)
        card_amount = parse_decimal_or_none(data.card_amount)
        card_tip_amount = parse_decimal_or_none(data.card_tip_amount)

        if not username:
            return {"success": False, "message": "Thiếu username"}
        if not shop_raw_text or not shop_name or not zip_code:
            return {"success": False, "message": "Thiếu thông tin tiệm"}
        if not ticket_number:
            return {"success": False, "message": "Thiếu ticket number"}
        if normalize_text(data.ticket_total_amount) and ticket_total_amount is None:
            return {"success": False, "message": "Ticket total amount không hợp lệ"}
        if normalize_text(data.card_amount) and card_amount is None:
            return {"success": False, "message": "CardAmount không hợp lệ"}
        if normalize_text(data.card_tip_amount) and card_tip_amount is None:
            return {"success": False, "message": "CardTipAmount không hợp lệ"}

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.SyncCardToTicketLog
            (
                Username,
                ShopRawText,
                ShopName,
                ZipCode,
                TicketNumber,
                TicketTotalAmount,
                CaseType,
                FinalGUID,
                CardDBHId,
                CardRefNum,
                CardAmount,
                CardTipAmount,
                CardL4
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                shop_raw_text,
                shop_name,
                zip_code,
                ticket_number,
                ticket_total_amount,
                normalize_text(data.case_type),
                normalize_text(data.final_guid),
                normalize_text(data.card_dbh_id),
                normalize_text(data.card_ref_num),
                card_amount,
                card_tip_amount,
                normalize_text(data.card_l4),
            ),
        )

        conn.commit()
        return {"success": True}

    except Exception as e:
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()
