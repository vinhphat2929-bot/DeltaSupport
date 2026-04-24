import re
from datetime import datetime, timedelta
import threading

import json

from fastapi import APIRouter

from database import get_connection
from models import (
    TaskFollowNotificationClearRequest,
    TaskFollowNotificationReadRequest,
    TaskFollowUpsertRequest,
)

EARLY_MORNING_SHIFT_CUTOFF_HOUR = 6
try:
    from services.schedule_match_service import (
        convert_target_to_company_schedule_slot,
        get_schedule_candidate_dates,
        get_schedule_time_range_text,
        schedule_row_matches_target,
    )
except ModuleNotFoundError:
    try:
        from backend_server.services.schedule_match_service import (
            convert_target_to_company_schedule_slot,
            get_schedule_candidate_dates,
            get_schedule_time_range_text,
            schedule_row_matches_target,
        )
    except ModuleNotFoundError:
        def normalize_schedule_text(value):
            return str(value or "").strip()


        def coerce_schedule_date(value):
            if hasattr(value, "date") and not isinstance(value, str):
                try:
                    return value.date()
                except TypeError:
                    return value

            text = normalize_schedule_text(value)
            if not text:
                return None

            for pattern in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(text, pattern).date()
                except ValueError:
                    continue
            return None


        def normalize_meridiem_time_text(value):
            text = normalize_schedule_text(value).upper()
            if not text:
                return ""

            text = re.sub(r"(?<=\d)\.(?=\d)", ":", text)
            text = text.replace(".", "")
            text = re.sub(r"\s*:\s*", ":", text)
            text = re.sub(r"\bA\s*M\b", "AM", text)
            text = re.sub(r"\bP\s*M\b", "PM", text)
            text = re.sub(r"(?<=\d)(AM|PM)\b", r" \1", text)
            text = re.sub(r"\s+", " ", text).strip()
            return text


        def parse_schedule_time_value(value):
            normalized_text = normalize_meridiem_time_text(value)
            if not normalized_text:
                return None

            for pattern in ("%I:%M %p", "%I %p", "%H:%M", "%H"):
                try:
                    return datetime.strptime(normalized_text, pattern).time()
                except ValueError:
                    continue
            return None


        def parse_schedule_time_range(range_text):
            text = normalize_schedule_text(range_text)
            if not text or "-" not in text:
                return None, None

            parts = re.split(r"\s*-\s*", text, maxsplit=1)
            if len(parts) != 2:
                return None, None

            start_time = parse_schedule_time_value(parts[0])
            end_time = parse_schedule_time_value(parts[1])
            if start_time is None or end_time is None:
                return None, None
            return start_time, end_time


        def is_previous_workday_morning_shift(start_time, end_time):
            if start_time is None or end_time is None:
                return False

            return (
                start_time < end_time
                and start_time.hour < EARLY_MORNING_SHIFT_CUTOFF_HOUR
                and end_time.hour <= 12
            )


        def get_schedule_candidate_dates(target_date, target_time=None):
            parsed_target_date = coerce_schedule_date(target_date)
            if parsed_target_date is None:
                return []

            candidate_dates = [parsed_target_date]
            if target_time is not None:
                candidate_dates.insert(0, parsed_target_date - timedelta(days=1))
            return candidate_dates


        def get_schedule_time_range_text(us_time_range="", vn_time_range=""):
            return normalize_schedule_text(us_time_range) or normalize_schedule_text(vn_time_range)


        def convert_target_to_company_schedule_slot(target_date, target_time=None, source_timezone=""):
            return coerce_schedule_date(target_date), target_time


        def schedule_row_matches_target(work_date, status_code, time_range_text, target_date, target_time=None):
            if normalize_schedule_text(status_code).upper() != "WORK":
                return False

            work_date_value = coerce_schedule_date(work_date)
            target_date_value = coerce_schedule_date(target_date)
            if work_date_value is None or target_date_value is None:
                return False

            if target_time is None:
                return work_date_value == target_date_value

            start_time, end_time = parse_schedule_time_range(time_range_text)
            if start_time is None or end_time is None:
                return work_date_value == target_date_value

            shift_start = datetime.combine(work_date_value, start_time)
            shift_end = datetime.combine(work_date_value, end_time)
            if shift_end <= shift_start:
                shift_end += timedelta(days=1)
            elif (
                target_date_value == work_date_value + timedelta(days=1)
                and is_previous_workday_morning_shift(start_time, end_time)
            ):
                shift_start += timedelta(days=1)
                shift_end += timedelta(days=1)

            target_moment = datetime.combine(target_date_value, target_time)
            return shift_start <= target_moment <= shift_end

