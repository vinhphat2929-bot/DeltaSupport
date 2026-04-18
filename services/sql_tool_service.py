import requests

from services.auth_service import API_BASE_URL


def create_sync_card_to_ticket_log_api(
    username,
    shop_raw_text,
    shop_name,
    zip_code,
    ticket_number,
    ticket_total_amount,
    case_type="",
    final_guid="",
    card_dbh_id="",
    card_ref_num="",
    card_amount="",
    card_tip_amount="",
    card_l4="",
):
    try:
        response = requests.post(
            f"{API_BASE_URL}/sync-card-to-ticket/log",
            json={
                "username": username,
                "shop_raw_text": shop_raw_text,
                "shop_name": shop_name,
                "zip_code": zip_code,
                "ticket_number": ticket_number,
                "ticket_total_amount": ticket_total_amount,
                "case_type": case_type,
                "final_guid": final_guid,
                "card_dbh_id": card_dbh_id,
                "card_ref_num": card_ref_num,
                "card_amount": card_amount,
                "card_tip_amount": card_tip_amount,
                "card_l4": card_l4,
            },
            timeout=15,
        )
        return response.json()
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Timeout khi lưu log GET SQL Code"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Lỗi kết nối API: {e}"}
