from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from models import PrayerTimes, Session, Task
from states.base_state import BaseState


class BaseScreenState(BaseState):
    name = "base_state"

    def __init__(self, session: Session, tasks: List[Task], prayer_times: Dict[str, PrayerTimes]):
        self.session = session
        self.tasks = tasks
        self.prayer_times = prayer_times

    def _times(self) -> dict[str, Any]:
        now = datetime.now()
        date_key = now.strftime("%Y-%m-%d")
        data = self.prayer_times.get(date_key) or self.prayer_times[sorted(self.prayer_times.keys())[0]]
        suhoor = datetime.strptime(f"{date_key} {data.fajr}", "%Y-%m-%d %H:%M")
        iftar = datetime.strptime(f"{date_key} {data.maghrib}", "%Y-%m-%d %H:%M")

        if now >= iftar:
            target = suhoor + timedelta(days=1)
            next_name = "сухура"
            phase = "night"
            start = iftar
            end = suhoor + timedelta(days=1)
        elif now >= suhoor:
            target = iftar
            next_name = "ифтара"
            phase = "day"
            start = suhoor
            end = iftar
        else:
            target = suhoor
            next_name = "сухура"
            phase = "night"
            start = iftar - timedelta(days=1)
            end = suhoor

        delta = max(0, int((target - now).total_seconds()))
        total = max(1, int((end - start).total_seconds()))
        progress = min(1.0, max(0.0, (now - start).total_seconds() / total))
        day_fraction = (now.hour * 3600 + now.minute * 60 + now.second) / 86400
        return {
            "next": next_name,
            "countdown": f"{delta // 3600:02d}:{(delta % 3600) // 60:02d}:{delta % 60:02d}",
            "phase": phase,
            "phase_progress": progress,
            "day_fraction": day_fraction,
            "suhoor": data.fajr,
            "iftar": data.maghrib,
        }

    def show(self) -> dict[str, Any]:
        times = self._times()
        return {
            "view": self.name,
            "day": self.session.current_day,
            "month_progress": ((self.session.current_day - 1) + times["day_fraction"]) / 30,
            "today_task": self.tasks[self.session.current_day - 1].text,
            "next_prayer": times,
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "open_task_info":
            self.session.selected_day = self.session.current_day
            return "task_info_state"
        if command == "open_tasks_map":
            self.session.selected_day = self.session.current_day
            return "tasks_map_state"
        if command == "open_day_review":
            return "day_review_state"
        if command == "open_eid":
            return "eid_state"
        return None