try:
    from services.timezone_service import (
        convert_local_to_utc,
        current_local_date,
        normalize_timezone_name,
        resolve_deadline_timezone,
        serialize_deadline_for_view,
    )
except ModuleNotFoundError:
    from backend_server.services.timezone_service import (
        convert_local_to_utc,
        current_local_date,
        normalize_timezone_name,
        resolve_deadline_timezone,
        serialize_deadline_for_view,
    )

router = APIRouter()
_task_follow_training_columns_lock = threading.Lock()
_task_follow_training_columns_ready = False

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


def schedule_config_matches_target(off_days_text, time_range_text, target_date, target_time=None):
    off_days = [
        part.strip().upper()
        for part in normalize_text(off_days_text).split(",")
        if part.strip()
    ]
    target_day_name = target_date.strftime("%a").upper()[:3]
    previous_date = target_date - timedelta(days=1)
    previous_day_name = previous_date.strftime("%a").upper()[:3]

    if target_time is None:
        return target_day_name not in off_days

    if target_day_name not in off_days and schedule_row_matches_target(
        target_date,
        "WORK",
        time_range_text,
        target_date,
        target_time,
    ):
        return True

    if previous_day_name not in off_days and schedule_row_matches_target(
        previous_date,
        "WORK",
        time_range_text,
        target_date,
        target_time,
    ):
        return True

    return False


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


def ensure_task_follow_training_columns(cursor):
    global _task_follow_training_columns_ready
    if _task_follow_training_columns_ready:
        return False

    with _task_follow_training_columns_lock:
        if _task_follow_training_columns_ready:
            return False

        schema_changed = False

        cursor.execute(
            """
            SELECT
                CASE WHEN COL_LENGTH('dbo.TaskFollow', 'TrainingFormJson') IS NULL THEN 1 ELSE 0 END,
                CASE WHEN COL_LENGTH('dbo.TaskFollow', 'TrainingStartedAt') IS NULL THEN 1 ELSE 0 END,
                CASE WHEN COL_LENGTH('dbo.TaskFollow', 'TrainingStartedByUsername') IS NULL THEN 1 ELSE 0 END,
                CASE WHEN COL_LENGTH('dbo.TaskFollow', 'TrainingStartedByDisplayName') IS NULL THEN 1 ELSE 0 END,
                CASE WHEN COL_LENGTH('dbo.TaskFollow', 'TrainingCompletedTabsJson') IS NULL THEN 1 ELSE 0 END,
                CASE WHEN COL_LENGTH('dbo.TaskFollow', 'TrackingNumber') IS NULL THEN 1 ELSE 0 END,
                CASE WHEN COL_LENGTH('dbo.TaskFollow', 'DeadlineAtUtc') IS NULL THEN 1 ELSE 0 END,
                CASE WHEN COL_LENGTH('dbo.TaskFollow', 'DeadlineTimezone') IS NULL THEN 1 ELSE 0 END
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
        cursor.execute(
            """
            IF COL_LENGTH('dbo.TaskFollow', 'DeadlineAtUtc') IS NULL
            BEGIN
                ALTER TABLE dbo.TaskFollow
                ADD DeadlineAtUtc DATETIME NULL
            END
            """
        )
        cursor.execute(
            """
            IF COL_LENGTH('dbo.TaskFollow', 'DeadlineTimezone') IS NULL
            BEGIN
                ALTER TABLE dbo.TaskFollow
                ADD DeadlineTimezone NVARCHAR(100) NULL
            END
            """
        )
        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1
                FROM sys.indexes
                WHERE name = 'IX_TaskFollow_DeadlineAtUtc'
                  AND object_id = OBJECT_ID('dbo.TaskFollow')
            )
            BEGIN
                CREATE INDEX IX_TaskFollow_DeadlineAtUtc
                ON dbo.TaskFollow(DeadlineAtUtc)
            END
            """
        )

        if schema_changed:
            cursor.connection.commit()

        _task_follow_training_columns_ready = True
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


