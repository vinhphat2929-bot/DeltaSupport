from datetime import datetime, timedelta

import json

from fastapi import APIRouter

from database import get_connection
from models import (
    TaskFollowNotificationClearRequest,
    TaskFollowNotificationReadRequest,
    TaskFollowUpsertRequest,
)

router = APIRouter()

ALLOWED_STATUSES = {
    "FOLLOW",
    "FOLLOW REQUEST",
    "SHIP OUT",
    "SET UP & TRAINING",
    "2ND TRAINING",
    "MISS TIP / CHARGE BACK",
    "DONE",
    "DEMO",
}


def normalize_text(value):
    return str(value or "").strip()


def normalize_username(value):
    return normalize_text(value)


def normalize_status(value):
    normalized = normalize_text(value).upper()
    if normalized == "CHECK TRACKING NUMBER":
        return "SHIP OUT"
    return normalized


def normalize_tracking_number(value):
    return normalize_text(value).upper()


def parse_merchant_fields(raw_text):
    raw_value = normalize_text(raw_text)
    if not raw_value:
        return "", "", ""

    parts = raw_value.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].isdigit():
        merchant_name = normalize_text(parts[0])
        zip_code = normalize_text(parts[1])
    else:
        merchant_name = raw_value
        zip_code = ""

    return raw_value, merchant_name, zip_code


def is_identity_column(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT COLUMNPROPERTY(OBJECT_ID(?), ?, 'IsIdentity')
        """,
        (table_name, column_name),
    )
    row = cursor.fetchone()
    return bool(row and row[0] == 1)


def get_next_int_id(cursor, table_name, column_name):
    cursor.execute(f"SELECT ISNULL(MAX({column_name}), 0) + 1 FROM {table_name}")
    row = cursor.fetchone()
    return int(row[0]) if row and row[0] is not None else 1


def is_null_insert_id_error(error, column_name):
    message = str(error or "").lower()
    return "cannot insert the value null into column" in message and column_name.lower() in message


def is_identity_insert_error(error, column_name):
    message = str(error or "").lower()
    return (
        "cannot insert explicit value for identity column" in message
        and column_name.lower() in message
    )


def get_user_display_name(cursor, username):
    username = normalize_username(username)
    if not username:
        return ""

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = 'TechScheduleEmployeeConfig'
        """
    )
    has_schedule_setup = cursor.fetchone()[0] > 0

    if has_schedule_setup:
        cursor.execute(
            """
            SELECT DisplayName
            FROM dbo.TechScheduleEmployeeConfig
            WHERE Username = ?
            """,
            (username,),
        )
        row = cursor.fetchone()
        if row and normalize_text(row[0]):
            return normalize_text(row[0])

    cursor.execute(
        """
        SELECT FullName
        FROM dbo.Users
        WHERE Username = ?
        """,
        (username,),
    )
    row = cursor.fetchone()
    return normalize_text(row[0]) if row else ""


def get_user_department(cursor, username):
    username = normalize_username(username)
    if not username:
        return ""

    cursor.execute(
        """
        SELECT Department
        FROM dbo.Users
        WHERE Username = ?
        """,
        (username,),
    )
    row = cursor.fetchone()
    return normalize_text(row[0]) if row else ""


def ensure_task_follow_notification_read_table(cursor):
    cursor.execute(
        """
        IF OBJECT_ID('dbo.TaskFollowNotificationRead', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.TaskFollowNotificationRead (
                ReadID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                TaskID INT NOT NULL,
                Username NVARCHAR(100) NOT NULL,
                ReadAt DATETIME NOT NULL DEFAULT GETDATE(),
                CONSTRAINT FK_TaskFollowNotificationRead_TaskID
                    FOREIGN KEY (TaskID) REFERENCES dbo.TaskFollow(TaskID)
            )
        END
        """
    )
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1
            FROM sys.indexes
            WHERE name = 'UX_TaskFollowNotificationRead_TaskID_Username'
              AND object_id = OBJECT_ID('dbo.TaskFollowNotificationRead')
        )
        BEGIN
            CREATE UNIQUE INDEX UX_TaskFollowNotificationRead_TaskID_Username
            ON dbo.TaskFollowNotificationRead(TaskID, Username)
        END
        """
    )
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1
            FROM sys.indexes
            WHERE name = 'IX_TaskFollowNotificationRead_Username_ReadAt'
              AND object_id = OBJECT_ID('dbo.TaskFollowNotificationRead')
        )
        BEGIN
            CREATE INDEX IX_TaskFollowNotificationRead_Username_ReadAt
            ON dbo.TaskFollowNotificationRead(Username, ReadAt DESC)
        END
        """
    )


def ensure_task_follow_notification_dismiss_table(cursor):
    cursor.execute(
        """
        IF OBJECT_ID('dbo.TaskFollowNotificationDismiss', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.TaskFollowNotificationDismiss (
                DismissID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                TaskID INT NOT NULL,
                Username NVARCHAR(100) NOT NULL,
                DismissedAt DATETIME NOT NULL DEFAULT GETDATE(),
                CONSTRAINT FK_TaskFollowNotificationDismiss_TaskID
                    FOREIGN KEY (TaskID) REFERENCES dbo.TaskFollow(TaskID)
            )
        END
        """
    )
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1
            FROM sys.indexes
            WHERE name = 'UX_TaskFollowNotificationDismiss_TaskID_Username'
              AND object_id = OBJECT_ID('dbo.TaskFollowNotificationDismiss')
        )
        BEGIN
            CREATE UNIQUE INDEX UX_TaskFollowNotificationDismiss_TaskID_Username
            ON dbo.TaskFollowNotificationDismiss(TaskID, Username)
        END
        """
    )
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1
            FROM sys.indexes
            WHERE name = 'IX_TaskFollowNotificationDismiss_Username_DismissedAt'
              AND object_id = OBJECT_ID('dbo.TaskFollowNotificationDismiss')
        )
        BEGIN
            CREATE INDEX IX_TaskFollowNotificationDismiss_Username_DismissedAt
            ON dbo.TaskFollowNotificationDismiss(Username, DismissedAt DESC)
        END
        """
    )


def ensure_task_follow_recipient_table(cursor):
    cursor.execute(
        """
        IF OBJECT_ID('dbo.TaskFollowRecipient', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.TaskFollowRecipient (
                RecipientID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                TaskID INT NOT NULL,
                RecipientType NVARCHAR(20) NOT NULL,
                Username NVARCHAR(100) NULL,
                DisplayName NVARCHAR(255) NULL,
                CreatedAt DATETIME NOT NULL DEFAULT GETDATE(),
                CONSTRAINT FK_TaskFollowRecipient_TaskID
                    FOREIGN KEY (TaskID) REFERENCES dbo.TaskFollow(TaskID)
            )
        END
        """
    )


