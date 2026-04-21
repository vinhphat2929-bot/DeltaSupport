import random

from fastapi import APIRouter

from database import get_connection
from models import (
    ChangePinRequest,
    ForgotPinOTPRequest,
    ResetPinWithOTPRequest,
    SetPinRequest,
    VerifyPinRequest,
)
from services.audit_service import is_valid_pin, write_user_log
from services.email_service import send_pin_reset_otp_email

router = APIRouter()


def ensure_user_pin_columns(cursor):
    schema_changed = False

    cursor.execute(
        """
        SELECT
            CASE WHEN COL_LENGTH('dbo.Users', 'PinCode') IS NULL THEN 1 ELSE 0 END,
            CASE WHEN COL_LENGTH('dbo.Users', 'PinUpdatedAt') IS NULL THEN 1 ELSE 0 END,
            CASE WHEN COL_LENGTH('dbo.Users', 'PinFailedCount') IS NULL THEN 1 ELSE 0 END,
            CASE WHEN COL_LENGTH('dbo.Users', 'PinLockedUntil') IS NULL THEN 1 ELSE 0 END
        """
    )
    row = cursor.fetchone()
    if row:
        schema_changed = any(int(value or 0) == 1 for value in row)

    cursor.execute(
        """
        IF COL_LENGTH('dbo.Users', 'PinCode') IS NULL
        BEGIN
            ALTER TABLE dbo.Users
            ADD PinCode NVARCHAR(10) NULL
        END
        """
    )
    cursor.execute(
        """
        IF COL_LENGTH('dbo.Users', 'PinUpdatedAt') IS NULL
        BEGIN
            ALTER TABLE dbo.Users
            ADD PinUpdatedAt DATETIME NULL
        END
        """
    )
    cursor.execute(
        """
        IF COL_LENGTH('dbo.Users', 'PinFailedCount') IS NULL
        BEGIN
            ALTER TABLE dbo.Users
            ADD PinFailedCount INT NOT NULL
                CONSTRAINT DF_Users_PinFailedCount DEFAULT 0
        END
        """
    )
    cursor.execute(
        """
        IF COL_LENGTH('dbo.Users', 'PinLockedUntil') IS NULL
        BEGIN
            ALTER TABLE dbo.Users
            ADD PinLockedUntil DATETIME NULL
        END
        """
    )

    if schema_changed:
        cursor.connection.commit()

    return schema_changed


