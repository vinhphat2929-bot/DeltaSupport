from fastapi import APIRouter

from database import get_connection
from models import LoginRequest, ChangePasswordRequest, SendOTPRequest, RegisterRequest
from services.email_service import send_otp_email
from services.audit_service import write_user_log

router = APIRouter()

VALID_REGISTER_DEPARTMENTS = [
    "Technical Support",
    "Sale Team",
    "Office",
    "Management",
    "Customer Service",
    "Marketing Team",
]

DEFAULT_REGISTER_ROLE_MAP = {
    "Technical Support": "TS Senior",
    "Sale Team": "Sale Staff",
    "Office": "HR",
    "Management": "Management",
    "Customer Service": "CS Staff",
    "Marketing Team": "MT Staff",
}


def users_has_team_column(cursor):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = 'Users'
          AND COLUMN_NAME = 'Team'
        """
    )
    return cursor.fetchone()[0] > 0


def has_schedule_setup_table(cursor):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = 'TechScheduleEmployeeConfig'
        """
    )
    return cursor.fetchone()[0] > 0


def get_user_display_name(cursor, username, fallback_full_name=""):
    username_text = str(username or "").strip()
    fallback_text = str(fallback_full_name or "").strip()
    if not username_text:
        return fallback_text

    if has_schedule_setup_table(cursor):
        cursor.execute(
            """
            SELECT DisplayName
            FROM dbo.TechScheduleEmployeeConfig
            WHERE Username = ?
            """,
            (username_text,),
        )
        row = cursor.fetchone()
        if row and str(row[0] or "").strip():
            return str(row[0] or "").strip()

    return fallback_text or username_text


@router.post("/login")
def login(data: LoginRequest):
    conn = None
    try:
        username = data.username.strip()
        password = data.password.strip()

        conn = get_connection()
        cursor = conn.cursor()

        has_team = users_has_team_column(cursor)
        query = """
        SELECT Username, Password, FullName, Role, IsActive, IsApproved, Department
        {team_select}
        FROM dbo.Users
        WHERE Username = ?
        """.format(
            team_select=", Team" if has_team else ""
        )
        cursor.execute(query, (username,))
        row = cursor.fetchone()

        if not row:
            return {
                "success": False,
                "message": "Tài khoản chưa đăng ký hoặc mật khẩu không đúng",
            }

        if has_team:
            (
                db_username,
                db_password,
                db_full_name,
                db_role,
                db_is_active,
                db_is_approved,
                db_department,
                db_team,
            ) = row
        else:
            (
                db_username,
                db_password,
                db_full_name,
                db_role,
                db_is_active,
                db_is_approved,
                db_department,
            ) = row
            db_team = "General"

        if not db_is_active:
            return {
                "success": False,
                "message": "Tài khoản này đã bị block",
            }

        if db_password != password:
            return {
                "success": False,
                "message": "Tài khoản chưa đăng ký hoặc mật khẩu không đúng",
            }

        if not db_is_approved:
            return {
                "success": False,
                "message": "Vui lòng liên hệ ADMIN để cấp quyền truy cập",
            }

        if has_schedule_setup_table(cursor):
            cursor.execute(
                """
                SELECT IsActive
                FROM dbo.TechScheduleEmployeeConfig
                WHERE Username = ?
                """,
                (username,),
            )
            schedule_row = cursor.fetchone()
            if schedule_row is not None and not bool(schedule_row[0]):
                return {
                    "success": False,
                    "message": "Your account is pending schedule setup or has been marked inactive.",
                }

        resolved_display_name = get_user_display_name(cursor, db_username, db_full_name)

        return {
            "success": True,
            "username": db_username,
            "full_name": db_full_name,
            "display_name": resolved_display_name,
            "role": db_role,
            "department": db_department,
            "team": "General" if db_team is None or str(db_team).strip() == "" else str(db_team).strip(),
            "message": "Đăng nhập thành công",
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Lỗi server: {str(e)}",
        }

    finally:
        if conn:
            conn.close()