def ensure_task_follow_training_columns(cursor):
    schema_changed = False

    cursor.execute(
        """
        SELECT
            CASE WHEN COL_LENGTH('dbo.TaskFollow', 'TrainingFormJson') IS NULL THEN 1 ELSE 0 END,
            CASE WHEN COL_LENGTH('dbo.TaskFollow', 'TrainingStartedAt') IS NULL THEN 1 ELSE 0 END,
            CASE WHEN COL_LENGTH('dbo.TaskFollow', 'TrainingStartedByUsername') IS NULL THEN 1 ELSE 0 END,
            CASE WHEN COL_LENGTH('dbo.TaskFollow', 'TrainingStartedByDisplayName') IS NULL THEN 1 ELSE 0 END,
            CASE WHEN COL_LENGTH('dbo.TaskFollow', 'TrainingCompletedTabsJson') IS NULL THEN 1 ELSE 0 END,
            CASE WHEN COL_LENGTH('dbo.TaskFollow', 'TrackingNumber') IS NULL THEN 1 ELSE 0 END
        """
    )
    row = cursor.fetchone()
    if row:
        schema_changed = any(int(value or 0) == 1 for value in row)

    cursor.execute(
        """
        IF COL_LENGTH('dbo.TaskFollow', 'TrainingFormJson') IS NULL
        BEGIN
            ALTER TABLE dbo.TaskFollow
            ADD TrainingFormJson NVARCHAR(MAX) NULL
        END
        """
    )
    cursor.execute(
        """
        IF COL_LENGTH('dbo.TaskFollow', 'TrainingStartedAt') IS NULL
        BEGIN
            ALTER TABLE dbo.TaskFollow
            ADD TrainingStartedAt DATETIME NULL
        END
        """
    )
    cursor.execute(
        """
        IF COL_LENGTH('dbo.TaskFollow', 'TrainingStartedByUsername') IS NULL
        BEGIN
            ALTER TABLE dbo.TaskFollow
            ADD TrainingStartedByUsername NVARCHAR(100) NULL
        END
        """
    )
    cursor.execute(
        """
        IF COL_LENGTH('dbo.TaskFollow', 'TrainingStartedByDisplayName') IS NULL
        BEGIN
            ALTER TABLE dbo.TaskFollow
            ADD TrainingStartedByDisplayName NVARCHAR(255) NULL
        END
        """
    )
    cursor.execute(
        """
        IF COL_LENGTH('dbo.TaskFollow', 'TrainingCompletedTabsJson') IS NULL
        BEGIN
            ALTER TABLE dbo.TaskFollow
            ADD TrainingCompletedTabsJson NVARCHAR(MAX) NULL
        END
        """
    )
    cursor.execute(
        """
        IF COL_LENGTH('dbo.TaskFollow', 'TrackingNumber') IS NULL
        BEGIN
            ALTER TABLE dbo.TaskFollow
            ADD TrackingNumber NVARCHAR(100) NULL
        END
        """
    )

    if schema_changed:
        cursor.connection.commit()

    return schema_changed


def bootstrap_task_follow_schema():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ensure_task_follow_training_columns(cursor)
        conn.commit()
    finally:
        if conn:
            conn.close()


def serialize_training_form_json(value):
    try:
        if not value:
            return ""
        return json.dumps(value, ensure_ascii=True)
    except Exception:
        return ""


def parse_training_form_json(value):
    raw_text = normalize_text(value)
    if not raw_text:
        return []
    try:
        payload = json.loads(raw_text)
    except Exception:
        return []
    return payload if isinstance(payload, list) else []
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1
            FROM sys.indexes
            WHERE name = 'IX_TaskFollowRecipient_TaskID'
              AND object_id = OBJECT_ID('dbo.TaskFollowRecipient')
        )
        BEGIN
            CREATE INDEX IX_TaskFollowRecipient_TaskID
            ON dbo.TaskFollowRecipient(TaskID)
        END
        """
    )
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1
            FROM sys.indexes
            WHERE name = 'IX_TaskFollowRecipient_Username'
              AND object_id = OBJECT_ID('dbo.TaskFollowRecipient')
        )
        BEGIN
            CREATE INDEX IX_TaskFollowRecipient_Username
            ON dbo.TaskFollowRecipient(Username)
        END
        """
    )


def parse_deadline_parts(deadline_date, deadline_time, deadline_period):
    deadline_date_text = normalize_text(deadline_date)
    deadline_time_text = normalize_text(deadline_time)
    deadline_period_text = normalize_text(deadline_period).upper()

    if not deadline_date_text:
        return None, None, None

    try:
        parsed_date = datetime.strptime(deadline_date_text, "%d-%m-%Y").date()
    except ValueError:
        return None, None, "Deadline date must be DD-MM-YYYY."

    if not deadline_time_text:
        return parsed_date, None, None

    if deadline_period_text not in {"AM", "PM"}:
        return None, None, "Deadline period must be AM or PM."

    try:
        parsed_time = datetime.strptime(f"{deadline_time_text} {deadline_period_text}", "%I:%M %p").time()
    except ValueError:
        return None, None, "Deadline time is invalid."

    return parsed_date, parsed_time, None


def serialize_deadline(deadline_date, deadline_time):
    deadline_date_text = ""
    deadline_time_text = ""
    deadline_period = "AM"
    deadline_full = ""

    if deadline_date:
        deadline_date_text = deadline_date.strftime("%d-%m-%Y")

    if deadline_time:
        deadline_time_text = deadline_time.strftime("%I:%M")
        deadline_period = deadline_time.strftime("%p")

    if deadline_date_text:
        deadline_full = deadline_date_text
        if deadline_time_text:
            deadline_full = f"{deadline_date_text} {deadline_time_text} {deadline_period}"

    return deadline_date_text, deadline_time_text, deadline_period, deadline_full


def is_task_in_board_scope(status, deadline_date, today=None):
    normalized_status = normalize_status(status)
    if normalized_status == "DONE" or not deadline_date:
        return False

    today = today or datetime.now().date()
    return is_task_in_board_window(deadline_date, today)


def is_task_in_board_window(deadline_date, today=None):
    if not deadline_date:
        return False

    today = today or datetime.now().date()
    return deadline_date < today or (deadline_date >= today and deadline_date <= today + timedelta(days=3))


def parse_handoff_summary(handoff_to_type, handoff_to_username, handoff_to_display_name):
    normalized_type = normalize_text(handoff_to_type).upper()
    username_text = normalize_text(handoff_to_username)
    display_text = normalize_text(handoff_to_display_name)

    if normalized_type == "TEAM":
        return {
            "type": "TEAM",
            "summary": display_text or "Tech Team",
            "usernames": [],
            "display_names": ["Tech Team"] if not display_text else [display_text],
        }

    display_names = [part.strip() for part in display_text.split(",") if part.strip()] if display_text else []
    usernames = [part.strip() for part in username_text.split(",") if part.strip()] if username_text else []
    if normalized_type == "USER" and not display_names and display_text:
        display_names = [display_text]
    if normalized_type == "USER" and not usernames and username_text:
        usernames = [username_text]

    if normalized_type not in {"USER", "USERS"}:
        normalized_type = "USERS" if len(display_names) > 1 else "USER"

    summary = ", ".join(display_names) if display_names else display_text
    return {
        "type": normalized_type,
        "summary": summary,
        "usernames": usernames,
        "display_names": display_names,
    }


def get_task_recipients(cursor, task_id):
    ensure_task_follow_recipient_table(cursor)
    cursor.execute(
        """
        SELECT RecipientType, Username, DisplayName
        FROM dbo.TaskFollowRecipient
        WHERE TaskID = ?
        ORDER BY
            CASE WHEN UPPER(ISNULL(RecipientType, '')) = 'TEAM' THEN 0 ELSE 1 END,
            COALESCE(DisplayName, Username),
            Username
        """,
        (task_id,),
    )
    rows = cursor.fetchall()
    recipients = []
    for row in rows:
        recipient_type = normalize_text(row.RecipientType).upper() or "USER"
        display_name = normalize_text(row.DisplayName)
        username = normalize_username(row.Username)
        recipients.append(
            {
                "type": recipient_type,
                "username": username,
                "display_name": display_name or ("Tech Team" if recipient_type == "TEAM" else username),
            }
        )
    return recipients