def ensure_user_otp_table(cursor):
    cursor.execute(
        """
        IF OBJECT_ID('dbo.UserOTP', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.UserOTP (
                OTPID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                Email NVARCHAR(255) NOT NULL,
                OTPCode NVARCHAR(10) NOT NULL,
                ExpiredAt DATETIME NOT NULL,
                IsUsed BIT NOT NULL DEFAULT 0,
                CreatedAt DATETIME NOT NULL DEFAULT GETDATE()
            )
        END
        """
    )
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1
            FROM sys.indexes
            WHERE name = 'IX_UserOTP_Email_IsUsed_ExpiredAt'
              AND object_id = OBJECT_ID('dbo.UserOTP')
        )
        BEGIN
            CREATE INDEX IX_UserOTP_Email_IsUsed_ExpiredAt
            ON dbo.UserOTP(Email, IsUsed, ExpiredAt DESC)
        END
        """
    )


def bootstrap_pin_schema():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ensure_user_pin_columns(cursor)
        ensure_user_otp_table(cursor)
        conn.commit()
    finally:
        if conn:
            conn.close()


@router.get("/pin-status/{username}")
def get_pin_status(username: str):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ensure_user_pin_columns(cursor)

        cursor.execute(
            """
            SELECT Username, PinCode, PinFailedCount, PinLockedUntil
            FROM dbo.Users
            WHERE Username = ?
            """,
            (username.strip(),),
        )
        row = cursor.fetchone()

        if not row:
            return {"success": False, "message": "User not found"}

        return {
            "success": True,
            "username": row[0],
            "has_pin": bool(row[1]),
            "failed_count": int(row[2] or 0),
            "locked_until": None if row[3] is None else str(row[3]),
        }

    except Exception as e:
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.post("/set-pin")
def set_pin(data: SetPinRequest):
    conn = None
    try:
        username = data.username.strip()
        pin_code = data.pin_code.strip()
        action_by = data.action_by.strip()

        if not is_valid_pin(pin_code):
            return {"success": False, "message": "PIN must be exactly 4 digits"}

        conn = get_connection()
        cursor = conn.cursor()
        ensure_user_pin_columns(cursor)

        cursor.execute(
            "SELECT PinCode FROM dbo.Users WHERE Username = ?",
            (username,),
        )
        row = cursor.fetchone()

        if not row:
            return {"success": False, "message": "User not found"}

        if row[0]:
            return {"success": False, "message": "User already has a PIN"}

        cursor.execute(
            """
            UPDATE dbo.Users
            SET PinCode = ?, PinUpdatedAt = GETDATE(), PinFailedCount = 0, PinLockedUntil = NULL
            WHERE Username = ?
            """,
            (pin_code, username),
        )

        write_user_log(
            cursor,
            username=username,
            action_type="SET_PIN",
            action_by=action_by,
            field_name="PinCode",
            old_value=None,
            new_value="****",
        )

        conn.commit()
        return {"success": True, "message": "PIN created successfully"}

    except Exception as e:
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.post("/verify-pin")
def verify_pin(data: VerifyPinRequest):
    conn = None
    try:
        username = data.username.strip()
        pin_code = data.pin_code.strip()

        if not is_valid_pin(pin_code):
            return {"success": False, "message": "PIN must be exactly 4 digits"}

        conn = get_connection()
        cursor = conn.cursor()
        ensure_user_pin_columns(cursor)

        cursor.execute(
            "SELECT PinCode FROM dbo.Users WHERE Username = ?",
            (username,),
        )
        row = cursor.fetchone()

        if not row:
            return {"success": False, "message": "User not found"}

        if str(row[0] or "") == pin_code:
            return {"success": True, "message": "PIN is correct"}

        return {"success": False, "message": "PIN is incorrect"}

    except Exception as e:
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.post("/change-pin")
def change_pin(data: ChangePinRequest):
    conn = None
    try:
        username = data.username.strip()
        old_pin = data.old_pin.strip()
        new_pin = data.new_pin.strip()
        action_by = data.action_by.strip()

        if not is_valid_pin(new_pin):
            return {"success": False, "message": "New PIN is invalid"}

        conn = get_connection()
        cursor = conn.cursor()
        ensure_user_pin_columns(cursor)

        cursor.execute(
            "SELECT PinCode FROM dbo.Users WHERE Username = ?",
            (username,),
        )
        row = cursor.fetchone()

        if not row:
            return {"success": False, "message": "User not found"}

        current_pin = str(row[0] or "")
        if current_pin != old_pin:
            return {"success": False, "message": "Current PIN is incorrect"}

        cursor.execute(
            """
            UPDATE dbo.Users
            SET PinCode = ?, PinUpdatedAt = GETDATE(), PinFailedCount = 0, PinLockedUntil = NULL
            WHERE Username = ?
            """,
            (new_pin, username),
        )

        write_user_log(
            cursor,
            username=username,
            action_type="CHANGE_PIN",
            action_by=action_by,
            field_name="PinCode",
            old_value="****" if current_pin else None,
            new_value="****",
        )

        conn.commit()
        return {"success": True, "message": "PIN changed successfully"}

    except Exception as e:
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.post("/forgot-pin/send-otp")
def send_forgot_pin_otp(data: ForgotPinOTPRequest):
    conn = None
    try:
        username = data.username.strip()

        conn = get_connection()
        cursor = conn.cursor()
        ensure_user_otp_table(cursor)

        cursor.execute(
            """
            SELECT Email
            FROM dbo.Users
            WHERE Username = ?
            """,
            (username,),
        )
        row = cursor.fetchone()

        if not row or not str(row[0] or "").strip():
            return {"success": False, "message": "User not found"}

        email = str(row[0]).strip().lower()
        otp_code = str(random.randint(100000, 999999))

        cursor.execute(
            """
            INSERT INTO dbo.UserOTP (Email, OTPCode, ExpiredAt, IsUsed)
            VALUES (?, ?, DATEADD(MINUTE, 5, GETDATE()), 0)
            """,
            (email, otp_code),
        )
        conn.commit()

        send_pin_reset_otp_email(email, otp_code)

        return {
            "success": True,
            "message": "OTP has been sent to your registered email address.",
        }

    except Exception as e:
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.post("/forgot-pin/reset")
def reset_pin_with_otp(data: ResetPinWithOTPRequest):
    conn = None
    try:
        username = data.username.strip()
        otp = data.otp.strip()
        new_pin = data.new_pin.strip()
        action_by = (data.action_by or username).strip()

        if not otp.isdigit() or len(otp) != 6:
            return {"success": False, "message": "OTP must be exactly 6 digits"}

        if not is_valid_pin(new_pin):
            return {"success": False, "message": "New PIN must be exactly 4 digits"}

        conn = get_connection()
        cursor = conn.cursor()
        ensure_user_pin_columns(cursor)
        ensure_user_otp_table(cursor)

        cursor.execute(
            """
            SELECT Email, PinCode
            FROM dbo.Users
            WHERE Username = ?
            """,
            (username,),
        )
        user_row = cursor.fetchone()

        if not user_row:
            return {"success": False, "message": "User not found"}

        email = str(user_row[0] or "").strip().lower()
        old_pin_masked = "****" if user_row[1] else None

        cursor.execute(
            """
            SELECT TOP 1 OTPID
            FROM dbo.UserOTP
            WHERE Email = ?
              AND OTPCode = ?
              AND IsUsed = 0
              AND ExpiredAt >= GETDATE()
            ORDER BY OTPID DESC
            """,
            (email, otp),
        )
        otp_row = cursor.fetchone()

        if not otp_row:
            return {"success": False, "message": "Invalid or expired OTP"}

        cursor.execute(
            """
            UPDATE dbo.Users
            SET PinCode = ?, PinUpdatedAt = GETDATE(), PinFailedCount = 0, PinLockedUntil = NULL
            WHERE Username = ?
            """,
            (new_pin, username),
        )

        cursor.execute(
            """
            UPDATE dbo.UserOTP
            SET IsUsed = 1
            WHERE OTPID = ?
            """,
            (otp_row[0],),
        )

        write_user_log(
            cursor,
            username=username,
            action_type="RESET_PIN",
            action_by=action_by,
            field_name="PinCode",
            old_value=old_pin_masked,
            new_value="****",
            note="PIN reset via OTP verification",
        )

        conn.commit()
        return {"success": True, "message": "PIN reset successfully"}

    except Exception as e:
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()
