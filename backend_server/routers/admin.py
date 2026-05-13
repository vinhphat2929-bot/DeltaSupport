from fastapi import APIRouter

from database import get_connection
from models import (
    AppAnnouncementCreateRequest,
    ApproveUserRequest,
    RejectUserRequest,
    BlockUserRequest,
    UpdateUserRequest,
    DeleteUserRequest,
)
from services.email_service import send_approved_email
from services.audit_service import write_user_log, get_status_text

router = APIRouter()


VALID_ROLES = {
    "Technical Support": [
        "TS Leader",
        "TS Senior",
        "TS Junior",
        "TS Probation",
    ],
    "Sale Team": [
        "Sale Leader",
        "Sale Staff",
        "Sale Admin",
    ],
    "Office": [
        "HR",
        "Accountant",
    ],
    "Management": [
        "Management",
    ],
    "Customer Service": [
        "CS Leader",
        "CS Staff",
    ],
    "Marketing Team": [
        "MT Leader",
        "MT Staff",
    ],
}


def is_valid_department_role(department: str, role: str) -> bool:
    if department not in VALID_ROLES:
        return False
    return role in VALID_ROLES[department]


def normalize_team(team_value: str | None) -> str:
    team = "" if team_value is None else str(team_value).strip()
    return team if team else "General"


def ensure_schedule_setup_table(cursor):
    cursor.execute(
        """
        IF OBJECT_ID('dbo.TechScheduleEmployeeConfig', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.TechScheduleEmployeeConfig (
                Username NVARCHAR(100) NOT NULL PRIMARY KEY,
                DisplayName NVARCHAR(255) NULL,
                Department NVARCHAR(100) NULL,
                Team NVARCHAR(100) NULL,
                ShiftName NVARCHAR(100) NULL,
                VNTimeRange NVARCHAR(100) NULL,
                USTimeRange NVARCHAR(100) NULL,
                OffDays NVARCHAR(100) NULL,
                IsActive BIT NOT NULL DEFAULT 0,
                UpdatedBy NVARCHAR(100) NULL,
                UpdatedAt DATETIME NULL
            )
        END
        """
    )


def get_actor_context(cursor, username: str):
    query = """
    SELECT Role, Department, Team
    FROM dbo.Users
    WHERE Username = ?
    """
    cursor.execute(query, (username.strip(),))
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "role": str(row[0] or "").strip(),
        "department": str(row[1] or "").strip(),
        "team": normalize_team(row[2]),
    }


def can_manage_same_scope(actor: dict | None, target_department: str, target_team: str):
    if not actor:
        return False
    role = str(actor.get("role", "")).strip().lower()
    actor_department = str(actor.get("department", "")).strip().lower()
    actor_team = normalize_team(actor.get("team"))
    target_department = str(target_department or "").strip().lower()
    target_team = normalize_team(target_team)

    if role in ["admin", "management", "hr", "leader", "manager"]:
        if role == "leader":
            return actor_department == target_department
        return True

    if role in ["ts leader", "sale leader", "mt leader", "cs leader"]:
        if actor_department != target_department:
            return False
        if target_department == "sale team":
            return actor_team == target_team
        return True

    return False


def can_delete_user(actor: dict | None):
    if not actor:
        return False
    return str(actor.get("role", "")).strip().lower() in ["admin", "management", "manager"]


def can_send_announcement(actor: dict | None):
    if not actor:
        return False
    return str(actor.get("role", "")).strip().lower() in [
        "admin",
        "management",
        "manager",
        "hr",
        "leader",
        "ts leader",
        "sale leader",
        "mt leader",
        "cs leader",
    ]


def can_approve_user(actor: dict | None, target_department: str, target_team: str):
    if not actor:
        return False
    role = str(actor.get("role", "")).strip().lower()
    if role in ["admin", "management", "manager"]:
        return True
    return False


