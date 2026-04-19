from datetime import datetime
import re

class ProcessService:
    def __init__(self, store, current_user_info):
        """
        :param store: TaskStore instance
        :param current_user_info: dict with username, full_name, etc.
        """
        self.store = store
        self.user_info = current_user_info
        self.username = str(current_user_info.get("username", "")).strip()
        self.display_name = str(current_user_info.get("full_name", "")).strip() or self.username

    def load_bootstrap(self, show_all=False, include_done=False):
        self.store.set_view(show_all=show_all, include_done=include_done)
        self.store.load_handoff_options(self.username, task_date="")
        self.refresh_tasks(show_all=show_all, include_done=include_done)

    def refresh_tasks(self, search_text="", show_all=False, include_done=False, force=False):
        if not self.username:
            return
        
        self.store.set_view(show_all=show_all, include_done=include_done)
        self.store.load(self.username, force=force, background_if_stale=True)

    def load_task_detail(self, task_id):
        if not task_id:
            return
        self.store.ensure_detail(task_id, action_by=self.username)

    def get_handoff_option_by_name(self, display_name, options):
        target = str(display_name or "").strip()
        for option in options:
            if str(option.get("display_name", "")).strip() == target:
                return option
        return None

    def build_follow_payload(self, form_data):
        """
        Refactored payload collection logic from collect_follow_form_payload
        :param form_data: dict containing raw input values from UI
        """
        merchant_raw_text = form_data.get("merchant_name", "").strip()
        status = form_data.get("status")
        note = form_data.get("note", "").strip()
        deadline_date = form_data.get("deadline_date")
        deadline_time = form_data.get("deadline_time")
        deadline_period = form_data.get("deadline_period")
        selected_handoff_names = form_data.get("handoff_targets", [])
        handoff_options = form_data.get("handoff_options", [])

        if not merchant_raw_text:
            return None, "Merchant Name khong duoc de trong."
        if not deadline_date:
            return None, "Ngay hen khong duoc de trong."
        if not deadline_time or deadline_period not in {"AM", "PM"}:
            return None, "Hay chon day du ngay gio hen."
        if status == "DONE" and not note:
            return None, "Status DONE bat buoc phai nhap note."

        # Map display names to option objects
        matched_options = []
        for name in selected_handoff_names:
            opt = self.get_handoff_option_by_name(name, handoff_options)
            if opt:
                matched_options.append(opt)
        
        if not matched_options:
            return None, "Hay chon nguoi nhan ban giao."

        # Determine handoff type
        if any(str(opt.get("type", "")).strip().upper() == "TEAM" for opt in matched_options):
            team_opt = next((o for o in matched_options if str(o.get("type", "")).strip().upper() == "TEAM"), {})
            handoff_to_type = "TEAM"
            handoff_to_username = ""
            handoff_to_display_name = str(team_opt.get("display_name", "Tech Team")).strip() or "Tech Team"
            handoff_to_usernames = []
            handoff_to_display_names = [handoff_to_display_name]
        else:
            handoff_to_display_names = [str(o.get("display_name", "")).strip() for o in matched_options if str(o.get("display_name", "")).strip()]
            handoff_to_usernames = [str(o.get("username", "")).strip() for o in matched_options if str(o.get("username", "")).strip()]
            if not handoff_to_usernames:
                return None, "Hay chon nguoi nhan ban giao hop le."
            handoff_to_type = "USER" if len(handoff_to_usernames) == 1 else "USERS"
            handoff_to_username = handoff_to_usernames[0] if len(handoff_to_usernames) == 1 else ""
            handoff_to_display_name = ", ".join(handoff_to_display_names)

        payload = {
            "action_by_username": self.username,
            "merchant_raw_text": merchant_raw_text,
            "phone": form_data.get("phone", "").strip(),
            "problem_summary": form_data.get("problem", "").strip(),
            "handoff_to_type": handoff_to_type,
            "handoff_to_username": handoff_to_username,
            "handoff_to_display_name": handoff_to_display_name,
            "handoff_to_usernames": handoff_to_usernames,
            "handoff_to_display_names": handoff_to_display_names,
            "status": status,
            "deadline_date": deadline_date,
            "deadline_time": deadline_time,
            "deadline_period": deadline_period,
            "note": note,
        }
        return payload, ""

    def build_training_payload(self, active_task, form_data, complete_first=False):
        """
        Refactored payload collection logic from collect_setup_training_payload
        """
        if not active_task or not active_task.get("task_id"):
            return None, "Hay chon task Setup / Training can xu ly."

        selected_handoff_names = form_data.get("handoff_targets", [])
        handoff_options = form_data.get("handoff_options", [])
        
        matched_options = []
        for name in selected_handoff_names:
            opt = self.get_handoff_option_by_name(name, handoff_options)
            if opt:
                matched_options.append(opt)
        
        if not matched_options:
            return None, "Hay chon nguoi nhan ban giao."

        if any(str(o.get("type", "")).strip().upper() == "TEAM" for o in matched_options):
            team_opt = next((o for o in matched_options if str(o.get("type", "")).strip().upper() == "TEAM"), {})
            handoff_to_type = "TEAM"
            handoff_to_username = ""
            handoff_to_display_name = str(team_opt.get("display_name", "Tech Team")).strip() or "Tech Team"
            handoff_to_usernames = []
            handoff_to_display_names = [handoff_to_display_name]
        else:
            handoff_to_display_names = [str(o.get("display_name", "")).strip() for o in matched_options if str(o.get("display_name", "")).strip()]
            handoff_to_usernames = [str(o.get("username", "")).strip() for o in matched_options if str(o.get("username", "")).strip()]
            if not handoff_to_usernames:
                return None, "Hay chon nguoi nhan ban giao hop le."
            handoff_to_type = "USER" if len(handoff_to_usernames) == 1 else "USERS"
            handoff_to_username = handoff_to_usernames[0] if len(handoff_to_usernames) == 1 else ""
            handoff_to_display_name = ", ".join(handoff_to_display_names)

        started_at_text = str(active_task.get("training_started_at", "")).strip()
        started_by_username = str(active_task.get("training_started_by_username", "")).strip() or self.username
        started_by_display_name = str(active_task.get("training_started_by_display_name", "")).strip() or self.display_name
        
        if not started_at_text:
            started_at_text = datetime.now().strftime("%d-%m-%Y %I:%M %p")

        payload = {
            "action_by_username": self.username,
            "merchant_raw_text": active_task.get("merchant_raw", ""),
            "phone": active_task.get("phone", ""),
            "problem_summary": active_task.get("problem", ""),
            "handoff_to_type": handoff_to_type,
            "handoff_to_username": handoff_to_username,
            "handoff_to_display_name": handoff_to_display_name,
            "handoff_to_usernames": handoff_to_usernames,
            "handoff_to_display_names": handoff_to_display_names,
            "status": "2ND TRAINING" if complete_first else active_task.get("status", "SET UP & TRAINING"),
            "deadline_date": active_task.get("deadline_date", ""),
            "deadline_time": active_task.get("deadline_time", ""),
            "deadline_period": active_task.get("deadline_period", "AM"),
            "note": form_data.get("note", "").strip(),
            "training_form": form_data.get("training_form", []),
            "training_started_at": started_at_text,
            "training_started_by_username": started_by_username,
            "training_started_by_display_name": started_by_display_name,
        }
        return payload, ""