def serialize_deadline(
    deadline_date,
    deadline_time,
    deadline_at_utc=None,
    deadline_timezone="",
    viewer_timezone="",
    merchant_raw_text="",
    merchant_name="",
    zip_code="",
):
    resolved_timezone, timezone_source = resolve_deadline_timezone(
        explicit_timezone="",
        merchant_raw_text=merchant_raw_text,
        merchant_name=merchant_name,
        zip_code=zip_code,
        existing_timezone=deadline_timezone,
        viewer_timezone=viewer_timezone,
    )
    serialized = serialize_deadline_for_view(
        legacy_deadline_date=deadline_date,
        legacy_deadline_time=deadline_time,
        deadline_at_utc=deadline_at_utc,
        deadline_timezone=resolved_timezone,
        viewer_timezone=viewer_timezone,
    )
    serialized["deadline_timezone_source"] = timezone_source
    return serialized


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


def parse_task_deadline_date_text(value):
    text = normalize_text(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%d-%m-%Y").date()
    except ValueError:
        return None


def parse_task_deadline_datetime_text(deadline_date_text, deadline_time_text, deadline_period_text):
    date_value = parse_task_deadline_date_text(deadline_date_text)
    if date_value is None:
        return None

    time_text = normalize_text(deadline_time_text)
    period_text = normalize_text(deadline_period_text).upper()
    if not time_text or period_text not in {"AM", "PM"}:
        return None

    try:
        parsed_time = datetime.strptime(f"{time_text} {period_text}", "%I:%M %p").time()
    except ValueError:
        return None

    return datetime.combine(date_value, parsed_time)


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


def build_task_response(
    row,
    history_items=None,
    recipient_items=None,
    include_history=True,
    include_training_form=True,
    viewer_timezone="",
):
    deadline_payload = serialize_deadline(
        row.DeadlineDate,
        row.DeadlineTime,
        deadline_at_utc=getattr(row, "DeadlineAtUtc", None),
        deadline_timezone=getattr(row, "DeadlineTimezone", ""),
        viewer_timezone=viewer_timezone,
        merchant_raw_text=getattr(row, "MerchantRawText", ""),
        merchant_name=getattr(row, "MerchantName", ""),
        zip_code=getattr(row, "ZipCode", ""),
    )
    raw_training_form_json = getattr(row, "TrainingFormJson", "")
    has_training_form = bool(getattr(row, "HasTrainingForm", 0)) or bool(normalize_text(raw_training_form_json))
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
        "deadline": deadline_payload["deadline"],
        "deadline_date": deadline_payload["deadline_date"],
        "deadline_time": deadline_payload["deadline_time"],
        "deadline_period": deadline_payload["deadline_period"],
        "deadline_original_label": deadline_payload["deadline_original_label"],
        "deadline_original_date": deadline_payload["deadline_original_date"],
        "deadline_original_time": deadline_payload["deadline_original_time"],
        "deadline_original_period": deadline_payload["deadline_original_period"],
        "deadline_ust_label": deadline_payload["deadline_ust_label"],
        "deadline_ust_date": deadline_payload["deadline_ust_date"],
        "deadline_ust_time": deadline_payload["deadline_ust_time"],
        "deadline_ust_period": deadline_payload["deadline_ust_period"],
        "deadline_vn_label": deadline_payload["deadline_vn_label"],
        "deadline_vn_date": deadline_payload["deadline_vn_date"],
        "deadline_vn_time": deadline_payload["deadline_vn_time"],
        "deadline_vn_period": deadline_payload["deadline_vn_period"],
        "deadline_timezone": deadline_payload["deadline_timezone"],
        "merchant_timezone": deadline_payload["deadline_timezone"],
        "deadline_timezone_source": deadline_payload["deadline_timezone_source"],
        "deadline_viewer_timezone": deadline_payload["deadline_viewer_timezone"],
        "deadline_at_utc": deadline_payload["deadline_at_utc"],
        "note": normalize_text(row.CurrentNote),
        "updated_at": row.UpdatedAt.strftime("%d-%m-%Y %I:%M %p") if row.UpdatedAt else "",
        "training_form": parse_training_form_json(raw_training_form_json) if include_training_form else [],
        "has_training_form": has_training_form,
        "training_started_at": (
            row.TrainingStartedAt.strftime("%d-%m-%Y %I:%M %p")
            if getattr(row, "TrainingStartedAt", None)
            else ""
        ),
        "training_started_by_username": normalize_text(getattr(row, "TrainingStartedByUsername", "")),
        "training_started_by_display_name": normalize_text(getattr(row, "TrainingStartedByDisplayName", "")),
        "training_completed_tabs": parse_training_form_json(getattr(row, "TrainingCompletedTabsJson", "")) or [],
        "history": (history_items or []) if include_history else [],
    }