def ensure_app_announcement_tables(cursor):
    cursor.execute(
        """
        IF OBJECT_ID('dbo.AppAnnouncement', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.AppAnnouncement (
                AnnouncementID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                Title NVARCHAR(255) NOT NULL,
                Message NVARCHAR(MAX) NOT NULL,
                TargetType NVARCHAR(30) NOT NULL DEFAULT 'ALL',
                TargetDepartment NVARCHAR(100) NULL,
                CreatedBy NVARCHAR(100) NULL,
                CreatedAt DATETIME NOT NULL DEFAULT GETDATE(),
                IsActive BIT NOT NULL DEFAULT 1
            )
        END
        """
    )
    cursor.execute(
        """
        IF OBJECT_ID('dbo.AppAnnouncementRead', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.AppAnnouncementRead (
                ReadID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                AnnouncementID INT NOT NULL,
                Username NVARCHAR(100) NOT NULL,
                ReadAt DATETIME NOT NULL DEFAULT GETDATE(),
                CONSTRAINT FK_AppAnnouncementRead_AnnouncementID
                    FOREIGN KEY (AnnouncementID) REFERENCES dbo.AppAnnouncement(AnnouncementID)
            )
        END
        """
    )
    cursor.execute(
        """
        IF OBJECT_ID('dbo.AppAnnouncementDismiss', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.AppAnnouncementDismiss (
                DismissID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                AnnouncementID INT NOT NULL,
                Username NVARCHAR(100) NOT NULL,
                DismissedAt DATETIME NOT NULL DEFAULT GETDATE(),
                CONSTRAINT FK_AppAnnouncementDismiss_AnnouncementID
                    FOREIGN KEY (AnnouncementID) REFERENCES dbo.AppAnnouncement(AnnouncementID)
            )
        END
        """
    )
    cursor.execute(
        """
        IF OBJECT_ID('dbo.AppAnnouncementRecipient', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.AppAnnouncementRecipient (
                RecipientID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                AnnouncementID INT NOT NULL,
                Username NVARCHAR(100) NOT NULL,
                CreatedAt DATETIME NOT NULL DEFAULT GETDATE(),
                CONSTRAINT FK_AppAnnouncementRecipient_AnnouncementID
                    FOREIGN KEY (AnnouncementID) REFERENCES dbo.AppAnnouncement(AnnouncementID)
            )
        END
        """
    )
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE name = 'IX_AppAnnouncement_Target_CreatedAt'
              AND object_id = OBJECT_ID('dbo.AppAnnouncement')
        )
        BEGIN
            CREATE INDEX IX_AppAnnouncement_Target_CreatedAt
            ON dbo.AppAnnouncement(IsActive, TargetType, TargetDepartment, CreatedAt DESC)
        END
        """
    )
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE name = 'UX_AppAnnouncementRead_AnnouncementID_Username'
              AND object_id = OBJECT_ID('dbo.AppAnnouncementRead')
        )
        BEGIN
            CREATE UNIQUE INDEX UX_AppAnnouncementRead_AnnouncementID_Username
            ON dbo.AppAnnouncementRead(AnnouncementID, Username)
        END
        """
    )
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE name = 'UX_AppAnnouncementDismiss_AnnouncementID_Username'
              AND object_id = OBJECT_ID('dbo.AppAnnouncementDismiss')
        )
        BEGIN
            CREATE UNIQUE INDEX UX_AppAnnouncementDismiss_AnnouncementID_Username
            ON dbo.AppAnnouncementDismiss(AnnouncementID, Username)
        END
        """
    )
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE name = 'UX_AppAnnouncementRecipient_AnnouncementID_Username'
              AND object_id = OBJECT_ID('dbo.AppAnnouncementRecipient')
        )
        BEGIN
            CREATE UNIQUE INDEX UX_AppAnnouncementRecipient_AnnouncementID_Username
            ON dbo.AppAnnouncementRecipient(AnnouncementID, Username)
        END
        """
    )


def upsert_schedule_setup_inactive(cursor, username: str, department: str, team: str, action_by: str):
    ensure_schedule_setup_table(cursor)
    cursor.execute(
        """
        MERGE dbo.TechScheduleEmployeeConfig AS target
        USING (SELECT ? AS Username) AS source
        ON target.Username = source.Username
        WHEN MATCHED THEN
            UPDATE SET
                Department = COALESCE(NULLIF(target.Department, ''), ?),
                Team = COALESCE(NULLIF(target.Team, ''), ?),
                IsActive = 0,
                UpdatedBy = ?,
                UpdatedAt = GETDATE()
        WHEN NOT MATCHED THEN
            INSERT (Username, Department, Team, IsActive, UpdatedBy, UpdatedAt)
            VALUES (?, ?, ?, 0, ?, GETDATE());
        """,
        (
            username,
            department,
            normalize_team(team),
            action_by,
            username,
            department,
            normalize_team(team),
            action_by,
        ),
    )


def set_schedule_setup_active(cursor, username: str, active: bool, action_by: str):
    ensure_schedule_setup_table(cursor)
    cursor.execute(
        """
        UPDATE dbo.TechScheduleEmployeeConfig
        SET IsActive = ?, UpdatedBy = ?, UpdatedAt = GETDATE()
        WHERE Username = ?
        """,
        (1 if active else 0, action_by, username),
    )