def build_task_response(row, history_items=None, recipient_items=None):
    deadline_date_text, deadline_time_text, deadline_period, deadline_full = serialize_deadline(
        row.DeadlineDate,
        row.DeadlineTime,
    )
    recipients = recipient_items or []
    if recipients:
        handoff_to_type = "TEAM"
        handoff_to_usernames = []
        handoff_to_display_names = []
        team_recipients = [item for item in recipients if normalize_text(item.get("type")).upper() == "TEAM"]
        user_recipients = [item for item in recipients if normalize_text(item.get("type")).upper() != "TEAM"]
        if user_recipients:
            handoff_to_type = "USER" if len(user_recipients) == 1 else "USERS"
            handoff_to_usernames = [normalize_username(item.get("username")) for item in user_recipients if normalize_username(item.get("username"))]
            handoff_to_display_names = [normalize_text(item.get("display_name")) for item in user_recipients if normalize_text(item.get("display_name"))]
        elif team_recipients:
            handoff_to_display_names = [normalize_text(team_recipients[0].get("display_name")) or "Tech Team"]
        handoff_to_summary = ", ".join(handoff_to_display_names) if handoff_to_display_names else "Tech Team"
        handoff_to_username = handoff_to_usernames[0] if len(handoff_to_usernames) == 1 else ""
    else:
        parsed_handoff = parse_handoff_summary(row.HandoffToType, row.HandoffToUsername, row.HandoffToDisplayName)
        handoff_to_type = parsed_handoff["type"]
        handoff_to_usernames = parsed_handoff["usernames"]
        handoff_to_display_names = parsed_handoff["display_names"]
        handoff_to_summary = parsed_handoff["summary"]
        handoff_to_username = handoff_to_usernames[0] if len(handoff_to_usernames) == 1 else ""

    return {
        "task_id": row.TaskID,
        "task_date": row.TaskDate.strftime("%d-%m-%Y") if row.TaskDate else "",
        "merchant_raw": normalize_text(row.MerchantRawText),
        "merchant_name": normalize_text(row.MerchantName),
        "zip_code": normalize_text(row.ZipCode),
        "phone": normalize_text(row.Phone),
        "tracking_number": normalize_tracking_number(getattr(row, "TrackingNumber", "")),
        "problem": normalize_text(row.ProblemSummary),
        "handoff_from_username": normalize_text(row.HandoffFromUsername),
        "handoff_from": normalize_text(row.HandoffFromDisplayName),
        "handoff_to_type": handoff_to_type,
        "handoff_to_username": handoff_to_username,
        "handoff_to_usernames": handoff_to_usernames,
        "handoff_to_display_names": handoff_to_display_names,
        "handoff_to": handoff_to_summary,
        "status": normalize_status(row.Status),
        "deadline": deadline_full,
        "deadline_date": deadline_date_text,
        "deadline_time": deadline_time_text,
        "deadline_period": deadline_period,
        "note": normalize_text(row.CurrentNote),
        "updated_at": row.UpdatedAt.strftime("%d-%m-%Y %I:%M %p") if row.UpdatedAt else "",
        "training_form": parse_training_form_json(getattr(row, "TrainingFormJson", "")),
        "training_started_at": (
            row.TrainingStartedAt.strftime("%d-%m-%Y %I:%M %p")
            if getattr(row, "TrainingStartedAt", None)
            else ""
        ),
        "training_started_by_username": normalize_text(getattr(row, "TrainingStartedByUsername", "")),
        "training_started_by_display_name": normalize_text(getattr(row, "TrainingStartedByDisplayName", "")),
        "training_completed_tabs": parse_training_form_json(getattr(row, "TrainingCompletedTabsJson", "")) or [],
        "history": history_items or [],
    }


def format_deadline_label(deadline_date, deadline_time):
    deadline_date_text, deadline_time_text, deadline_period, deadline_full = serialize_deadline(
        deadline_date,
        deadline_time,
    )
    if deadline_full:
        return deadline_full
    return deadline_date_text


def normalize_handoff_targets(cursor, data):
    raw_type = normalize_text(getattr(data, "handoff_to_type", "")).upper()
    raw_usernames = [normalize_username(value) for value in (getattr(data, "handoff_to_usernames", []) or []) if normalize_username(value)]
    raw_display_names = [normalize_text(value) for value in (getattr(data, "handoff_to_display_names", []) or []) if normalize_text(value)]
    single_username = normalize_username(getattr(data, "handoff_to_username", ""))
    single_display_name = normalize_text(getattr(data, "handoff_to_display_name", ""))

    if raw_type == "TEAM":
        return {
            "type": "TEAM",
            "summary_username": "",
            "summary_display_name": "Tech Team",
            "recipients": [{"type": "TEAM", "username": "", "display_name": "Tech Team"}],
        }

    if single_username and single_username not in raw_usernames:
        raw_usernames.append(single_username)
    if single_display_name and single_display_name not in raw_display_names:
        raw_display_names.append(single_display_name)

    recipients = []
    for index, username in enumerate(raw_usernames):
        display_name = raw_display_names[index] if index < len(raw_display_names) and normalize_text(raw_display_names[index]) else ""
        resolved_display_name = display_name or get_user_display_name(cursor, username) or username
        recipients.append(
            {
                "type": "USER",
                "username": username,
                "display_name": resolved_display_name,
            }
        )

    if not recipients and single_display_name and raw_type in {"USER", "USERS"}:
        return {
            "type": "TEAM" if single_display_name == "Tech Team" else "",
            "summary_username": "",
            "summary_display_name": single_display_name,
            "recipients": [],
        }

    if not recipients:
        return {
            "type": "",
            "summary_username": "",
            "summary_display_name": "",
            "recipients": [],
        }

    return {
        "type": "USER" if len(recipients) == 1 else "USERS",
        "summary_username": recipients[0]["username"] if len(recipients) == 1 else "",
        "summary_display_name": ", ".join([item["display_name"] for item in recipients]),
        "recipients": recipients,
    }


def serialize_recipient_signature(recipients):
    normalized = []
    for item in recipients or []:
        recipient_type = normalize_text(item.get("type")).upper() or "USER"
        username = normalize_username(item.get("username"))
        display_name = normalize_text(item.get("display_name"))
        normalized.append(
            (
                recipient_type,
                username,
                display_name or ("Tech Team" if recipient_type == "TEAM" else username),
            )
        )
    return tuple(sorted(normalized))


def is_notification_refresh_relevant(status_changed, recipient_changed):
    return bool(status_changed or recipient_changed)


