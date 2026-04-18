from typing import List

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str


class SendOTPRequest(BaseModel):
    email: str


class RegisterRequest(BaseModel):
    username: str
    full_name: str
    email: str
    password: str
    otp: str
    department: str
    team: str


class ApproveUserRequest(BaseModel):
    username: str
    department: str
    role: str
    team: str
    approved_by: str


class RejectUserRequest(BaseModel):
    username: str
    rejected_by: str = ""
    reason: str = ""


class BlockUserRequest(BaseModel):
    username: str
    action_by: str


class UpdateUserRequest(BaseModel):
    username: str
    full_name: str
    email: str
    department: str
    role: str
    team: str
    action_by: str
    notes: str = ""


class SetPinRequest(BaseModel):
    username: str
    pin_code: str
    action_by: str


class VerifyPinRequest(BaseModel):
    username: str
    pin_code: str
    action_by: str = ""


class ChangePinRequest(BaseModel):
    username: str
    old_pin: str
    new_pin: str
    action_by: str


class ForgotPinOTPRequest(BaseModel):
    username: str


class ResetPinWithOTPRequest(BaseModel):
    username: str
    otp: str
    new_pin: str
    action_by: str = ""


class TechScheduleUpdateRequest(BaseModel):
    username: str
    work_date: str
    status_code: str
    action_by: str
    note: str = ""


class ScheduleSetupSaveRequest(BaseModel):
    username: str
    display_name: str = ""
    department: str
    team: str = "General"
    shift_name: str
    vn_time_range: str = ""
    us_time_range: str = ""
    off_days: List[str]
    action_by: str


class ScheduleSetupActiveRequest(BaseModel):
    username: str
    active: bool
    action_by: str


class DeleteUserRequest(BaseModel):
    username: str
    action_by: str
    reason: str = ""


class SyncCardToTicketLogRequest(BaseModel):
    username: str
    shop_raw_text: str
    shop_name: str
    zip_code: str
    ticket_number: str
    ticket_total_amount: str = ""
    case_type: str = ""
    final_guid: str = ""
    card_dbh_id: str = ""
    card_ref_num: str = ""
    card_amount: str = ""
    card_tip_amount: str = ""
    card_l4: str = ""
    note: str = ""


class TaskFollowUpsertRequest(BaseModel):
    action_by_username: str
    merchant_raw_text: str
    phone: str = ""
    problem_summary: str = ""
    handoff_to_type: str = ""
    handoff_to_username: str = ""
    handoff_to_display_name: str = ""
    status: str
    deadline_date: str = ""
    deadline_time: str = ""
    deadline_period: str = "AM"
    note: str = ""