@router.post("/admin/announcements")
def create_app_announcement(data: AppAnnouncementCreateRequest):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ensure_app_announcement_tables(cursor)

        action_by = str(data.action_by or "").strip()
        title = str(data.title or "").strip()
        message = str(data.message or "").strip()
        target_type = str(data.target_type or "ALL").strip().upper()
        target_department = str(data.target_department or "").strip()
        target_usernames = []
        for raw_username in getattr(data, "target_usernames", []) or []:
            username = str(raw_username or "").strip()
            if username and username not in target_usernames:
                target_usernames.append(username)

        if not action_by:
            return {"success": False, "message": "Missing action_by."}
        if not title:
            return {"success": False, "message": "Title is required."}
        if not message:
            return {"success": False, "message": "Message is required."}
        if target_type not in {"ALL", "DEPARTMENT", "USERS"}:
            return {"success": False, "message": "Target type is invalid."}
        if target_type == "DEPARTMENT" and target_department not in VALID_ROLES:
            return {"success": False, "message": "Target department is invalid."}
        if target_type == "USERS" and not target_usernames:
            return {"success": False, "message": "Please select at least one user."}

        actor = get_actor_context(cursor, action_by)
        if not can_send_announcement(actor):
            return {"success": False, "message": "You do not have permission to send announcements."}

        valid_target_usernames = []
        if target_type == "USERS":
            placeholders = ",".join(["?"] * len(target_usernames))
            cursor.execute(
                f"""
                SELECT Username
                FROM dbo.Users
                WHERE IsActive = 1
                  AND Username IN ({placeholders})
                """,
                tuple(target_usernames),
            )
            valid_target_usernames = [
                str(row[0] or "").strip()
                for row in cursor.fetchall()
                if row and str(row[0] or "").strip()
            ]
            if not valid_target_usernames:
                return {"success": False, "message": "Selected users are invalid."}

        cursor.execute(
            """
            INSERT INTO dbo.AppAnnouncement
            (
                Title,
                Message,
                TargetType,
                TargetDepartment,
                CreatedBy,
                CreatedAt,
                IsActive
            )
            OUTPUT INSERTED.AnnouncementID
            VALUES (?, ?, ?, ?, ?, GETDATE(), 1)
            """,
            (
                title,
                message,
                target_type,
                target_department if target_type == "DEPARTMENT" else None,
                action_by,
            ),
        )
        row = cursor.fetchone()
        announcement_id = int(row[0]) if row and row[0] is not None else None
        if target_type == "USERS" and announcement_id:
            for username in valid_target_usernames:
                cursor.execute(
                    """
                    INSERT INTO dbo.AppAnnouncementRecipient (AnnouncementID, Username)
                    VALUES (?, ?)
                    """,
                    (announcement_id, username),
                )
        conn.commit()
        return {
            "success": True,
            "announcement_id": announcement_id,
            "message": "Announcement sent successfully.",
        }

    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.get("/pending-users")
def pending_users():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        SELECT Username, FullName, Email, Department, Team, CreatedAt
        FROM dbo.Users
        WHERE IsApproved = 0 AND IsActive = 1
        ORDER BY CreatedAt DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append(
                {
                    "username": row[0],
                    "full_name": row[1],
                    "email": row[2],
                    "department": row[3],
                    "team": normalize_team(row[4]),
                    "created_at": str(row[5]),
                }
            )

        return {"success": True, "users": data}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.get("/all-users")
def all_users(action_by: str = ""):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        actor_username = str(action_by or "").strip()
        query = """
        SELECT Username, FullName, Email, Department, Team, Role, IsApproved, IsActive, CreatedAt, ApprovedBy, ApprovedAt
        FROM dbo.Users
        WHERE ISNULL(Role, '') NOT IN ('Deleted User', 'Admin')
        ORDER BY CreatedAt DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        data = []
        for row in rows:
            status = get_status_text(bool(row[6]), bool(row[7]), row[5])
            if actor_username and str(row[0] or "").strip().lower() == actor_username.lower():
                continue

            data.append(
                {
                    "username": row[0],
                    "full_name": row[1],
                    "email": row[2],
                    "department": row[3],
                    "team": normalize_team(row[4]),
                    "role": row[5],
                    "is_approved": bool(row[6]),
                    "is_active": bool(row[7]),
                    "status": status,
                    "created_at": str(row[8]),
                    "approved_by": row[9],
                    "approved_at": None if row[10] is None else str(row[10]),
                }
            )

        return {"success": True, "users": data}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.get("/admin/users")
def admin_users(action_by: str = ""):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        actor_username = str(action_by or "").strip()
        query = """
        SELECT Username, FullName, Email, Department, Team, Role, IsApproved, IsActive, CreatedAt, ApprovedBy, ApprovedAt
        FROM dbo.Users
        WHERE ISNULL(Role, '') NOT IN ('Deleted User', 'Admin')
        ORDER BY CreatedAt DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        users = []
        for row in rows:
            is_approved = bool(row[6])
            is_active = bool(row[7])
            status = get_status_text(is_approved, is_active, row[5])

            if actor_username and str(row[0] or "").strip().lower() == actor_username.lower():
                continue

            users.append(
                {
                    "username": row[0],
                    "full_name": row[1],
                    "email": row[2],
                    "department": row[3],
                    "team": normalize_team(row[4]),
                    "role": row[5] or "",
                    "status": status,
                    "is_approved": is_approved,
                    "is_active": is_active,
                    "created_at": str(row[8]),
                    "approved_by": row[9],
                    "approved_at": None if row[10] is None else str(row[10]),
                    "notes": "",
                }
            )

        return {"success": True, "users": users}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.post("/approve-user")
