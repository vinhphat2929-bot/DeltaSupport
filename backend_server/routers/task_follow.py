from datetime import datetime, timedelta

from fastapi import APIRouter

from database import get_connection
from models import TaskFollowUpsertRequest

router = APIRouter()

ALLOWED_STATUSES = {
    "FOLLOW",
    "FOLLOW REQUEST",
    "CHECK TRACKING NUMBER",
    "SET UP & TRAINING",
    "MISS TIP / CHARGE BACK",
    "DONE",
    "DEMO",
}


def normalize_text(value):
    return str(value or "").strip()


def normalize_username(value):
    return normalize_text(value)


def normalize_status(value):
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


def build_task_response(row, history_items=None):
    deadline_date_text, deadline_time_text, deadline_period, deadline_full = serialize_deadline(
        row.DeadlineDate,
        row.DeadlineTime,
    )

    return {
        "task_id": row.TaskID,
        "task_date": row.TaskDate.strftime("%d-%m-%Y") if row.TaskDate else "",
        "merchant_raw": normalize_text(row.MerchantRawText),
        "merchant_name": normalize_text(row.MerchantName),
        "zip_code": normalize_text(row.ZipCode),
        "phone": normalize_text(row.Phone),
        "problem": normalize_text(row.ProblemSummary),
        "handoff_from_username": normalize_text(row.HandoffFromUsername),
        "handoff_from": normalize_text(row.HandoffFromDisplayName),
        "handoff_to_type": normalize_text(row.HandoffToType),
        "handoff_to_username": normalize_text(row.HandoffToUsername),
        "handoff_to": normalize_text(row.HandoffToDisplayName),
        "status": normalize_status(row.Status),
        "deadline": deadline_full,
        "deadline_date": deadline_date_text,
        "deadline_time": deadline_time_text,
        "deadline_period": deadline_period,
        "note": normalize_text(row.CurrentNote),
        "updated_at": row.UpdatedAt.strftime("%d-%m-%Y %I:%M %p") if row.UpdatedAt else "",
        "history": history_items or [],
    }


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
            UpdatedAt
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


@router.get("/task-follows/handoff-options")
def get_task_follow_handoff_options(action_by: str):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        action_by = normalize_username(action_by)
        if not action_by:
            return {"success": False, "message": "Missing action_by."}

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
                SELECT Username, DisplayName
                FROM dbo.TechScheduleEmployeeConfig
                WHERE IsActive = 1
                  AND Department = ?
                ORDER BY COALESCE(DisplayName, Username), Username
                """,
                (department,),
            )
            rows = cursor.fetchall()
            for option_row in rows:
                username = normalize_username(option_row[0])
                display_name = normalize_text(option_row[1]) or username
                if not username:
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
                UpdatedAt
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


@router.get("/task-follows/{task_id}")
def get_task_follow_detail(task_id: int, action_by: str = ""):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        row = get_task_by_id(cursor, task_id)
        if not row:
            return {"success": False, "message": "Task not found."}

        history = get_task_logs(cursor, task_id)
        return {"success": True, "data": build_task_response(row, history)}

    except Exception as e:
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
        handoff_to_type = normalize_text(data.handoff_to_type).upper() or "TEAM"
        handoff_to_username = normalize_username(data.handoff_to_username)
        handoff_to_display_name = normalize_text(data.handoff_to_display_name)

        if handoff_to_type == "TEAM":
            handoff_to_username = ""
            handoff_to_display_name = handoff_to_display_name or "Tech Team"
        else:
            if not handoff_to_username:
                return {"success": False, "message": "Handoff target is required."}
            handoff_to_display_name = handoff_to_display_name or get_user_display_name(cursor, handoff_to_username) or handoff_to_username

        task_values = (
            datetime.now().date(),
            raw_text,
            merchant_name,
            zip_code,
            normalize_text(data.phone),
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
                    CreatedAt,
                    UpdatedAt,
                    IsActive
                )
                OUTPUT INSERTED.TaskID
                VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), 1)
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
                        CreatedAt,
                        UpdatedAt,
                        IsActive
                    )
                    VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), 1)
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
                            CreatedAt,
                            UpdatedAt,
                            IsActive
                        )
                        OUTPUT INSERTED.TaskID
                        VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), 1)
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
        insert_task_log(cursor, task_id, "CREATE", log_payload, actor_display_name)

        conn.commit()
        created_row = get_task_by_id(cursor, task_id)
        is_visible_on_board = bool(
            created_row and is_task_in_board_scope(created_row.Status, created_row.DeadlineDate)
        )
        return {
            "success": True,
            "task_id": task_id,
            "visible_on_board": is_visible_on_board,
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

        raw_text, merchant_name, zip_code = parse_merchant_fields(data.merchant_raw_text)
        if not raw_text or not merchant_name:
            return {"success": False, "message": "Merchant name is required."}

        status = normalize_status(data.status)
        if status not in ALLOWED_STATUSES:
            return {"success": False, "message": "Status is invalid."}

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
        handoff_to_type = normalize_text(data.handoff_to_type).upper() or "TEAM"
        handoff_to_username = normalize_username(data.handoff_to_username)
        handoff_to_display_name = normalize_text(data.handoff_to_display_name)

        if handoff_to_type == "TEAM":
            handoff_to_username = ""
            handoff_to_display_name = handoff_to_display_name or "Tech Team"
        else:
            if not handoff_to_username:
                return {"success": False, "message": "Handoff target is required."}
            handoff_to_display_name = handoff_to_display_name or get_user_display_name(cursor, handoff_to_username) or handoff_to_username

        cursor.execute(
            """
            UPDATE dbo.TaskFollow
            SET MerchantRawText = ?,
                MerchantName = ?,
                ZipCode = ?,
                Phone = ?,
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
                UpdatedAt = GETDATE()
            WHERE TaskID = ?
            """,
            (
                raw_text,
                merchant_name,
                zip_code,
                normalize_text(data.phone),
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
                task_id,
            ),
        )

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
        insert_task_log(cursor, task_id, "UPDATE", log_payload, actor_display_name)

        conn.commit()
        updated_row = get_task_by_id(cursor, task_id)
        is_visible_on_board = bool(
            updated_row and is_task_in_board_scope(updated_row.Status, updated_row.DeadlineDate)
        )
        return {
            "success": True,
            "task_id": task_id,
            "visible_on_board": is_visible_on_board,
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