@router.post("/change-password")
def change_password(data: ChangePasswordRequest):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        SELECT Password
        FROM dbo.Users
        WHERE Username = ? AND IsActive = 1
        """
        cursor.execute(query, (data.username.strip(),))
        row = cursor.fetchone()

        if not row:
            return {"success": False, "message": "User không tồn tại"}

        old_password_in_db = row[0]

        if old_password_in_db != data.old_password.strip():
            return {"success": False, "message": "Mật khẩu cũ không đúng"}

        update_query = """
        UPDATE dbo.Users
        SET Password = ?
        WHERE Username = ?
        """
        cursor.execute(update_query, (data.new_password.strip(), data.username.strip()))

        write_user_log(
            cursor,
            username=data.username.strip(),
            action_type="CHANGE_PASSWORD",
            action_by=data.username.strip(),
            field_name="Password",
            old_value="***",
            new_value="***",
            note="User tự đổi mật khẩu",
        )

        conn.commit()

        return {"success": True, "message": "Đổi mật khẩu thành công"}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.post("/send-register-otp")
def send_register_otp(data: SendOTPRequest):
    conn = None
    try:
        email = data.email.strip().lower()

        if not email.endswith("@aiomerchant.com"):
            return {
                "success": False,
                "message": "Chỉ chấp nhận email @aiomerchant.com",
            }

        conn = get_connection()
        cursor = conn.cursor()

        check_query = """
        SELECT Username
        FROM dbo.Users
        WHERE Email = ?
        """
        cursor.execute(check_query, (email,))
        existing = cursor.fetchone()

        if existing:
            return {"success": False, "message": "Email này đã được sử dụng"}

        import random
        otp_code = str(random.randint(100000, 999999))

        insert_query = """
        INSERT INTO dbo.UserOTP (Email, OTPCode, ExpiredAt, IsUsed)
        VALUES (?, ?, DATEADD(MINUTE, 5, GETDATE()), 0)
        """
        cursor.execute(insert_query, (email, otp_code))
        conn.commit()

        send_otp_email(email, otp_code)

        return {"success": True, "message": "OTP đã được gửi qua email"}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.post("/register")
def register(data: RegisterRequest):
    conn = None
    try:
        username = data.username.strip()
        full_name = data.full_name.strip()
        email = data.email.strip().lower()
        password = data.password.strip()
        otp = data.otp.strip()
        department = data.department.strip()
        team = str(data.team or "").strip()

        if not email.endswith("@aiomerchant.com"):
            return {
                "success": False,
                "message": "Chỉ chấp nhận email @aiomerchant.com",
            }

        if department not in VALID_REGISTER_DEPARTMENTS:
            return {
                "success": False,
                "message": "Department không hợp lệ",
            }

        if department == "Sale Team":
            if team not in ["Team 1", "Team 2", "Team 3"]:
                return {
                    "success": False,
                    "message": "Team không hợp lệ cho Sale Team",
                }
        else:
            team = "General"

        default_role = DEFAULT_REGISTER_ROLE_MAP.get(department, "Pending")

        conn = get_connection()
        cursor = conn.cursor()

        check_user_query = """
        SELECT Username
        FROM dbo.Users
        WHERE Username = ?
        """
        cursor.execute(check_user_query, (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            return {"success": False, "message": "Username đã tồn tại"}

        check_email_query = """
        SELECT Username
        FROM dbo.Users
        WHERE Email = ?
        """
        cursor.execute(check_email_query, (email,))
        existing_email = cursor.fetchone()

        if existing_email:
            return {"success": False, "message": "Email này đã được sử dụng"}

        otp_query = """
        SELECT TOP 1 OTPID
        FROM dbo.UserOTP
        WHERE Email = ?
          AND OTPCode = ?
          AND IsUsed = 0
          AND ExpiredAt >= GETDATE()
        ORDER BY OTPID DESC
        """
        cursor.execute(otp_query, (email, otp))
        otp_row = cursor.fetchone()

        if not otp_row:
            return {"success": False, "message": "OTP không đúng hoặc đã hết hạn"}

        has_team = users_has_team_column(cursor)

        if has_team:
            insert_user_query = """
            INSERT INTO dbo.Users (
                Username, Password, FullName, Role, Department, Team,
                IsActive, CreatedAt, Email, IsApproved
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, GETDATE(), ?, 0)
            """
            cursor.execute(
                insert_user_query,
                (username, password, full_name, default_role, department, team, email),
            )
        else:
            insert_user_query = """
            INSERT INTO dbo.Users (
                Username, Password, FullName, Role, Department,
                IsActive, CreatedAt, Email, IsApproved
            )
            VALUES (?, ?, ?, ?, ?, 1, GETDATE(), ?, 0)
            """
            cursor.execute(
                insert_user_query,
                (username, password, full_name, default_role, department, email),
            )

        update_otp_query = """
        UPDATE dbo.UserOTP
        SET IsUsed = 1
        WHERE OTPID = ?
        """
        cursor.execute(update_otp_query, (otp_row[0],))

        write_user_log(
            cursor,
            username=username,
            action_type="REGISTER",
            action_by=username,
            note=f"User tự đăng ký tài khoản. Department={department}, Team={team}",
        )

        conn.commit()

        return {
            "success": True,
            "message": "Đăng ký thành công. Vui lòng chờ admin duyệt tài khoản.",
        }

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()