def approve_user(data: ApproveUserRequest):
    conn = None
    try:
        department = data.department.strip()
        role = data.role.strip()
        team = normalize_team(data.team)
        approved_by = data.approved_by.strip()
        username = data.username.strip()

        if not is_valid_department_role(department, role):
            return {"success": False, "message": "Role không hợp lệ với Department đã chọn"}

        conn = get_connection()
        cursor = conn.cursor()
        actor = get_actor_context(cursor, approved_by)
        if not can_approve_user(actor, department, team):
            return {"success": False, "message": "Bạn không có quyền duyệt user này"}

        get_user_query = """
        SELECT Email, FullName, Department, Team, Role, IsApproved
        FROM dbo.Users
        WHERE Username = ?
        """
        cursor.execute(get_user_query, (username,))
        user_row = cursor.fetchone()

        if not user_row:
            return {"success": False, "message": "Không tìm thấy user"}

        user_email = user_row[0]
        user_full_name = user_row[1]
        old_department = user_row[2]
        old_team = normalize_team(user_row[3])
        old_role = user_row[4]
        old_is_approved = user_row[5]

        update_query = """
        UPDATE dbo.Users
        SET IsApproved = 1,
            Department = ?,
            Team = ?,
            Role = ?,
            ApprovedBy = ?,
            ApprovedAt = GETDATE()
        WHERE Username = ?
        """
        cursor.execute(
            update_query,
            (
                department,
                team,
                role,
                approved_by,
                username,
            ),
        )
        upsert_schedule_setup_inactive(cursor, username, department, team, approved_by)

        write_user_log(
            cursor,
            username=username,
            action_type="APPROVE",
            action_by=approved_by,
            field_name="IsApproved",
            old_value=old_is_approved,
            new_value=1,
            note=f"Approved user. Department: {old_department} -> {department}, Team: {old_team} -> {team}, Role: {old_role} -> {role}",
        )

        if str(old_department or "") != department:
            write_user_log(
                cursor,
                username=username,
                action_type="APPROVE",
                action_by=approved_by,
                field_name="Department",
                old_value=old_department,
                new_value=department,
                note="Department changed during approval",
            )

        if str(old_team or "") != team:
            write_user_log(
                cursor,
                username=username,
                action_type="APPROVE",
                action_by=approved_by,
                field_name="Team",
                old_value=old_team,
                new_value=team,
                note="Team changed during approval",
            )

        if str(old_role or "") != role:
            write_user_log(
                cursor,
                username=username,
                action_type="APPROVE",
                action_by=approved_by,
                field_name="Role",
                old_value=old_role,
                new_value=role,
                note="Role changed during approval",
            )

        conn.commit()

        try:
            send_approved_email(
                user_email,
                user_full_name,
                department,
                role,
            )
        except Exception:
            pass

        return {"success": True, "message": "Duyệt tài khoản thành công và đã ghi log"}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.put("/admin/users/{username}/approve")
