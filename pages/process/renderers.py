import tkinter as tk
import customtkinter as ctk
from datetime import datetime, timedelta

class ProcessRenderer:
    def __init__(self, page):
        self.page = page

    def draw_round_rect(self, canvas, x1, y1, x2, y2, radius, fill, outline="", width=1):
        points = [
            x1 + radius, y1,
            x1 + radius, y1,
            x2 - radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, fill=fill, outline=outline, width=width)

    def redraw_follow_canvas(self, canvas, header_canvas, tasks, active_task, is_training, status_meta, 
                             text_dark, text_muted, canvas_header, canvas_row, canvas_row_alt, 
                             canvas_overdue, canvas_overdue_text, canvas_today, canvas_today_text, 
                             canvas_tomorrow, canvas_tomorrow_text, canvas_day_after, canvas_day_after_text):
        canvas.delete("all")
        header_canvas.delete("all")
        hits = []
        row_height = 44
        row_gap = 6
        content_padding = 46
        header_height = 62
        scrollbar_height = 18

        canvas_width = max(canvas.winfo_width(), 640)
        if is_training:
            header_ratios = [("Merchant", 0.48), ("Next", 0.24), ("Training", 0.28)]
            min_widths = {"Merchant": 130, "Next": 90, "Training": 120}
        else:
            header_ratios = [
                ("Merchant", 0.25), ("Phone", 0.13), ("Problem", 0.22),
                ("Handoff To", 0.12), ("Deadline", 0.14), ("Status", 0.14)
            ]
            min_widths = {"Merchant": 155, "Phone": 105, "Problem": 145, "Handoff To": 100, "Deadline": 120, "Status": 145}
        
        x = 14
        y = 4
        right_padding = 18
        target_width = max(sum(min_widths.values()), canvas_width - (x * 2) - right_padding)
        resolved_headers = []
        used_width = 0
        for name, ratio in header_ratios:
            w = max(min_widths[name], int(target_width * ratio))
            resolved_headers.append((name, w))
            used_width += w

        header_x = x
        for name, w in resolved_headers:
            header_canvas.create_text(header_x + (w / 2), header_height / 2, text=name, fill=canvas_header, font=("Segoe UI", 11, "bold"))
            header_x += w

        active_task_id = active_task.get("task_id") if active_task else None
        y = 0
        for idx, item in enumerate(tasks):
            item_id = item.get("task_id")
            is_active = item_id == active_task_id
            bg_color = canvas_row if idx % 2 == 0 else canvas_row_alt
            text_color = text_dark
            meta = status_meta.get(str(item.get("status", "")).strip().upper(), {"bg": "#9ca3af", "text": "#ffffff"})

            deadline_date_text = str(item.get("deadline_date", "")).strip()
            if deadline_date_text and not is_active:
                try:
                    deadline_date = datetime.strptime(deadline_date_text, "%d-%m-%Y").date()
                    today = datetime.now().date()
                    if item.get("status") != "DONE":
                        if deadline_date < today:
                            bg_color = canvas_overdue
                            text_color = canvas_overdue_text
                        elif deadline_date == today:
                            bg_color = canvas_today
                            text_color = canvas_today_text
                        elif deadline_date == today + timedelta(days=1):
                            bg_color = canvas_tomorrow
                            text_color = canvas_tomorrow_text
                        elif deadline_date == today + timedelta(days=2):
                            bg_color = canvas_day_after
                            text_color = canvas_day_after_text
                except ValueError: pass

            border_color = "#3b82f6" if is_active else "#e5e7eb"
            border_w = 2 if is_active else 1
            self.draw_round_rect(canvas, x, y, x + used_width, y + row_height, 10, bg_color, border_color, width=border_w)
            hits.append((x, y, x + used_width, y + row_height, item_id))

            row_x = x
            if is_training:
                merchant_label = str(item.get("merchant_name", "")).strip() or str(item.get("merchant_raw", "")).strip()
                zip_code = str(item.get("zip_code", "")).strip()
                if zip_code: merchant_label = f"{merchant_label}  {zip_code}"
                canvas.create_text(row_x + 16, y + (row_height / 2), text=merchant_label, fill=text_color, font=("Segoe UI", 11, "bold"), anchor="w")
                row_x += resolved_headers[0][1]
                deadline_text = str(item.get("deadline", "")).strip()
                canvas.create_text(row_x + 16, y + (row_height / 2), text=deadline_text, fill=text_color, font=("Segoe UI", 10), anchor="w")
                row_x += resolved_headers[1][1]
                is_second = str(item.get("status", "")).strip().upper() == "2ND TRAINING"
                stage_text = "2nd Training" if is_second else "1st Setup & Training"
                stage_color = "#0ea5a3" if is_second else "#9333ea"
                self.draw_round_rect(canvas, row_x + 12, y + 10, row_x + 152, y + row_height - 10, 8, stage_color, stage_color)
                canvas.create_text(row_x + 82, y + (row_height / 2), text=stage_text, fill="#ffffff", font=("Segoe UI", 10, "bold"))
            else:
                for h_idx, (h_name, h_w) in enumerate(resolved_headers):
                    val = ""
                    if h_name == "Merchant":
                        val = str(item.get("merchant_name", "")).strip() or str(item.get("merchant_raw", "")).strip()
                        zip_code = str(item.get("zip_code", "")).strip()
                        if zip_code: val = f"{val}  {zip_code}"
                    elif h_name == "Phone": val = str(item.get("phone", "")).strip()
                    elif h_name == "Problem": val = str(item.get("problem", "")).strip()
                    elif h_name == "Handoff To": val = str(item.get("handoff_to", "")).strip()
                    elif h_name == "Deadline": val = str(item.get("deadline", "")).strip()
                    elif h_name == "Status":
                        self.draw_round_rect(canvas, row_x + 12, y + 10, row_x + h_w - 12, y + row_height - 10, 8, meta["bg"], meta["bg"])
                        canvas.create_text(row_x + (h_w / 2), y + (row_height / 2), text=val or str(item.get("status", "")).strip(), fill=meta["text"], font=("Segoe UI", 10, "bold"))
                        val = ""
                    if val:
                        canvas.create_text(row_x + 16, y + (row_height / 2), text=val, fill=text_color, font=("Segoe UI", 11, "bold" if h_name == "Merchant" else "normal"), anchor="w", width=h_w - 24)
                    row_x += h_w
            y += row_height + row_gap

        canvas.configure(scrollregion=(0, 0, x + used_width + right_padding, y + content_padding))
        header_canvas.configure(scrollregion=(0, 0, x + used_width + right_padding, header_height))
        return y + content_padding, hits

    def estimate_training_row_height(self, row):
        kind = row.get("kind")
        if kind == "banner":
            subtitle = str(row.get("subtitle", "")).strip()
            return 42 + (22 * max(0, subtitle.count("\n") + (1 if subtitle else 0)))
        if kind == "columns": return 30
        if kind == "group": return 34
        label = str(row.get("label", "")).strip()
        line_count = max(1, label.count("\n") + 1)
        return max(34, 12 + (line_count * 18))

    def redraw_training_canvas(self, canvas, flat_rows, training_note_entries, training_note_values, canvas_width, banner_bg, subheader_bg, group_bg):
        if canvas is None: return 0, []
        for row_key, note_entry in list(training_note_entries.items()):
            try: training_note_values[row_key] = note_entry.get().strip()
            except Exception: pass
        canvas.delete("all")
        layout = []
        x, y = 0, 0
        step_w, result_w = 44, 92
        note_w = max(210, int(canvas_width * 0.33))
        list_w = max(280, canvas_width - step_w - result_w - note_w - 4)
        col_positions = {"step": x, "list": x + step_w, "result": x + step_w + list_w, "note": x + step_w + list_w + result_w, "right": x + step_w + list_w + result_w + note_w}

        for row in flat_rows:
            height = self.estimate_training_row_height(row)
            row_data = row.copy()
            row_data["height"], row_data["y"] = height, y
            layout.append(row_data)
            kind = row.get("kind")
            if kind == "banner":
                canvas.create_rectangle(col_positions["step"], y, col_positions["right"], y + height, fill=banner_bg, outline="#000000")
                canvas.create_text((col_positions["step"] + col_positions["right"]) / 2, y + 14, text=row.get("title", ""), fill="#1d1d1d", font=("Segoe UI", 13, "bold"), anchor="n")
                subtitle = str(row.get("subtitle", "")).strip()
                if subtitle:
                    canvas.create_text((col_positions["step"] + col_positions["right"]) / 2, y + 34, text=subtitle, fill="#b91c1c" if row.get("section_key") != "second_training" else "#1d1d1d", font=("Segoe UI", 10, "bold"), anchor="n", justify="center", width=col_positions["right"] - 24)
            elif kind == "columns":
                for start_x, end_x, text in [(col_positions["step"], col_positions["list"], "STEP"), (col_positions["list"], col_positions["result"], "LIST"), (col_positions["result"], col_positions["note"], "Result"), (col_positions["note"], col_positions["right"], "NOTE")]:
                    canvas.create_rectangle(start_x, y, end_x, y + height, fill=subheader_bg, outline="#000000")
                    canvas.create_text((start_x + end_x) / 2, y + (height / 2), text=text, fill="#1d1d1d", font=("Segoe UI", 10, "bold"))
            elif kind == "group":
                canvas.create_rectangle(col_positions["step"], y, col_positions["right"], y + height, fill=group_bg, outline="#000000")
                canvas.create_text((col_positions["step"] + col_positions["right"]) / 2, y + (height / 2), text=row.get("label", ""), fill="#1d1d1d", font=("Segoe UI", 11, "bold"))
            else:
                for start_x, end_x in [(col_positions["step"], col_positions["list"]), (col_positions["list"], col_positions["result"]), (col_positions["result"], col_positions["note"]), (col_positions["note"], col_positions["right"])]:
                    canvas.create_rectangle(start_x, y, end_x, y + height, fill="#ffffff", outline="#000000")
                canvas.create_text((col_positions["step"] + col_positions["list"]) / 2, y + 8, text=row.get("step", ""), fill="#1d1d1d", font=("Segoe UI", 10, "bold"), anchor="n")
                canvas.create_text(col_positions["list"] + 8, y + 6, text=row.get("label", ""), fill="#1d1d1d", font=("Segoe UI", 10), anchor="nw", justify="left", width=list_w - 16)

                # Vẽ nút DONE/X toggle trong ô result
                result_val = str(row.get("result", "")).strip().upper()
                btn_x1 = col_positions["result"] + 8
                btn_y1 = y + (height / 2) - 13
                btn_x2 = col_positions["note"] - 8
                btn_y2 = y + (height / 2) + 13
                if result_val == "DONE":
                    btn_fill, btn_text_color, btn_label = "#ef4444", "#ffffff", "DONE"
                elif result_val == "X":
                    btn_fill, btn_text_color, btn_label = "#f59e0b", "#ffffff", "X"
                else:
                    btn_fill, btn_text_color, btn_label = "#f3ede4", "#8d7867", "—"
                self.draw_round_rect(canvas, btn_x1, btn_y1, btn_x2, btn_y2, 6, btn_fill, btn_fill)
                canvas.create_text((btn_x1 + btn_x2) / 2, (btn_y1 + btn_y2) / 2, text=btn_label, fill=btn_text_color, font=("Segoe UI", 10, "bold"))
                row_data["result_hit"] = (btn_x1, btn_y1, btn_x2, btn_y2)

            y += height
        canvas.configure(scrollregion=(0, 0, col_positions["right"], y + 4))
        return y + 4, layout