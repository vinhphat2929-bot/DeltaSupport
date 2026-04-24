import re
from datetime import datetime, timedelta

from fastapi import APIRouter

from database import get_connection
from models import TaskReportUpsertRequest

EARLY_MORNING_SHIFT_CUTOFF_HOUR = 6

try:
    from services.schedule_match_service import (
        get_company_schedule_timezone,
        get_schedule_candidate_dates,
        get_schedule_time_range_text,
        schedule_row_matches_target,
    )
except ModuleNotFoundError:
    try:
        from backend_server.services.schedule_match_service import (
            get_company_schedule_timezone,
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


        def get_company_schedule_timezone():
            return "America/Chicago"


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

router = APIRouter()


def normalize_text(value):
    return str(value or "").strip()


def normalize_username(value):
    return normalize_text(value)


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


def table_exists(cursor, table_name):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = ?
        """,
        (table_name,),
    )
    return cursor.fetchone()[0] > 0


def normalize_phone(value):
    digits = "".join(ch for ch in normalize_text(value) if ch.isdigit())[:10]
    if len(digits) != 10:
        return normalize_text(value)
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:10]}"


def parse_report_date(value):
    text = normalize_text(value)
    if not text:
        return None, "Report date is required."

    for pattern in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, pattern).date(), None
        except ValueError:
            continue
    return None, "Report date must be DD-MM-YYYY."


def parse_report_time(value):
    text = normalize_text(value)
    if not text:
        return None, "Report time is required."

    for pattern in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, pattern).time().replace(microsecond=0), None
        except ValueError:
            continue
    return None, "Report time must be HH:MM or HH:MM:SS."


def get_user_display_name(cursor, username):
    username = normalize_username(username)
    if not username:
        return ""

    if table_exists(cursor, "TechScheduleEmployeeConfig"):
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


def resolve_technician(cursor, username, display_name):
    username_text = normalize_username(username)
    display_text = normalize_text(display_name)

    if username_text:
        resolved_display_name = get_user_display_name(cursor, username_text) or display_text or username_text
        return username_text, resolved_display_name

    return "", display_text


def ensure_task_report_table(cursor):
    cursor.execute(
        """
        IF OBJECT_ID('dbo.TaskReport', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.TaskReport (
                ReportID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                ReportDate DATE NOT NULL,
                ReportTime TIME(0) NOT NULL,
                MerchantName NVARCHAR(255) NOT NULL,
                CallerPhone NVARCHAR(20) NOT NULL,
                ProblemSummary NVARCHAR(MAX) NOT NULL,
                SolutionSummary NVARCHAR(MAX) NOT NULL,
                ProcessingStatus NVARCHAR(100) NOT NULL,
                TechnicianUsername NVARCHAR(100) NULL,
                TechnicianDisplayName NVARCHAR(255) NOT NULL,
                CreatedByUsername NVARCHAR(100) NOT NULL,
                CreatedByDisplayName NVARCHAR(255) NULL,
                UpdatedByUsername NVARCHAR(100) NULL,
                UpdatedByDisplayName NVARCHAR(255) NULL,
                CreatedAt DATETIME NOT NULL DEFAULT GETDATE(),
                UpdatedAt DATETIME NOT NULL DEFAULT GETDATE(),
                IsActive BIT NOT NULL DEFAULT 1
            )
        END
        """
    )
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1
            FROM sys.indexes
            WHERE name = 'IX_TaskReport_ReportDate'
              AND object_id = OBJECT_ID('dbo.TaskReport')
        )
        BEGIN
            CREATE INDEX IX_TaskReport_ReportDate
            ON dbo.TaskReport(ReportDate DESC, ReportTime DESC, UpdatedAt DESC)
        END
        """
    )
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1
            FROM sys.indexes
            WHERE name = 'IX_TaskReport_TechnicianUsername'
              AND object_id = OBJECT_ID('dbo.TaskReport')
        )
        BEGIN
            CREATE INDEX IX_TaskReport_TechnicianUsername
            ON dbo.TaskReport(TechnicianUsername, ReportDate DESC)
        END
        """
    )


def bootstrap_task_report_schema():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ensure_task_report_table(cursor)
        conn.commit()
    finally:
        if conn:
            conn.close()


def task_report_exists(cursor, report_id):
    cursor.execute(
        """
        SELECT ReportID
        FROM dbo.TaskReport
        WHERE ReportID = ? AND IsActive = 1
        """,
        (report_id,),
    )
    return cursor.fetchone() is not None


def serialize_task_report_row(row):
    return {
        "report_id": int(row[0]),
        "report_date": row[1].strftime("%d-%m-%Y") if row[1] else "",
        "report_time": row[2].strftime("%H:%M:%S") if row[2] else "",
        "merchant": normalize_text(row[3]),
        "caller_phone": normalize_phone(row[4]),
        "problem": normalize_text(row[5]),
        "solution": normalize_text(row[6]),
        "processing": normalize_text(row[7]),
        "technician_username": normalize_username(row[8]),
        "technician_display_name": normalize_text(row[9]),
        "created_by_username": normalize_username(row[10]),
        "created_by_display_name": normalize_text(row[11]),
        "updated_by_username": normalize_username(row[12]),
        "updated_by_display_name": normalize_text(row[13]),
        "created_at": row[14].strftime("%d-%m-%Y %H:%M:%S") if row[14] else "",
        "updated_at": row[15].strftime("%d-%m-%Y %H:%M:%S") if row[15] else "",
    }


def get_task_report_by_id(cursor, report_id):
    cursor.execute(
        """
        SELECT
            ReportID,
            ReportDate,
            ReportTime,
            MerchantName,
            CallerPhone,
            ProblemSummary,
            SolutionSummary,
            ProcessingStatus,
            TechnicianUsername,
            TechnicianDisplayName,
            CreatedByUsername,
            CreatedByDisplayName,
            UpdatedByUsername,
            UpdatedByDisplayName,
            CreatedAt,
            UpdatedAt
        FROM dbo.TaskReport
        WHERE ReportID = ? AND IsActive = 1
        """,
        (report_id,),
    )
    row = cursor.fetchone()
    return serialize_task_report_row(row) if row else None


def validate_task_report_payload(cursor, data):
    action_by_username = normalize_username(data.action_by_username)
    if not action_by_username:
        return None, "Missing action_by_username."

    cursor.execute("SELECT Username FROM dbo.Users WHERE Username = ?", (action_by_username,))
    if not cursor.fetchone():
        return None, "User not found."

    report_date, date_error = parse_report_date(data.report_date)
    if date_error:
        return None, date_error

    report_time, time_error = parse_report_time(data.report_time)
    if time_error:
        return None, time_error

    merchant = normalize_text(data.merchant)
    caller_phone = normalize_phone(data.caller_phone)
    problem = normalize_text(data.problem)
    solution = normalize_text(data.solution)
    processing = normalize_text(data.processing)
    technician_username, technician_display_name = resolve_technician(
        cursor,
        data.technician_username,
        data.technician_display_name,
    )
    actor_display_name = get_user_display_name(cursor, action_by_username) or action_by_username

    if not merchant:
        return None, "Merchant is required."
    if len("".join(ch for ch in caller_phone if ch.isdigit())) != 10:
        return None, "Caller phone must be in the format (___) ___-____."
    if not problem:
        return None, "Problem is required."
    if not solution:
        return None, "Solution is required."
    if not processing:
        return None, "Processing is required."
    if not technician_display_name:
        return None, "Technician is required."

    return {
        "action_by_username": action_by_username,
        "actor_display_name": actor_display_name,
        "report_date": report_date,
        "report_time": report_time,
        "merchant": merchant,
        "caller_phone": caller_phone,
        "problem": problem,
        "solution": solution,
        "processing": processing,
        "technician_username": technician_username,
        "technician_display_name": technician_display_name,
    }, ""


@router.get("/task-reports/technicians")
def get_task_report_technicians(action_by: str, work_date: str = "", work_time: str = ""):
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

        work_date_value = None
        if normalize_text(work_date):
            work_date_value, date_error = parse_report_date(work_date)
            if date_error:
                return {"success": False, "message": date_error}

        work_time_value = None
        if normalize_text(work_time):
            work_time_value, time_error = parse_report_time(work_time)
            if time_error:
                return {"success": False, "message": time_error}

        technician_rows = []
        if work_date_value and table_exists(cursor, "TechSchedule"):
            candidate_dates = get_schedule_candidate_dates(work_date_value, work_time_value)
            candidate_date_values = [value.strftime("%Y-%m-%d") for value in candidate_dates]
            date_placeholders = ",".join(["?"] * len(candidate_dates))
            cursor.execute(
                f"""
                SELECT DISTINCT
                    ts.Username,
                    ts.WorkDate,
                    ts.StatusCode,
                    ts.USTimeRange,
                    ts.VNTimeRange,
                    COALESCE(NULLIF(cfg.DisplayName, ''), NULLIF(u.FullName, ''), ts.Username) AS DisplayName
                FROM dbo.TechSchedule ts
                LEFT JOIN dbo.TechScheduleEmployeeConfig cfg ON cfg.Username = ts.Username
                LEFT JOIN dbo.Users u ON u.Username = ts.Username
                WHERE ts.WorkDate IN ({date_placeholders})
                  AND UPPER(COALESCE(cfg.Department, u.Department, '')) = 'TECHNICAL SUPPORT'
                  AND COALESCE(cfg.IsActive, 1) = 1
                ORDER BY COALESCE(NULLIF(cfg.DisplayName, ''), NULLIF(u.FullName, ''), ts.Username), ts.Username, ts.WorkDate
                """,
                tuple(candidate_date_values),
            )
            matched_user_map = {}
            for row in cursor.fetchall():
                username = normalize_username(row[0])
                display_name = normalize_text(row[5]) or username
                if not username:
                    continue
                if not schedule_row_matches_target(
                    row[1],
                    row[2],
                    get_schedule_time_range_text(row[3], row[4]),
                    work_date_value,
                    work_time_value,
                ):
                    continue
                matched_user_map.setdefault(
                    username.lower(),
                    {
                        "username": username,
                        "display_name": display_name,
                    },
                )
            technician_rows = list(matched_user_map.values())

        if not technician_rows:
            if table_exists(cursor, "TechScheduleEmployeeConfig"):
                cursor.execute(
                    """
                    SELECT
                        cfg.Username,
                        COALESCE(NULLIF(cfg.DisplayName, ''), NULLIF(u.FullName, ''), cfg.Username) AS DisplayName,
                        cfg.OffDays,
                        cfg.USTimeRange,
                        cfg.VNTimeRange
                    FROM dbo.TechScheduleEmployeeConfig cfg
                    LEFT JOIN dbo.Users u ON u.Username = cfg.Username
                    WHERE UPPER(COALESCE(cfg.Department, u.Department, '')) = 'TECHNICAL SUPPORT'
                      AND COALESCE(cfg.IsActive, 1) = 1
                    ORDER BY COALESCE(NULLIF(cfg.DisplayName, ''), NULLIF(u.FullName, ''), cfg.Username), cfg.Username
                    """
                )
                technician_rows = []
                for row in cursor.fetchall():
                    username = normalize_username(row[0])
                    display_name = normalize_text(row[1]) or username
                    if not username:
                        continue
                    if work_date_value and not schedule_config_matches_target(
                        row[2],
                        get_schedule_time_range_text(row[3], row[4]),
                        work_date_value,
                        work_time_value,
                    ):
                        continue
                    technician_rows.append(
                        {
                            "username": username,
                            "display_name": display_name,
                        }
                    )
            else:
                cursor.execute(
                    """
                    SELECT
                        Username,
                        COALESCE(NULLIF(FullName, ''), Username) AS DisplayName
                    FROM dbo.Users
                    WHERE UPPER(ISNULL(Department, '')) = 'TECHNICAL SUPPORT'
                    ORDER BY COALESCE(NULLIF(FullName, ''), Username), Username
                    """
                )
                technician_rows = cursor.fetchall()

        data = []
        for row in technician_rows:
            if isinstance(row, dict):
                username = normalize_username(row.get("username"))
                display_name = normalize_text(row.get("display_name")) or username
            else:
                username = normalize_username(row[0])
                display_name = normalize_text(row[1]) or username
            if not username:
                continue
            data.append({"username": username, "display_name": display_name})

        return {
            "success": True,
            "data": data,
            "schedule_timezone": get_company_schedule_timezone(),
        }

    except Exception as e:
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.get("/task-reports")
def get_task_reports(action_by: str, from_date: str = "", to_date: str = "", search: str = ""):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ensure_task_report_table(cursor)

        action_by = normalize_username(action_by)
        if not action_by:
            return {"success": False, "message": "Missing action_by."}

        cursor.execute("SELECT Username FROM dbo.Users WHERE Username = ?", (action_by,))
        if not cursor.fetchone():
            return {"success": False, "message": "User not found."}

        parsed_from_date, from_error = parse_report_date(from_date or datetime.now().strftime("%d-%m-%Y"))
        if from_error:
            return {"success": False, "message": from_error}

        parsed_to_date, to_error = parse_report_date(to_date or from_date or datetime.now().strftime("%d-%m-%Y"))
        if to_error:
            return {"success": False, "message": to_error}

        if parsed_from_date > parsed_to_date:
            return {"success": False, "message": "From date must be before or equal to to date."}

        query = """
            SELECT
                ReportID,
                ReportDate,
                ReportTime,
                MerchantName,
                CallerPhone,
                ProblemSummary,
                SolutionSummary,
                ProcessingStatus,
                TechnicianUsername,
                TechnicianDisplayName,
                CreatedByUsername,
                CreatedByDisplayName,
                UpdatedByUsername,
                UpdatedByDisplayName,
                CreatedAt,
                UpdatedAt
            FROM dbo.TaskReport
            WHERE IsActive = 1
              AND ReportDate >= ?
              AND ReportDate <= ?
        """
        params = [parsed_from_date, parsed_to_date]
        search_text = normalize_text(search)
        if search_text:
            query += """
              AND (
                    MerchantName LIKE ?
                    OR ProblemSummary LIKE ?
                    OR SolutionSummary LIKE ?
                  )
            """
            keyword = f"%{search_text}%"
            params.extend([keyword, keyword, keyword])

        query += """
            ORDER BY
                ReportDate DESC,
                ReportTime DESC,
                UpdatedAt DESC,
                ReportID DESC
        """
        cursor.execute(query, params)
        rows = cursor.fetchall()

        data = [serialize_task_report_row(row) for row in rows]
        return {
            "success": True,
            "data": data,
            "from_date": parsed_from_date.strftime("%d-%m-%Y"),
            "to_date": parsed_to_date.strftime("%d-%m-%Y"),
        }

    except Exception as e:
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.post("/task-reports")
def create_task_report(data: TaskReportUpsertRequest):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ensure_task_report_table(cursor)

        payload, error_message = validate_task_report_payload(cursor, data)
        if error_message:
            return {"success": False, "message": error_message}

        cursor.execute(
            """
            INSERT INTO dbo.TaskReport
            (
                ReportDate,
                ReportTime,
                MerchantName,
                CallerPhone,
                ProblemSummary,
                SolutionSummary,
                ProcessingStatus,
                TechnicianUsername,
                TechnicianDisplayName,
                CreatedByUsername,
                CreatedByDisplayName,
                UpdatedByUsername,
                UpdatedByDisplayName,
                CreatedAt,
                UpdatedAt,
                IsActive
            )
            OUTPUT INSERTED.ReportID
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), 1)
            """,
            (
                payload["report_date"],
                payload["report_time"],
                payload["merchant"],
                payload["caller_phone"],
                payload["problem"],
                payload["solution"],
                payload["processing"],
                payload["technician_username"],
                payload["technician_display_name"],
                payload["action_by_username"],
                payload["actor_display_name"],
                payload["action_by_username"],
                payload["actor_display_name"],
            ),
        )
        row = cursor.fetchone()
        report_id = int(row[0]) if row and row[0] is not None else None
        conn.commit()

        return {
            "success": True,
            "message": "Report saved successfully.",
            "report_id": report_id,
            "data": get_task_report_by_id(cursor, report_id) if report_id else None,
        }

    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.put("/task-reports/{report_id}")
def update_task_report(report_id: int, data: TaskReportUpsertRequest):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ensure_task_report_table(cursor)

        if not task_report_exists(cursor, report_id):
            return {"success": False, "message": "Report not found."}

        payload, error_message = validate_task_report_payload(cursor, data)
        if error_message:
            return {"success": False, "message": error_message}

        cursor.execute(
            """
            UPDATE dbo.TaskReport
            SET ReportDate = ?,
                ReportTime = ?,
                MerchantName = ?,
                CallerPhone = ?,
                ProblemSummary = ?,
                SolutionSummary = ?,
                ProcessingStatus = ?,
                TechnicianUsername = ?,
                TechnicianDisplayName = ?,
                UpdatedByUsername = ?,
                UpdatedByDisplayName = ?,
                UpdatedAt = GETDATE()
            WHERE ReportID = ? AND IsActive = 1
            """,
            (
                payload["report_date"],
                payload["report_time"],
                payload["merchant"],
                payload["caller_phone"],
                payload["problem"],
                payload["solution"],
                payload["processing"],
                payload["technician_username"],
                payload["technician_display_name"],
                payload["action_by_username"],
                payload["actor_display_name"],
                report_id,
            ),
        )
        conn.commit()

        return {
            "success": True,
            "message": "Report updated successfully.",
            "report_id": report_id,
            "data": get_task_report_by_id(cursor, report_id),
        }

    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()


@router.delete("/task-reports/{report_id}")
def delete_task_report(report_id: int, action_by: str = ""):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ensure_task_report_table(cursor)

        action_by = normalize_username(action_by)
        if not action_by:
            return {"success": False, "message": "Missing action_by."}

        cursor.execute("SELECT Username FROM dbo.Users WHERE Username = ?", (action_by,))
        if not cursor.fetchone():
            return {"success": False, "message": "User not found."}

        if not task_report_exists(cursor, report_id):
            return {"success": False, "message": "Report not found."}

        cursor.execute(
            """
            UPDATE dbo.TaskReport
            SET IsActive = 0,
                UpdatedByUsername = ?,
                UpdatedByDisplayName = ?,
                UpdatedAt = GETDATE()
            WHERE ReportID = ? AND IsActive = 1
            """,
            (
                action_by,
                get_user_display_name(cursor, action_by) or action_by,
                report_id,
            ),
        )
        conn.commit()

        return {
            "success": True,
            "report_id": report_id,
            "message": "Report deleted successfully.",
        }

    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()