def admin_approve_user(username: str, data: dict):
    conn = None
    try:
        approved_by = str(data.get("approved_by", "")).strip()
        department = str(data.get("department", "")).strip()
        role = str(data.get("role", "")).strip()
        team = normalize_team(data.get("team", "General"))

        conn = get_connection()
        cursor = conn.cursor()
        actor = get_actor_context(cursor, approved_by)

        get_user_query = """
        SELECT IsApproved, Department, Team, Role
        FROM dbo.Users
        WHERE Username = ?
        """
        cursor.execute(get_user_query, (username.strip(),))
        row = cursor.fetchone()

        if not row:
            return {"success": False, "message": "Không tìm thấy user"}

        old_is_approved = row[0]
        old_department = row[1]
        old_team = normalize_team(row[2])
        old_role = row[3]

        target_department = department or str(old_department or "").strip()
        target_team = team or normalize_team(old_team)

        if not can_approve_user(actor, target_department, target_team):
            return {"success": False, "message": "Bạn không có quyền duyệt user này"}

        if department and role and not is_valid_department_role(department, role):
            return {"success": False, "message": "Role không hợp lệ với Department đã chọn"}

        if department and role:
            update_query = """
            UPDATE dbo.Users
            SET IsApproved = 1,
                Department = ?,
                Team = ?,
                Role = ?,
                ApprovedBy = ?,
                ApprovedAt = GETDATE()
            WHERE Username = ?
            """
            cursor.execute(
                update_query,
                (
                    department,
                    team,
                    role,
                    approved_by,
                    username.strip(),
                ),
            )
            upsert_schedule_setup_inactive(cursor, username.strip(), department, team, approved_by)
        else:
            update_query = """
            UPDATE dbo.Users
            SET IsApproved = 1,
                ApprovedBy = ?,
                ApprovedAt = GETDATE()
            WHERE Username = ?
            """
            cursor.execute(update_query, (approved_by, username.strip()))
            upsert_schedule_setup_inactive(
                cursor,
                username.strip(),
                target_department,
                target_team,
                approved_by,
            )

        write_user_log(
            cursor,
            username=username.strip(),
            action_type="APPROVE",
            action_by=approved_by,
            field_name="IsApproved",
            old_value=old_is_approved,
            new_value=1,
            note="Approved from Admin Manager",
        )

        if department and str(old_department or "") != department:
            write_user_log(
                cursor,
                username=username.strip(),
                action_type="APPROVE",
                action_by=approved_by,
                field_name="Department",
                old_value=old_department,
                new_value=department,
                note="Department changed from Admin Manager",
            )

        if department and str(old_team or "") != team:
            write_user_log(
                cursor,
                username=username.strip(),
                action_type="APPROVE",
                action_by=approved_by,
                field_name="Team",
                old_value=old_team,
                new_value=team,
                note="Team changed from Admin Manager",
            )

        if department and str(old_role or "") != role:
            write_user_log(
                cursor,
                username=username.strip(),
                action_type="APPROVE",
                action_by=approved_by,
                field_name="Role",
                old_value=old_role,
                new_value=role,
                note="Role changed from Admin Manager",
            )

        conn.commit()

        return {"success": True, "message": "Đã duyệt user"}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.post("/reject-user")
def reject_user(data: RejectUserRequest):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        check_query = """
        SELECT Username, FullName, Email, Department, Team
        FROM dbo.Users
        WHERE Username = ? AND IsApproved = 0
        """
        cursor.execute(check_query, (data.username.strip(),))
        row = cursor.fetchone()

        if not row:
            return {"success": False, "message": "Không tìm thấy user chờ duyệt"}

        old_username = row[0]
        old_full_name = row[1]
        old_email = row[2]
        old_department = row[3]
        old_team = normalize_team(row[4])

        write_user_log(
            cursor,
            username=data.username.strip(),
            action_type="REJECT",
            action_by=data.rejected_by.strip(),
            note=f"Rejected pending user. FullName={old_full_name}, Email={old_email}, Department={old_department}, Team={old_team}. Reason={data.reason.strip()}",
        )

        delete_query = """
        DELETE FROM dbo.Users
        WHERE Username = ? AND IsApproved = 0
        """
        cursor.execute(delete_query, (old_username,))
        conn.commit()

        return {"success": True, "message": "Đã từ chối user đăng ký mới"}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.post("/update-user")