def replace_task_recipients(cursor, task_id, recipients):
    ensure_task_follow_recipient_table(cursor)
    cursor.execute("DELETE FROM dbo.TaskFollowRecipient WHERE TaskID = ?", (task_id,))
    for recipient in recipients or []:
        cursor.execute(
            """
            INSERT INTO dbo.TaskFollowRecipient
            (
                TaskID,
                RecipientType,
                Username,
                DisplayName
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                task_id,
                normalize_text(recipient.get("type")).upper() or "USER",
                normalize_username(recipient.get("username")),
                normalize_text(recipient.get("display_name")),
            ),
        )


def get_task_by_id(cursor, task_id):
    cursor.execute(
        """
        SELECT
            TaskID,
            TaskDate,
            MerchantRawText,
            MerchantName,
            ZipCode,
            Phone,
            TrackingNumber,
            ProblemSummary,
            HandoffFromUsername,
            HandoffFromDisplayName,
            HandoffToType,
            HandoffToUsername,
            HandoffToDisplayName,
            Status,
            DeadlineDate,
            DeadlineTime,
            CurrentNote,
            UpdatedAt,
            TrainingFormJson,
            TrainingStartedAt,
            TrainingStartedByUsername,
            TrainingStartedByDisplayName
        FROM dbo.TaskFollow
        WHERE TaskID = ? AND IsActive = 1
        """,
        (task_id,),
    )
    return cursor.fetchone()


def get_task_logs(cursor, task_id):
    cursor.execute(
        """
        SELECT
            LogID,
            ActionType,
            Note,
            Status,
            HandoffFromUsername,
            HandoffFromDisplayName,
            HandoffToType,
            HandoffToUsername,
            HandoffToDisplayName,
            UpdatedByUsername,
            UpdatedByDisplayName,
            CreatedAt
        FROM dbo.TaskFollowLog
        WHERE TaskID = ?
        ORDER BY CreatedAt DESC, LogID DESC
        """,
        (task_id,),
    )
    rows = cursor.fetchall()

    history = []
    for row in rows:
        history.append(
            {
                "log_id": row.LogID,
                "action_type": normalize_text(row.ActionType),
                "user": normalize_text(row.UpdatedByDisplayName) or normalize_text(row.UpdatedByUsername),
                "username": normalize_text(row.UpdatedByUsername),
                "time": row.CreatedAt.strftime("%d-%m-%Y %I:%M %p") if row.CreatedAt else "",
                "note": normalize_text(row.Note),
                "status": normalize_status(row.Status),
                "handoff_from": normalize_text(row.HandoffFromDisplayName),
                "handoff_to": normalize_text(row.HandoffToDisplayName),
                "handoff_to_type": normalize_text(row.HandoffToType),
            }
        )

    return history


def build_history_note(action_type, status, note, actor_display_name):
    normalized_action = normalize_text(action_type).upper()
    normalized_status = normalize_status(status)
    normalized_note = normalize_text(note)
    actor_name = normalize_text(actor_display_name) or "Someone"

    if normalized_action == "UPDATE" and normalized_status == "DONE" and normalized_note:
        return f"{actor_name} has marked the task as done with note: {normalized_note}"

    return normalized_note


def build_assignment_note(actor_display_name, handoff_to_type, handoff_to_display_name):
    actor_name = normalize_text(actor_display_name) or "Someone"
    target_type = normalize_text(handoff_to_type).upper()
    target_display = normalize_text(handoff_to_display_name) or "Tech Team"

    if target_type == "TEAM":
        return f"{actor_name} assigned task to Tech Team"

    return f"{actor_name} assigned task to {target_display}"


def insert_task_log(cursor, task_id, action_type, payload, actor_display_name):
    history_note = build_history_note(
        action_type,
        payload["status"],
        payload["note"],
        actor_display_name,
    )

    log_values = (
        task_id,
        normalize_text(action_type),
        history_note,
        normalize_status(payload["status"]),
        normalize_username(payload["handoff_from_username"]),
        normalize_text(payload["handoff_from_display_name"]),
        normalize_text(payload["handoff_to_type"]),
        normalize_username(payload["handoff_to_username"]),
        normalize_text(payload["handoff_to_display_name"]),
        normalize_username(payload["action_by_username"]),
        normalize_text(actor_display_name),
    )

    try:
        cursor.execute(
            """
            INSERT INTO dbo.TaskFollowLog
            (
                TaskID,
                ActionType,
                Note,
                Status,
                HandoffFromUsername,
                HandoffFromDisplayName,
                HandoffToType,
                HandoffToUsername,
                HandoffToDisplayName,
                UpdatedByUsername,
                UpdatedByDisplayName
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            log_values,
        )
        return
    except Exception as e:
        if not is_null_insert_id_error(e, "LogID"):
            raise

    next_log_id = get_next_int_id(cursor, "dbo.TaskFollowLog", "LogID")
    cursor.execute(
        """
        INSERT INTO dbo.TaskFollowLog
        (
            LogID,
            TaskID,
            ActionType,
            Note,
            Status,
            HandoffFromUsername,
            HandoffFromDisplayName,
            HandoffToType,
            HandoffToUsername,
            HandoffToDisplayName,
            UpdatedByUsername,
            UpdatedByDisplayName
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (next_log_id, *log_values),
    )


def insert_assignment_log(cursor, task_id, payload, actor_display_name):
    assign_note = build_assignment_note(
        actor_display_name,
        payload["handoff_to_type"],
        payload["handoff_to_display_name"],
    )

    assignment_payload = dict(payload)
    assignment_payload["note"] = assign_note
    insert_task_log(cursor, task_id, "ASSIGN", assignment_payload, actor_display_name)


@router.get("/task-follows/handoff-options")
def get_task_follow_handoff_options(action_by: str, task_date: str = "", task_time: str = "", task_period: str = ""):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        action_by = normalize_username(action_by)
        if not action_by:
            return {"success": False, "message": "Missing action_by."}

        task_date_text = normalize_text(task_date)
        if task_date_text:
            try:
                effective_date = datetime.strptime(task_date_text, "%d-%m-%Y").date()
            except ValueError:
                return {"success": False, "message": "task_date must be DD-MM-YYYY."}
        else:
            effective_date = datetime.now().date()

        effective_day_name = effective_date.strftime("%a").upper()[:3]
        effective_work_date = effective_date.strftime("%Y-%m-%d")

        def parse_ui_time(time_text: str, period_text: str):
            raw_time = normalize_text(time_text)
            raw_period = normalize_text(period_text).upper()
            if not raw_time or raw_period not in {"AM", "PM"}:
                return None
            try:
                return datetime.strptime(f"{raw_time} {raw_period}", "%I:%M %p").time()
            except ValueError:
                return None

        def parse_time_range(range_text: str):
            text = normalize_text(range_text)
            if not text or "-" not in text:
                return None, None
            parts = [part.strip() for part in text.split("-", 1)]
            if len(parts) != 2:
                return None, None
            try:
                start_time = datetime.strptime(parts[0], "%I:%M %p").time()
                end_time = datetime.strptime(parts[1], "%I:%M %p").time()
                return start_time, end_time
            except ValueError:
                return None, None

        def time_within_shift(target, start, end):
            if target is None or start is None or end is None:
                return True
            start_dt = datetime.combine(datetime(2000, 1, 1).date(), start)
            end_dt = datetime.combine(datetime(2000, 1, 1).date(), end)
            target_dt = datetime.combine(datetime(2000, 1, 1).date(), target)
            if end_dt < start_dt:
                # overnight shift (e.g. 10 PM - 7 AM)
                if target_dt < start_dt:
                    target_dt = target_dt.replace(day=2)
                end_dt = end_dt.replace(day=2)
            return start_dt <= target_dt <= end_dt

        target_time = parse_ui_time(task_time, task_period)

        cursor.execute(
            """
            SELECT Department
            FROM dbo.Users
            WHERE Username = ?
            """,
            (action_by,),
        )
        row = cursor.fetchone()
        if not row:
            return {"success": False, "message": "User not found."}

        current_display_name = get_user_display_name(cursor, action_by) or action_by
        department = normalize_text(row[0])

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo'
              AND TABLE_NAME = 'TechScheduleEmployeeConfig'
            """
        )
        has_schedule_setup = cursor.fetchone()[0] > 0

        options = [{"username": "", "display_name": "Tech Team", "type": "TEAM"}]

        if has_schedule_setup:
            cursor.execute(
                """
                SELECT Username, DisplayName, OffDays
                FROM dbo.TechScheduleEmployeeConfig
                WHERE IsActive = 1
                  AND Department = ?
                ORDER BY COALESCE(DisplayName, Username), Username
                """,
                (department,),
            )
            rows = cursor.fetchall()

            schedule_status_map = {}
            schedule_time_range_map = {}
            try:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = 'dbo'
                      AND TABLE_NAME = 'TechSchedule'
                    """
                )
                has_tech_schedule = cursor.fetchone()[0] > 0
            except Exception:
                has_tech_schedule = False

            if has_tech_schedule and rows:
                usernames = [normalize_username(r[0]) for r in rows if normalize_username(r[0])]
                if usernames:
                    placeholders = ",".join(["?"] * len(usernames))
                    cursor.execute(
                        f"""
                        SELECT Username, StatusCode, VNTimeRange
                        FROM dbo.TechSchedule
                        WHERE WorkDate = ?
                          AND Username IN ({placeholders})
                        """,
                        (effective_work_date, *usernames),
                    )
                    for schedule_row in cursor.fetchall():
                        schedule_username = normalize_username(schedule_row[0])
                        if not schedule_username:
                            continue
                        schedule_status_map[schedule_username.lower()] = normalize_text(schedule_row[1]).upper()
                        schedule_time_range_map[schedule_username.lower()] = normalize_text(schedule_row[2])
            for option_row in rows:
                username = normalize_username(option_row[0])
                display_name = normalize_text(option_row[1]) or username
                off_days_text = normalize_text(option_row[2])
                off_days = [part.strip().upper() for part in off_days_text.split(",") if part.strip()] if off_days_text else []
                if not username:
                    continue
                status_code = schedule_status_map.get(username.lower())
                if status_code and status_code != "WORK":
                    continue
                if target_time is not None:
                    vn_time_range_text = schedule_time_range_map.get(username.lower(), "")
                    start_time, end_time = parse_time_range(vn_time_range_text)
                    if start_time and end_time and not time_within_shift(target_time, start_time, end_time):
                        continue
                if effective_day_name in off_days:
                    continue
                options.append(
                    {
                        "username": username,
                        "display_name": display_name,
                        "type": "USER",
                    }
                )

        return {
            "success": True,
            "current_display_name": current_display_name,
            "data": options,
        }

    except Exception as e:
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.get("/task-follows")
def get_task_follows(action_by: str, search: str = "", show_all: bool = False, include_done: bool = False):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        action_by = normalize_username(action_by)
        if not action_by:
            return {"success": False, "message": "Missing action_by."}

        cursor.execute("SELECT Username FROM dbo.Users WHERE Username = ?", (action_by,))
        if not cursor.fetchone():
            return {"success": False, "message": "User not found."}

        ensure_task_follow_training_columns(cursor)

        today = datetime.now().date()
        search_keyword = normalize_text(search)

        query = """
            SELECT
                TaskID,
                TaskDate,
                MerchantRawText,
                MerchantName,
                ZipCode,
                Phone,
                TrackingNumber,
                ProblemSummary,
                HandoffFromUsername,
                HandoffFromDisplayName,
                HandoffToType,
                HandoffToUsername,
                HandoffToDisplayName,
                Status,
                DeadlineDate,
                DeadlineTime,
                CurrentNote,
                UpdatedAt,
                TrainingFormJson,
                TrainingStartedAt,
                TrainingStartedByUsername,
                TrainingStartedByDisplayName
            FROM dbo.TaskFollow
            WHERE IsActive = 1
        """
        params = []
        board_filter_applied = not show_all

        if not include_done:
            query += " AND UPPER(Status) <> 'DONE'"

        if board_filter_applied:
            query += """
              AND DeadlineDate IS NOT NULL
              AND (
                    DeadlineDate < ?
                    OR (DeadlineDate >= ? AND DeadlineDate <= DATEADD(DAY, 3, ?))
                  )
            """
            params.extend([today, today, today])

        if search_keyword:
            query += " AND MerchantName LIKE ?"
            params.append(f"%{search_keyword}%")

        if board_filter_applied:
            query += """
                ORDER BY
                    DeadlineDate ASC,
                    CASE WHEN DeadlineTime IS NULL THEN 1 ELSE 0 END,
                    DeadlineTime ASC,
                    UpdatedAt DESC
            """
        else:
            query += """
                ORDER BY
                    CASE WHEN DeadlineDate IS NULL THEN 1 ELSE 0 END,
                    DeadlineDate ASC,
                    CASE WHEN DeadlineTime IS NULL THEN 1 ELSE 0 END,
                    DeadlineTime ASC,
                    UpdatedAt DESC
            """

        cursor.execute(query, params)
        rows = cursor.fetchall()

        data = [build_task_response(row) for row in rows]
        if board_filter_applied:
            search_scope = "board"
        elif include_done:
            search_scope = "show_all_with_done"
        else:
            search_scope = "show_all_active_not_done"

        return {
            "success": True,
            "data": data,
            "board_filter_applied": board_filter_applied,
            "search_scope": search_scope,
            "show_all": bool(show_all),
            "include_done": bool(include_done),
        }

    except Exception as e:
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.get("/task-follows/notifications")
def get_task_follow_notifications(action_by: str):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        action_by = normalize_username(action_by)
        if not action_by:
            return {"success": False, "message": "Missing action_by."}

        cursor.execute("SELECT Username, Department FROM dbo.Users WHERE Username = ?", (action_by,))
        user_row = cursor.fetchone()
        if not user_row:
            return {"success": False, "message": "User not found."}
        current_department = normalize_text(user_row[1])
        is_technical_support_user = current_department == "Technical Support"

        ensure_task_follow_notification_read_table(cursor)
        ensure_task_follow_notification_dismiss_table(cursor)
        ensure_task_follow_recipient_table(cursor)

        cursor.execute(
            """
            SELECT
                TOP 20
                tf.TaskID,
                tf.MerchantName,
                tf.ZipCode,
                tf.Status,
                tf.DeadlineDate,
                tf.DeadlineTime,
                tf.HandoffFromDisplayName,
                tf.UpdatedAt,
                CASE
                    WHEN nr.TaskID IS NOT NULL
                     AND nr.ReadAt >= ISNULL(tf.UpdatedAt, GETDATE())
                    THEN 1
                    ELSE 0
                END AS IsRead
            FROM dbo.TaskFollow tf
            LEFT JOIN dbo.TaskFollowNotificationRead nr
                ON nr.TaskID = tf.TaskID
               AND nr.Username = ?
            LEFT JOIN dbo.TaskFollowNotificationDismiss nd
                ON nd.TaskID = tf.TaskID
               AND nd.Username = ?
            LEFT JOIN dbo.TaskFollowRecipient tr
                ON tr.TaskID = tf.TaskID
               AND tr.Username = ?
            WHERE tf.IsActive = 1
              AND UPPER(tf.Status) <> 'DONE'
              AND (
                    nd.TaskID IS NULL
                    OR nd.DismissedAt < ISNULL(tf.UpdatedAt, GETDATE())
                  )
              AND (
                    tr.TaskID IS NOT NULL
                    OR (
                        UPPER(ISNULL(tf.HandoffToType, '')) = 'USER'
                        AND tf.HandoffToUsername = ?
                    )
                    OR (
                        ? = 1
                        AND UPPER(ISNULL(tf.HandoffToType, '')) = 'TEAM'
                    )
                  )
            ORDER BY
                tf.UpdatedAt DESC,
                tf.TaskID DESC
            """,
            (action_by, action_by, action_by, action_by, 1 if is_technical_support_user else 0),
        )
        rows = cursor.fetchall()

        items = []
        unread_count = 0
        for row in rows:
            merchant_name = normalize_text(row.MerchantName) or f"Task #{row.TaskID}"
            zip_code = normalize_text(row.ZipCode)
            title = merchant_name if not zip_code else f"{merchant_name} {zip_code}"
            status_text = normalize_status(row.Status) or "FOLLOW"
            handoff_from = normalize_text(row.HandoffFromDisplayName) or "Someone"
            deadline_label = format_deadline_label(row.DeadlineDate, row.DeadlineTime)
            is_read = bool(getattr(row, "IsRead", 0))
            meta_parts = [f"From {handoff_from}", status_text]
            if deadline_label:
                meta_parts.append(deadline_label)

            items.append(
                {
                    "id": f"task-{row.TaskID}",
                    "task_id": row.TaskID,
                    "title": title,
                    "meta": " | ".join(meta_parts),
                    "task_section": "follow",
                    "is_read": is_read,
                }
            )
            if not is_read:
                unread_count += 1

        return {
            "success": True,
            "unread_count": unread_count,
            "data": items,
        }

    except Exception as e:
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.get("/task-follows/notifications/count")
def get_task_follow_notification_count(action_by: str):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        action_by = normalize_username(action_by)
        if not action_by:
            return {"success": False, "message": "Missing action_by."}

        cursor.execute("SELECT Username, Department FROM dbo.Users WHERE Username = ?", (action_by,))
        user_row = cursor.fetchone()
        if not user_row:
            return {"success": False, "message": "User not found."}
        current_department = normalize_text(user_row[1])
        is_technical_support_user = current_department == "Technical Support"

        ensure_task_follow_notification_read_table(cursor)
        ensure_task_follow_notification_dismiss_table(cursor)
        ensure_task_follow_recipient_table(cursor)

        cursor.execute(
            """
            SELECT
                COUNT(DISTINCT tf.TaskID) AS UnreadCount,
                MAX(tf.UpdatedAt) AS LatestUpdatedAt
            FROM dbo.TaskFollow tf
            LEFT JOIN dbo.TaskFollowNotificationRead nr
                ON nr.TaskID = tf.TaskID
               AND nr.Username = ?
            LEFT JOIN dbo.TaskFollowNotificationDismiss nd
                ON nd.TaskID = tf.TaskID
               AND nd.Username = ?
            LEFT JOIN dbo.TaskFollowRecipient tr
                ON tr.TaskID = tf.TaskID
               AND tr.Username = ?
            WHERE tf.IsActive = 1
              AND UPPER(tf.Status) <> 'DONE'
              AND (
                    nd.TaskID IS NULL
                    OR nd.DismissedAt < ISNULL(tf.UpdatedAt, GETDATE())
                  )
              AND (
                    tr.TaskID IS NOT NULL
                    OR (
                        UPPER(ISNULL(tf.HandoffToType, '')) = 'USER'
                        AND tf.HandoffToUsername = ?
                    )
                    OR (
                        ? = 1
                        AND UPPER(ISNULL(tf.HandoffToType, '')) = 'TEAM'
                    )
                  )
              AND (
                    nr.TaskID IS NULL
                    OR nr.ReadAt < ISNULL(tf.UpdatedAt, GETDATE())
                  )
            """,
            (action_by, action_by, action_by, action_by, 1 if is_technical_support_user else 0),
        )
        row = cursor.fetchone()
        latest_updated_at = None
        if row and getattr(row, "LatestUpdatedAt", None):
            latest_updated_at = row.LatestUpdatedAt.strftime("%Y-%m-%d %H:%M:%S")

        return {
            "success": True,
            "unread_count": int(getattr(row, "UnreadCount", 0) or 0) if row else 0,
            "latest_updated_at": latest_updated_at,
        }

    except Exception as e:
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.get("/task-follows/{task_id}")
def get_task_follow_detail(task_id: int, action_by: str = ""):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ensure_task_follow_training_columns(cursor)

        row = get_task_by_id(cursor, task_id)
        if not row:
            return {"success": False, "message": "Task not found."}

        history = get_task_logs(cursor, task_id)
        recipients = get_task_recipients(cursor, task_id)
        return {"success": True, "data": build_task_response(row, history, recipients)}

    except Exception as e:
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.post("/task-follows/notifications/read")
def mark_task_follow_notifications_read(data: TaskFollowNotificationReadRequest):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        action_by_username = normalize_username(data.action_by_username)
        if not action_by_username:
            return {"success": False, "message": "Missing action_by_username."}

        cursor.execute("SELECT Username FROM dbo.Users WHERE Username = ?", (action_by_username,))
        if not cursor.fetchone():
            return {"success": False, "message": "User not found."}

        ensure_task_follow_training_columns(cursor)

        ensure_task_follow_notification_read_table(cursor)
        ensure_task_follow_recipient_table(cursor)
        user_department = get_user_department(cursor, action_by_username)
        is_technical_support_user = user_department == "Technical Support"

        normalized_task_ids = []
        for raw_task_id in data.task_ids or []:
            try:
                task_id = int(raw_task_id)
            except (TypeError, ValueError):
                continue
            if task_id > 0 and task_id not in normalized_task_ids:
                normalized_task_ids.append(task_id)

        if not normalized_task_ids:
            return {"success": True, "marked_count": 0, "task_ids": []}

        placeholders = ",".join(["?"] * len(normalized_task_ids))
        cursor.execute(
            f"""
            SELECT DISTINCT tf.TaskID
            FROM dbo.TaskFollow tf
            LEFT JOIN dbo.TaskFollowRecipient tr
              ON tr.TaskID = tf.TaskID
             AND tr.Username = ?
            WHERE tf.IsActive = 1
              AND (
                    tr.TaskID IS NOT NULL
                    OR (
                        UPPER(ISNULL(tf.HandoffToType, '')) = 'USER'
                        AND tf.HandoffToUsername = ?
                    )
                    OR (
                        ? = 1
                        AND UPPER(ISNULL(tf.HandoffToType, '')) = 'TEAM'
                    )
                  )
              AND tf.TaskID IN ({placeholders})
            """,
            (action_by_username, action_by_username, 1 if is_technical_support_user else 0, *normalized_task_ids),
        )
        valid_task_ids = [int(row[0]) for row in cursor.fetchall() if row and row[0] is not None]

        marked_count = 0
        for task_id in valid_task_ids:
            cursor.execute(
                """
                IF EXISTS (
                    SELECT 1
                    FROM dbo.TaskFollowNotificationRead
                    WHERE TaskID = ? AND Username = ?
                )
                BEGIN
                    UPDATE dbo.TaskFollowNotificationRead
                    SET ReadAt = GETDATE()
                    WHERE TaskID = ? AND Username = ?
                END
                ELSE
                BEGIN
                    INSERT INTO dbo.TaskFollowNotificationRead (TaskID, Username, ReadAt)
                    VALUES (?, ?, GETDATE())
                END
                """,
                (
                    task_id,
                    action_by_username,
                    task_id,
                    action_by_username,
                    task_id,
                    action_by_username,
                ),
            )
            marked_count += 1

        conn.commit()
        return {
            "success": True,
            "marked_count": marked_count,
            "task_ids": valid_task_ids,
        }

    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.post("/task-follows/notifications/clear")
def clear_task_follow_notifications(data: TaskFollowNotificationClearRequest):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        action_by_username = normalize_username(data.action_by_username)
        if not action_by_username:
            return {"success": False, "message": "Missing action_by_username."}

        cursor.execute("SELECT Username FROM dbo.Users WHERE Username = ?", (action_by_username,))
        if not cursor.fetchone():
            return {"success": False, "message": "User not found."}

        ensure_task_follow_notification_dismiss_table(cursor)
        ensure_task_follow_recipient_table(cursor)
        user_department = get_user_department(cursor, action_by_username)
        is_technical_support_user = user_department == "Technical Support"

        normalized_task_ids = []
        for raw_task_id in data.task_ids or []:
            try:
                task_id = int(raw_task_id)
            except (TypeError, ValueError):
                continue
            if task_id > 0 and task_id not in normalized_task_ids:
                normalized_task_ids.append(task_id)

        if not normalized_task_ids:
            return {"success": True, "cleared_count": 0, "task_ids": []}

        placeholders = ",".join(["?"] * len(normalized_task_ids))
        cursor.execute(
            f"""
            SELECT DISTINCT tf.TaskID
            FROM dbo.TaskFollow tf
            LEFT JOIN dbo.TaskFollowRecipient tr
              ON tr.TaskID = tf.TaskID
             AND tr.Username = ?
            WHERE tf.IsActive = 1
              AND UPPER(tf.Status) <> 'DONE'
              AND (
                    tr.TaskID IS NOT NULL
                    OR (
                        UPPER(ISNULL(tf.HandoffToType, '')) = 'USER'
                        AND tf.HandoffToUsername = ?
                    )
                    OR (
                        ? = 1
                        AND UPPER(ISNULL(tf.HandoffToType, '')) = 'TEAM'
                    )
                  )
              AND tf.TaskID IN ({placeholders})
            """,
            (action_by_username, action_by_username, 1 if is_technical_support_user else 0, *normalized_task_ids),
        )
        valid_task_ids = [int(row[0]) for row in cursor.fetchall() if row and row[0] is not None]

        cleared_count = 0
        for task_id in valid_task_ids:
            cursor.execute(
                """
                IF EXISTS (
                    SELECT 1
                    FROM dbo.TaskFollowNotificationDismiss
                    WHERE TaskID = ? AND Username = ?
                )
                BEGIN
                    UPDATE dbo.TaskFollowNotificationDismiss
                    SET DismissedAt = GETDATE()
                    WHERE TaskID = ? AND Username = ?
                END
                ELSE
                BEGIN
                    INSERT INTO dbo.TaskFollowNotificationDismiss (TaskID, Username, DismissedAt)
                    VALUES (?, ?, GETDATE())
                END
                """,
                (
                    task_id,
                    action_by_username,
                    task_id,
                    action_by_username,
                    task_id,
                    action_by_username,
                ),
            )
            cleared_count += 1

        conn.commit()
        return {
            "success": True,
            "cleared_count": cleared_count,
            "task_ids": valid_task_ids,
        }

    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.post("/task-follows")
def create_task_follow(data: TaskFollowUpsertRequest):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ensure_task_follow_training_columns(cursor)

        action_by_username = normalize_username(data.action_by_username)
        if not action_by_username:
            return {"success": False, "message": "Missing action_by_username."}

        cursor.execute("SELECT Username FROM dbo.Users WHERE Username = ?", (action_by_username,))
        if not cursor.fetchone():
            return {"success": False, "message": "User not found."}

        raw_text, merchant_name, zip_code = parse_merchant_fields(data.merchant_raw_text)
        if not raw_text or not merchant_name:
            return {"success": False, "message": "Merchant name is required."}

        status = normalize_status(data.status)
        if status not in ALLOWED_STATUSES:
            return {"success": False, "message": "Status is invalid."}

        tracking_number = normalize_tracking_number(getattr(data, "tracking_number", ""))
        if status == "SHIP OUT" and not tracking_number:
            return {"success": False, "message": "Tracking number is required for SHIP OUT."}

        note_text = normalize_text(data.note)
        if status == "DONE" and not note_text:
            return {"success": False, "message": "Note is required when status is DONE."}

        deadline_date, deadline_time, deadline_error = parse_deadline_parts(
            data.deadline_date,
            data.deadline_time,
            data.deadline_period,
        )
        if deadline_error:
            return {"success": False, "message": deadline_error}

        actor_display_name = get_user_display_name(cursor, action_by_username) or action_by_username
        handoff_selection = normalize_handoff_targets(cursor, data)
        handoff_to_type = handoff_selection["type"] or "TEAM"
        handoff_to_username = handoff_selection["summary_username"]
        handoff_to_display_name = handoff_selection["summary_display_name"] or "Tech Team"
        handoff_recipients = handoff_selection["recipients"]
        recipient_changed = True
        status_changed = True
        notification_relevant = bool(status != "DONE")

        if handoff_to_type != "TEAM" and not handoff_recipients:
            return {"success": False, "message": "Handoff target is required."}

        training_form_json = serialize_training_form_json(getattr(data, "training_form", []))
        training_started_by_username = normalize_username(getattr(data, "training_started_by_username", ""))
        training_started_by_display_name = normalize_text(getattr(data, "training_started_by_display_name", ""))
        training_started_at = datetime.now() if normalize_text(getattr(data, "training_started_at", "")) else None
        if training_form_json and not training_started_at:
            training_started_at = datetime.now()
        if training_form_json and not training_started_by_username:
            training_started_by_username = action_by_username
        if training_form_json and not training_started_by_display_name:
            training_started_by_display_name = actor_display_name

        task_values = (
            datetime.now().date(),
            raw_text,
            merchant_name,
            zip_code,
            normalize_text(data.phone),
            tracking_number,
            normalize_text(data.problem_summary),
            action_by_username,
            actor_display_name,
            handoff_to_type,
            handoff_to_username,
            handoff_to_display_name,
            status,
            deadline_date,
            deadline_time,
            note_text,
            action_by_username,
            actor_display_name,
            training_form_json or None,
            training_started_at,
            training_started_by_username,
            training_started_by_display_name,
        )

        task_id = None
        try:
            cursor.execute(
                """
                INSERT INTO dbo.TaskFollow
                (
                    TaskDate,
                    MerchantRawText,
                    MerchantName,
                    ZipCode,
                    Phone,
                    TrackingNumber,
                    ProblemSummary,
                    HandoffFromUsername,
                    HandoffFromDisplayName,
                    HandoffToType,
                    HandoffToUsername,
                    HandoffToDisplayName,
                    Status,
                    DeadlineDate,
                    DeadlineTime,
                    CurrentNote,
                    LastUpdatedByUsername,
                    LastUpdatedByDisplayName,
                    TrainingFormJson,
                    TrainingStartedAt,
                    TrainingStartedByUsername,
                    TrainingStartedByDisplayName,
                    CreatedAt,
                    UpdatedAt,
                    IsActive
                )
                OUTPUT INSERTED.TaskID
                VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), 1)
                """,
                task_values,
            )
            inserted_row = cursor.fetchone()
            task_id = int(inserted_row[0]) if inserted_row and inserted_row[0] is not None else None
        except Exception as e:
            if not is_null_insert_id_error(e, "TaskID"):
                raise

        if task_id is None:
            try:
                task_id = get_next_int_id(cursor, "dbo.TaskFollow", "TaskID")
                cursor.execute(
                    """
                    INSERT INTO dbo.TaskFollow
                    (
                        TaskID,
                        TaskDate,
                        MerchantRawText,
                        MerchantName,
                        ZipCode,
                        Phone,
                        TrackingNumber,
                        ProblemSummary,
                        HandoffFromUsername,
                        HandoffFromDisplayName,
                        HandoffToType,
                        HandoffToUsername,
                        HandoffToDisplayName,
                        Status,
                        DeadlineDate,
                        DeadlineTime,
                        CurrentNote,
                        LastUpdatedByUsername,
                        LastUpdatedByDisplayName,
                        TrainingFormJson,
                        TrainingStartedAt,
                        TrainingStartedByUsername,
                        TrainingStartedByDisplayName,
                        CreatedAt,
                        UpdatedAt,
                        IsActive
                    )
                    VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), 1)
                    """,
                    (task_id, *task_values),
                )
            except Exception as e:
                if is_identity_insert_error(e, "TaskID"):
                    cursor.execute(
                        """
                        INSERT INTO dbo.TaskFollow
                        (
                            TaskDate,
                            MerchantRawText,
                            MerchantName,
                            ZipCode,
                            Phone,
                            TrackingNumber,
                            ProblemSummary,
                            HandoffFromUsername,
                            HandoffFromDisplayName,
                            HandoffToType,
                            HandoffToUsername,
                            HandoffToDisplayName,
                            Status,
                            DeadlineDate,
                            DeadlineTime,
                            CurrentNote,
                            LastUpdatedByUsername,
                            LastUpdatedByDisplayName,
                            TrainingFormJson,
                            TrainingStartedAt,
                            TrainingStartedByUsername,
                            TrainingStartedByDisplayName,
                            CreatedAt,
                            UpdatedAt,
                            IsActive
                        )
                        OUTPUT INSERTED.TaskID
                        VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), 1)
                        """,
                        task_values,
                    )
                    inserted_row = cursor.fetchone()
                    task_id = int(inserted_row[0]) if inserted_row and inserted_row[0] is not None else None
                else:
                    raise

        log_payload = {
            "action_by_username": action_by_username,
            "note": note_text,
            "status": status,
            "handoff_from_username": action_by_username,
            "handoff_from_display_name": actor_display_name,
            "handoff_to_type": handoff_to_type,
            "handoff_to_username": handoff_to_username,
            "handoff_to_display_name": handoff_to_display_name,
        }
        replace_task_recipients(cursor, task_id, handoff_recipients or [{"type": "TEAM", "username": "", "display_name": "Tech Team"}])

        if note_text:
            insert_task_log(cursor, task_id, "CREATE", log_payload, actor_display_name)
        insert_assignment_log(cursor, task_id, log_payload, actor_display_name)

        conn.commit()
        created_row = get_task_by_id(cursor, task_id)
        created_history = get_task_logs(cursor, task_id)
        created_recipients = get_task_recipients(cursor, task_id)
        is_visible_on_board = bool(
            created_row and is_task_in_board_scope(created_row.Status, created_row.DeadlineDate)
        )
        return {
            "success": True,
            "task_id": task_id,
            "data": build_task_response(created_row, created_history, created_recipients) if created_row else None,
            "visible_on_board": is_visible_on_board,
            "notification_relevant": notification_relevant,
            "recipient_changed": recipient_changed,
            "status_changed": status_changed,
            "message": (
                "Task created successfully."
                if is_visible_on_board
                else "Task created successfully, but it is outside the current board filter."
            ),
        }

    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.put("/task-follows/{task_id}")
def update_task_follow(task_id: int, data: TaskFollowUpsertRequest):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ensure_task_follow_training_columns(cursor)

        action_by_username = normalize_username(data.action_by_username)
        if not action_by_username:
            return {"success": False, "message": "Missing action_by_username."}

        cursor.execute("SELECT Username FROM dbo.Users WHERE Username = ?", (action_by_username,))
        if not cursor.fetchone():
            return {"success": False, "message": "User not found."}

        cursor.execute(
            """
            SELECT TaskID
            FROM dbo.TaskFollow
            WHERE TaskID = ? AND IsActive = 1
            """,
            (task_id,),
        )
        if not cursor.fetchone():
            return {"success": False, "message": "Task not found."}

        previous_row = get_task_by_id(cursor, task_id)
        previous_recipients = get_task_recipients(cursor, task_id)

        raw_text, merchant_name, zip_code = parse_merchant_fields(data.merchant_raw_text)
        if not raw_text or not merchant_name:
            return {"success": False, "message": "Merchant name is required."}

        status = normalize_status(data.status)
        if status not in ALLOWED_STATUSES:
            return {"success": False, "message": "Status is invalid."}

        tracking_number = normalize_tracking_number(getattr(data, "tracking_number", ""))
        if status == "SHIP OUT" and not tracking_number:
            return {"success": False, "message": "Tracking number is required for SHIP OUT."}

        note_text = normalize_text(data.note)
        if status == "DONE" and not note_text:
            return {"success": False, "message": "Note is required when status is DONE."}

        deadline_date, deadline_time, deadline_error = parse_deadline_parts(
            data.deadline_date,
            data.deadline_time,
            data.deadline_period,
        )
        if deadline_error:
            return {"success": False, "message": deadline_error}

        actor_display_name = get_user_display_name(cursor, action_by_username) or action_by_username
        handoff_selection = normalize_handoff_targets(cursor, data)
        handoff_to_type = handoff_selection["type"] or "TEAM"
        handoff_to_username = handoff_selection["summary_username"]
        handoff_to_display_name = handoff_selection["summary_display_name"] or "Tech Team"
        handoff_recipients = handoff_selection["recipients"]

        if handoff_to_type != "TEAM" and not handoff_recipients:
            return {"success": False, "message": "Handoff target is required."}

        training_form_json = serialize_training_form_json(getattr(data, "training_form", []))
        training_completed_tabs_json = serialize_training_form_json(getattr(data, "training_completed_tabs", []))
        previous_training_started_at = getattr(previous_row, "TrainingStartedAt", None) if previous_row else None
        previous_training_started_by_username = (
            normalize_username(getattr(previous_row, "TrainingStartedByUsername", "")) if previous_row else ""
        )
        previous_training_started_by_display_name = (
            normalize_text(getattr(previous_row, "TrainingStartedByDisplayName", "")) if previous_row else ""
        )
        training_started_at = previous_training_started_at
        if normalize_text(getattr(data, "training_started_at", "")):
            training_started_at = previous_training_started_at or datetime.now()
        elif training_form_json and not training_started_at:
            training_started_at = datetime.now()

        training_started_by_username = normalize_username(getattr(data, "training_started_by_username", ""))
        if not training_started_by_username and training_form_json:
            training_started_by_username = previous_training_started_by_username or action_by_username

        training_started_by_display_name = normalize_text(getattr(data, "training_started_by_display_name", ""))
        if not training_started_by_display_name and training_form_json:
            training_started_by_display_name = previous_training_started_by_display_name or actor_display_name

        cursor.execute(
            """
            UPDATE dbo.TaskFollow
            SET MerchantRawText = ?,
                MerchantName = ?,
                ZipCode = ?,
                Phone = ?,
                TrackingNumber = ?,
                ProblemSummary = ?,
                HandoffFromUsername = ?,
                HandoffFromDisplayName = ?,
                HandoffToType = ?,
                HandoffToUsername = ?,
                HandoffToDisplayName = ?,
                Status = ?,
                DeadlineDate = ?,
                DeadlineTime = ?,
                CurrentNote = ?,
                LastUpdatedByUsername = ?,
                LastUpdatedByDisplayName = ?,
                TrainingFormJson = ?,
                TrainingStartedAt = ?,
                TrainingStartedByUsername = ?,
                TrainingStartedByDisplayName = ?,
                TrainingCompletedTabsJson = ?,
                UpdatedAt = GETDATE()
            WHERE TaskID = ?
            """,
            (
                raw_text,
                merchant_name,
                zip_code,
                normalize_text(data.phone),
                tracking_number,
                normalize_text(data.problem_summary),
                action_by_username,
                actor_display_name,
                handoff_to_type,
                handoff_to_username,
                handoff_to_display_name,
                status,
                deadline_date,
                deadline_time,
                "",
                action_by_username,
                actor_display_name,
                training_form_json or None,
                training_started_at,
                training_started_by_username,
                training_started_by_display_name,
                training_completed_tabs_json or None,
                task_id,
            ),
        )

        replace_task_recipients(cursor, task_id, handoff_recipients or [{"type": "TEAM", "username": "", "display_name": "Tech Team"}])

        log_payload = {
            "action_by_username": action_by_username,
            "note": note_text,
            "status": status,
            "handoff_from_username": action_by_username,
            "handoff_from_display_name": actor_display_name,
            "handoff_to_type": handoff_to_type,
            "handoff_to_username": handoff_to_username,
            "handoff_to_display_name": handoff_to_display_name,
        }
        previous_signature = serialize_recipient_signature(
            previous_recipients
            or [
                {
                    "type": normalize_text(previous_row.HandoffToType).upper() or "TEAM",
                    "username": normalize_username(previous_row.HandoffToUsername),
                    "display_name": normalize_text(previous_row.HandoffToDisplayName),
                }
            ]
        )
        new_signature = serialize_recipient_signature(
            handoff_recipients or [{"type": "TEAM", "username": "", "display_name": "Tech Team"}]
        )
        recipient_changed = new_signature != previous_signature
        previous_status = normalize_status(previous_row.Status) if previous_row else ""
        status_changed = previous_status != status
        notification_relevant = is_notification_refresh_relevant(
            status_changed=status_changed,
            recipient_changed=recipient_changed,
        )

        if note_text:
            insert_task_log(cursor, task_id, "UPDATE", log_payload, actor_display_name)
        if recipient_changed:
            insert_assignment_log(cursor, task_id, log_payload, actor_display_name)

        conn.commit()
        updated_row = get_task_by_id(cursor, task_id)
        updated_history = get_task_logs(cursor, task_id)
        updated_recipients = get_task_recipients(cursor, task_id)
        is_visible_on_board = bool(
            updated_row and is_task_in_board_scope(updated_row.Status, updated_row.DeadlineDate)
        )
        return {
            "success": True,
            "task_id": task_id,
            "data": build_task_response(updated_row, updated_history, updated_recipients) if updated_row else None,
            "visible_on_board": is_visible_on_board,
            "notification_relevant": notification_relevant,
            "recipient_changed": recipient_changed,
            "status_changed": status_changed,
            "message": (
                "Task updated successfully."
                if is_visible_on_board
                else "Task updated successfully, but it is outside the current board filter."
            ),
        }

    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.delete("/task-follows/{task_id}")
def delete_task_follow(task_id: int, action_by: str = ""):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ensure_task_follow_training_columns(cursor)
        ensure_task_follow_notification_read_table(cursor)
        ensure_task_follow_notification_dismiss_table(cursor)
        ensure_task_follow_recipient_table(cursor)

        action_by_username = normalize_username(action_by)
        if not action_by_username:
            return {"success": False, "message": "Missing action_by."}

        cursor.execute("SELECT Username FROM dbo.Users WHERE Username = ?", (action_by_username,))
        if not cursor.fetchone():
            return {"success": False, "message": "User not found."}

        existing_row = get_task_by_id(cursor, task_id)
        if not existing_row:
            return {"success": False, "message": "Task not found."}

        notification_relevant = normalize_status(existing_row.Status) != "DONE"

        cursor.execute("DELETE FROM dbo.TaskFollowNotificationRead WHERE TaskID = ?", (task_id,))
        cursor.execute("DELETE FROM dbo.TaskFollowNotificationDismiss WHERE TaskID = ?", (task_id,))
        cursor.execute("DELETE FROM dbo.TaskFollowRecipient WHERE TaskID = ?", (task_id,))
        cursor.execute("DELETE FROM dbo.TaskFollowLog WHERE TaskID = ?", (task_id,))
        cursor.execute("DELETE FROM dbo.TaskFollow WHERE TaskID = ?", (task_id,))

        conn.commit()
        return {
            "success": True,
            "task_id": task_id,
            "notification_relevant": notification_relevant,
            "message": "Task deleted successfully.",
        }

    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()