def format_deadline_label(
    deadline_date,
    deadline_time,
    deadline_at_utc=None,
    deadline_timezone="",
    viewer_timezone="",
    merchant_raw_text="",
    merchant_name="",
    zip_code="",
):
    deadline_payload = serialize_deadline(
        deadline_date,
        deadline_time,
        deadline_at_utc=deadline_at_utc,
        deadline_timezone=deadline_timezone,
        viewer_timezone=viewer_timezone,
        merchant_raw_text=merchant_raw_text,
        merchant_name=merchant_name,
        zip_code=zip_code,
    )
    if deadline_payload["deadline"]:
        return deadline_payload["deadline"]
    return deadline_payload["deadline_date"]


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
            DeadlineAtUtc,
            DeadlineTimezone,
            CurrentNote,
            UpdatedAt,
            TrainingFormJson,
            TrainingStartedAt,
            TrainingStartedByUsername,
            TrainingStartedByDisplayName,
            TrainingCompletedTabsJson
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
def get_task_follow_handoff_options(
    action_by: str,
    task_date: str = "",
    task_time: str = "",
    task_period: str = "",
    deadline_timezone: str = "",
):
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

        def parse_ui_time(time_text: str, period_text: str):
            raw_time = normalize_text(time_text)
            raw_period = normalize_text(period_text).upper()
            if not raw_time or raw_period not in {"AM", "PM"}:
                return None
            try:
                return datetime.strptime(f"{raw_time} {raw_period}", "%I:%M %p").time()
            except ValueError:
                return None

        target_time = parse_ui_time(task_time, task_period)
        schedule_effective_date, schedule_target_time = convert_target_to_company_schedule_slot(
            effective_date,
            target_time,
            deadline_timezone,
        )
        if schedule_effective_date is None:
            schedule_effective_date = effective_date

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
                SELECT Username, DisplayName, OffDays, USTimeRange, VNTimeRange
                FROM dbo.TechScheduleEmployeeConfig
                WHERE IsActive = 1
                  AND Department = ?
                ORDER BY COALESCE(DisplayName, Username), Username
                """,
                (department,),
            )
            rows = cursor.fetchall()

            schedule_rows_by_username = {}
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
                    candidate_dates = get_schedule_candidate_dates(schedule_effective_date, schedule_target_time)
                    candidate_date_values = [value.strftime("%Y-%m-%d") for value in candidate_dates]
                    date_placeholders = ",".join(["?"] * len(candidate_dates))
                    placeholders = ",".join(["?"] * len(usernames))
                    cursor.execute(
                        f"""
                        SELECT Username, WorkDate, StatusCode, USTimeRange, VNTimeRange
                        FROM dbo.TechSchedule
                        WHERE WorkDate IN ({date_placeholders})
                          AND Username IN ({placeholders})
                        """,
                        (*candidate_date_values, *usernames),
                    )
                    for schedule_row in cursor.fetchall():
                        schedule_username = normalize_username(schedule_row[0])
                        if not schedule_username:
                            continue
                        schedule_rows_by_username.setdefault(schedule_username.lower(), []).append(
                            {
                                "work_date": schedule_row[1],
                                "status_code": schedule_row[2],
                                "us_time_range": schedule_row[3],
                                "vn_time_range": schedule_row[4],
                            }
                        )
            for option_row in rows:
                username = normalize_username(option_row[0])
                display_name = normalize_text(option_row[1]) or username
                off_days_text = normalize_text(option_row[2])
                config_us_time_range = normalize_text(option_row[3])
                config_vn_time_range = normalize_text(option_row[4])
                config_time_range = get_schedule_time_range_text(
                    config_us_time_range,
                    config_vn_time_range,
                )
                if not username:
                    continue
                user_schedule_rows = schedule_rows_by_username.get(username.lower(), [])
                if user_schedule_rows:
                    if not any(
                        schedule_row_matches_target(
                            schedule_row.get("work_date"),
                            schedule_row.get("status_code"),
                            get_schedule_time_range_text(
                                schedule_row.get("us_time_range"),
                                schedule_row.get("vn_time_range"),
                            ),
                            schedule_effective_date,
                            schedule_target_time,
                        )
                        for schedule_row in user_schedule_rows
                    ):
                        continue
                else:
                    if not schedule_config_matches_target(
                        off_days_text,
                        config_time_range,
                        schedule_effective_date,
                        schedule_target_time,
                    ):
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
def get_task_follows(
    action_by: str,
    search: str = "",
    show_all: bool = False,
    include_done: bool = False,
    viewer_timezone: str = "",
):
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

        resolved_viewer_timezone = normalize_timezone_name(viewer_timezone) or ""
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
                DeadlineAtUtc,
                DeadlineTimezone,
                CurrentNote,
                UpdatedAt,
                CASE
                    WHEN TrainingFormJson IS NULL OR LTRIM(RTRIM(TrainingFormJson)) = '' THEN 0
                    ELSE 1
                END AS HasTrainingForm,
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

        if search_keyword:
            query += " AND MerchantName LIKE ?"
            params.append(f"%{search_keyword}%")

        query += """
            ORDER BY
                UpdatedAt DESC,
                TaskID DESC
        """

        cursor.execute(query, params)
        rows = cursor.fetchall()

        viewer_today = current_local_date(resolved_viewer_timezone)
        response_rows = []
        for row in rows:
            item = build_task_response(
                row,
                include_history=False,
                include_training_form=False,
                viewer_timezone=resolved_viewer_timezone,
            )
            if board_filter_applied:
                deadline_date_value = parse_task_deadline_date_text(item.get("deadline_date"))
                if not is_task_in_board_scope(item.get("status"), deadline_date_value, viewer_today):
                    continue
            response_rows.append((row, item))

        response_rows.sort(
            key=lambda pair: (
                1 if not normalize_text(pair[1].get("deadline_date")) else 0,
                parse_task_deadline_date_text(pair[1].get("deadline_date")) or datetime.max.date(),
                1 if not normalize_text(pair[1].get("deadline_time")) else 0,
                parse_task_deadline_datetime_text(
                    pair[1].get("deadline_date"),
                    pair[1].get("deadline_time"),
                    pair[1].get("deadline_period"),
                )
                or datetime.max,
                datetime.max - (getattr(pair[0], "UpdatedAt", None) or datetime.min),
            )
        )
        data = [item for _row, item in response_rows]

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
def get_task_follow_notifications(action_by: str, viewer_timezone: str = ""):
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
        resolved_viewer_timezone = normalize_timezone_name(viewer_timezone) or ""

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
                tf.DeadlineAtUtc,
                tf.DeadlineTimezone,
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
            deadline_label = format_deadline_label(
                row.DeadlineDate,
                row.DeadlineTime,
                deadline_at_utc=getattr(row, "DeadlineAtUtc", None),
                deadline_timezone=getattr(row, "DeadlineTimezone", ""),
                viewer_timezone=resolved_viewer_timezone,
                merchant_name=merchant_name,
                zip_code=zip_code,
            )
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
def get_task_follow_detail(task_id: int, action_by: str = "", viewer_timezone: str = ""):
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
        return {
            "success": True,
            "data": build_task_response(
                row,
                history,
                recipients,
                viewer_timezone=normalize_timezone_name(viewer_timezone) or "",
            ),
        }

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

        deadline_timezone, deadline_timezone_source = resolve_deadline_timezone(
            explicit_timezone=getattr(data, "merchant_timezone", ""),
            merchant_raw_text=raw_text,
            merchant_name=merchant_name,
            zip_code=zip_code,
            viewer_timezone=getattr(data, "viewer_timezone", ""),
        )
        if deadline_timezone_source == "invalid":
            return {"success": False, "message": "Merchant timezone is invalid."}

        deadline_at_utc = None
        if deadline_date:
            deadline_at_utc = convert_local_to_utc(
                datetime.combine(deadline_date, deadline_time or datetime.min.time()),
                deadline_timezone,
            )

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
            deadline_at_utc,
            deadline_timezone or None,
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
                    DeadlineAtUtc,
                    DeadlineTimezone,
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
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), 1)
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
                        DeadlineAtUtc,
                        DeadlineTimezone,
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
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), 1)
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
                            DeadlineAtUtc,
                            DeadlineTimezone,
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
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), 1)
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
        resolved_viewer_timezone = normalize_timezone_name(getattr(data, "viewer_timezone", "")) or ""
        created_item = (
            build_task_response(
                created_row,
                created_history,
                created_recipients,
                viewer_timezone=resolved_viewer_timezone,
            )
            if created_row
            else None
        )
        is_visible_on_board = bool(
            created_item
            and is_task_in_board_scope(
                created_item.get("status"),
                parse_task_deadline_date_text(created_item.get("deadline_date")),
                current_local_date(resolved_viewer_timezone),
            )
        )
        return {
            "success": True,
            "task_id": task_id,
            "data": created_item,
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

        deadline_timezone, deadline_timezone_source = resolve_deadline_timezone(
            explicit_timezone=getattr(data, "merchant_timezone", ""),
            merchant_raw_text=raw_text,
            merchant_name=merchant_name,
            zip_code=zip_code,
            existing_timezone=getattr(previous_row, "DeadlineTimezone", "") if previous_row else "",
            viewer_timezone=getattr(data, "viewer_timezone", ""),
        )
        if deadline_timezone_source == "invalid":
            return {"success": False, "message": "Merchant timezone is invalid."}

        deadline_at_utc = None
        if deadline_date:
            deadline_at_utc = convert_local_to_utc(
                datetime.combine(deadline_date, deadline_time or datetime.min.time()),
                deadline_timezone,
            )

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
                DeadlineAtUtc = ?,
                DeadlineTimezone = ?,
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
                deadline_at_utc,
                deadline_timezone or None,
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
        resolved_viewer_timezone = normalize_timezone_name(getattr(data, "viewer_timezone", "")) or ""
        updated_item = (
            build_task_response(
                updated_row,
                updated_history,
                updated_recipients,
                viewer_timezone=resolved_viewer_timezone,
            )
            if updated_row
            else None
        )
        is_visible_on_board = bool(
            updated_item
            and is_task_in_board_scope(
                updated_item.get("status"),
                parse_task_deadline_date_text(updated_item.get("deadline_date")),
                current_local_date(resolved_viewer_timezone),
            )
        )
        return {
            "success": True,
            "task_id": task_id,
            "data": updated_item,
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