def update_user(data: UpdateUserRequest):
    conn = None
    try:
        department = data.department.strip()
        role = data.role.strip()
        team = normalize_team(data.team)

        if not is_valid_department_role(department, role):
            return {"success": False, "message": "Role không hợp lệ với Department đã chọn"}

        if not data.email.strip().lower().endswith("@aiomerchant.com"):
            return {"success": False, "message": "Chỉ chấp nhận email @aiomerchant.com"}

        conn = get_connection()
        cursor = conn.cursor()

        get_old_query = """
        SELECT FullName, Email, Department, Role, Team
        FROM dbo.Users
        WHERE Username = ?
        """
        cursor.execute(get_old_query, (data.username.strip(),))
        old_row = cursor.fetchone()

        if not old_row:
            return {"success": False, "message": "Không tìm thấy user để cập nhật"}

        old_full_name = old_row[0]
        old_email = old_row[1]
        old_department = old_row[2]
        old_role = old_row[3]
        old_team = normalize_team(old_row[4])

        update_query = """
        UPDATE dbo.Users
        SET FullName = ?,
            Email = ?,
            Department = ?,
            Role = ?,
            Team = ?
        WHERE Username = ?
        """
        cursor.execute(
            update_query,
            (
                data.full_name.strip(),
                data.email.strip().lower(),
                department,
                role,
                team,
                data.username.strip(),
            ),
        )

        if str(old_full_name or "") != data.full_name.strip():
            write_user_log(
                cursor,
                username=data.username.strip(),
                action_type="UPDATE_USER",
                action_by=data.action_by.strip(),
                field_name="FullName",
                old_value=old_full_name,
                new_value=data.full_name.strip(),
            )

        if str(old_email or "").lower() != data.email.strip().lower():
            write_user_log(
                cursor,
                username=data.username.strip(),
                action_type="UPDATE_USER",
                action_by=data.action_by.strip(),
                field_name="Email",
                old_value=old_email,
                new_value=data.email.strip().lower(),
            )

        if str(old_department or "") != department:
            write_user_log(
                cursor,
                username=data.username.strip(),
                action_type="UPDATE_USER",
                action_by=data.action_by.strip(),
                field_name="Department",
                old_value=old_department,
                new_value=department,
            )

        if str(old_role or "") != role:
            write_user_log(
                cursor,
                username=data.username.strip(),
                action_type="UPDATE_USER",
                action_by=data.action_by.strip(),
                field_name="Role",
                old_value=old_role,
                new_value=role,
            )

        if str(old_team or "") != team:
            write_user_log(
                cursor,
                username=data.username.strip(),
                action_type="UPDATE_USER",
                action_by=data.action_by.strip(),
                field_name="Team",
                old_value=old_team,
                new_value=team,
            )

        conn.commit()

        return {"success": True, "message": "Cập nhật user thành công"}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.put("/admin/users/{username}")
def admin_update_user(username: str, data: dict):
    conn = None
    try:
        full_name = str(data.get("full_name", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        department = str(data.get("department", "")).strip()
        role = str(data.get("role", "")).strip()
        team = normalize_team(data.get("team", "General"))
        status = str(data.get("status", "")).strip().lower()
        action_by = str(data.get("updated_by", "")).strip()
        notes = str(data.get("notes", "")).strip()

        if email and not email.endswith("@aiomerchant.com"):
            return {"success": False, "message": "Chỉ chấp nhận email @aiomerchant.com"}

        if department and role and not is_valid_department_role(department, role):
            return {"success": False, "message": "Role không hợp lệ với Department đã chọn"}

        conn = get_connection()
        cursor = conn.cursor()
        actor = get_actor_context(cursor, action_by)

        get_old_query = """
        SELECT FullName, Email, Department, Role, Team, IsApproved, IsActive, ApprovedBy
        FROM dbo.Users
        WHERE Username = ?
        """
        cursor.execute(get_old_query, (username.strip(),))
        old_row = cursor.fetchone()

        if not old_row:
            return {"success": False, "message": "Không tìm thấy user"}

        old_full_name = old_row[0]
        old_email = old_row[1]
        old_department = old_row[2]
        old_role = old_row[3]
        old_team = normalize_team(old_row[4])
        old_is_approved = bool(old_row[5])
        old_is_active = bool(old_row[6])
        old_approved_by = old_row[7]

        if not can_manage_same_scope(actor, department or old_department, team or old_team):
            return {"success": False, "message": "Bạn không có quyền cập nhật user này"}

        new_is_approved = old_is_approved
        new_is_active = old_is_active

        if status == "pending":
            new_is_approved = False
            new_is_active = True
        elif status == "approved":
            new_is_approved = True
            new_is_active = True
        elif status == "inactive":
            new_is_active = False

        update_query = """
        UPDATE dbo.Users
        SET FullName = ?,
            Email = ?,
            Department = ?,
            Role = ?,
            Team = ?,
            IsApproved = ?,
            IsActive = ?,
            ApprovedBy = ?
        WHERE Username = ?
        """
        cursor.execute(
            update_query,
            (
                full_name,
                email,
                department,
                role,
                team,
                1 if new_is_approved else 0,
                1 if new_is_active else 0,
                old_approved_by,
                username.strip(),
            ),
        )

        if str(old_full_name or "") != full_name:
            write_user_log(
                cursor,
                username=username.strip(),
                action_type="UPDATE_USER",
                action_by=action_by,
                field_name="FullName",
                old_value=old_full_name,
                new_value=full_name,
            )

        if str(old_email or "").lower() != email:
            write_user_log(
                cursor,
                username=username.strip(),
                action_type="UPDATE_USER",
                action_by=action_by,
                field_name="Email",
                old_value=old_email,
                new_value=email,
            )

        if str(old_department or "") != department:
            write_user_log(
                cursor,
                username=username.strip(),
                action_type="UPDATE_USER",
                action_by=action_by,
                field_name="Department",
                old_value=old_department,
                new_value=department,
            )

        if str(old_role or "") != role:
            write_user_log(
                cursor,
                username=username.strip(),
                action_type="UPDATE_USER",
                action_by=action_by,
                field_name="Role",
                old_value=old_role,
                new_value=role,
            )

        if str(old_team or "") != team:
            write_user_log(
                cursor,
                username=username.strip(),
                action_type="UPDATE_USER",
                action_by=action_by,
                field_name="Team",
                old_value=old_team,
                new_value=team,
            )

        if bool(old_is_approved) != bool(new_is_approved):
            write_user_log(
                cursor,
                username=username.strip(),
                action_type="UPDATE_USER",
                action_by=action_by,
                field_name="IsApproved",
                old_value=old_is_approved,
                new_value=new_is_approved,
            )

        if bool(old_is_active) != bool(new_is_active):
            write_user_log(
                cursor,
                username=username.strip(),
                action_type="UPDATE_USER",
                action_by=action_by,
                field_name="IsActive",
                old_value=old_is_active,
                new_value=new_is_active,
                note=notes or ("User marked inactive" if not new_is_active else "User reactivated"),
            )

        if not new_is_active:
            set_schedule_setup_active(cursor, username.strip(), False, action_by)

        conn.commit()

        return {"success": True, "message": "Đã cập nhật user"}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.put("/admin/users/{username}/delete")
def admin_delete_user(username: str, data: dict):
    conn = None
    try:
        action_by = str(data.get("action_by", "")).strip()
        reason = str(data.get("reason", "")).strip()

        conn = get_connection()
        cursor = conn.cursor()
        actor = get_actor_context(cursor, action_by)
        if not can_delete_user(actor):
            return {"success": False, "message": "Bạn không có quyền xóa user"}

        cursor.execute(
            """
            SELECT FullName, Email, Department, Team, Role, IsApproved, IsActive
            FROM dbo.Users
            WHERE Username = ?
            """,
            (username.strip(),),
        )
        row = cursor.fetchone()

        if not row:
            return {"success": False, "message": "Không tìm thấy user"}

        old_role = str(row[4] or "").strip()
        old_is_approved = bool(row[5])
        old_is_active = bool(row[6])

        cursor.execute(
            """
            UPDATE dbo.Users
            SET Role = 'Deleted User',
                IsApproved = 0,
                IsActive = 0
            WHERE Username = ?
            """,
            (username.strip(),),
        )

        set_schedule_setup_active(cursor, username.strip(), False, action_by)

        write_user_log(
            cursor,
            username=username.strip(),
            action_type="DELETE_USER",
            action_by=action_by,
            field_name="Role",
            old_value=old_role,
            new_value="Deleted User",
            note=reason or "User removed from system view",
        )
        if old_is_approved:
            write_user_log(
                cursor,
                username=username.strip(),
                action_type="DELETE_USER",
                action_by=action_by,
                field_name="IsApproved",
                old_value=old_is_approved,
                new_value=False,
                note=reason or "User removed from system view",
            )
        if old_is_active:
            write_user_log(
                cursor,
                username=username.strip(),
                action_type="DELETE_USER",
                action_by=action_by,
                field_name="IsActive",
                old_value=old_is_active,
                new_value=False,
                note=reason or "User removed from system view",
            )

        conn.commit()
        return {"success": True, "message": "Đã xóa user khỏi hệ thống hiển thị"}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.post("/block-user")
def block_user(data: BlockUserRequest):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        check_query = """
        SELECT IsActive
        FROM dbo.Users
        WHERE Username = ?
        """
        cursor.execute(check_query, (data.username.strip(),))
        row = cursor.fetchone()

        if not row:
            return {"success": False, "message": "Không tìm thấy user để block"}

        old_is_active = row[0]

        query = """
        UPDATE dbo.Users
        SET IsActive = 0
        WHERE Username = ?
        """
        cursor.execute(query, (data.username.strip(),))

        write_user_log(
            cursor,
            username=data.username.strip(),
            action_type="BLOCK",
            action_by=data.action_by.strip(),
            field_name="IsActive",
            old_value=old_is_active,
            new_value=0,
            note="Blocked user",
        )

        conn.commit()

        return {"success": True, "message": "Đã block user"}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.put("/admin/users/{username}/block")
def admin_block_user(username: str, data: dict):
    conn = None
    try:
        action_by = str(data.get("blocked_by", "")).strip()

        conn = get_connection()
        cursor = conn.cursor()

        check_query = """
        SELECT IsActive
        FROM dbo.Users
        WHERE Username = ?
        """
        cursor.execute(check_query, (username.strip(),))
        row = cursor.fetchone()

        if not row:
            return {"success": False, "message": "Không tìm thấy user"}

        old_is_active = row[0]

        query = """
        UPDATE dbo.Users
        SET IsActive = 0
        WHERE Username = ?
        """
        cursor.execute(query, (username.strip(),))

        write_user_log(
            cursor,
            username=username.strip(),
            action_type="BLOCK",
            action_by=action_by,
            field_name="IsActive",
            old_value=old_is_active,
            new_value=0,
            note="Blocked from Admin Manager",
        )

        conn.commit()

        return {"success": True, "message": "Đã block user"}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.post("/unblock-user")
def unblock_user(data: BlockUserRequest):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        check_query = """
        SELECT IsActive
        FROM dbo.Users
        WHERE Username = ?
        """
        cursor.execute(check_query, (data.username.strip(),))
        row = cursor.fetchone()

        if not row:
            return {"success": False, "message": "Không tìm thấy user để mở block"}

        old_is_active = row[0]

        query = """
        UPDATE dbo.Users
        SET IsActive = 1
        WHERE Username = ?
        """
        cursor.execute(query, (data.username.strip(),))

        write_user_log(
            cursor,
            username=data.username.strip(),
            action_type="UNBLOCK",
            action_by=data.action_by.strip(),
            field_name="IsActive",
            old_value=old_is_active,
            new_value=1,
            note="Unblocked user",
        )

        conn.commit()

        return {"success": True, "message": "Đã mở block user"}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.put("/admin/users/{username}/unblock")
def admin_unblock_user(username: str, data: dict):
    conn = None
    try:
        action_by = str(data.get("updated_by", "")).strip()

        conn = get_connection()
        cursor = conn.cursor()

        check_query = """
        SELECT IsActive
        FROM dbo.Users
        WHERE Username = ?
        """
        cursor.execute(check_query, (username.strip(),))
        row = cursor.fetchone()

        if not row:
            return {"success": False, "message": "Không tìm thấy user"}

        old_is_active = row[0]

        query = """
        UPDATE dbo.Users
        SET IsActive = 1
        WHERE Username = ?
        """
        cursor.execute(query, (username.strip(),))

        write_user_log(
            cursor,
            username=username.strip(),
            action_type="UNBLOCK",
            action_by=action_by,
            field_name="IsActive",
            old_value=old_is_active,
            new_value=1,
            note="Unblocked from Admin Manager",
        )

        conn.commit()

        return {"success": True, "message": "Đã mở block user"}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.get("/user-logs/{username}")
def get_user_logs(username: str):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        SELECT LogID, Username, ActionType, FieldName, OldValue, NewValue, ActionBy, ActionAt, Note
        FROM dbo.UserAuditLog
        WHERE Username = ?
        ORDER BY ActionAt DESC, LogID DESC
        """
        cursor.execute(query, (username.strip(),))
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append(
                {
                    "log_id": row[0],
                    "username": row[1],
                    "action_type": row[2],
                    "field_name": row[3],
                    "old_value": row[4],
                    "new_value": row[5],
                    "action_by": row[6],
                    "action_at": str(row[7]),
                    "note": row[8],
                }
            )

        return {"success": True, "logs": data}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()


@router.get("/audit-logs")
def get_all_logs():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        SELECT TOP 500 LogID, Username, ActionType, FieldName, OldValue, NewValue, ActionBy, ActionAt, Note
        FROM dbo.UserAuditLog
        ORDER BY ActionAt DESC, LogID DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append(
                {
                    "log_id": row[0],
                    "username": row[1],
                    "action_type": row[2],
                    "field_name": row[3],
                    "old_value": row[4],
                    "new_value": row[5],
                    "action_by": row[6],
                    "action_at": str(row[7]),
                    "note": row[8],
                }
            )

        return {"success": True, "logs": data}

    except Exception as e:
        return {"success": False, "message": f"Lỗi server: {str(e)}"}

    finally:
        if conn:
            conn.close()
