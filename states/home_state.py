from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from models import PrayerTimes, Session, Task
from states.base_state import BaseState


class HomeState(BaseState):
    name = "base"

    def __init__(self, session: Session, tasks: List[Task], prayer_times: Dict[str, PrayerTimes]):
        self.session = session
        self.tasks = tasks
        self.prayer_times = prayer_times

    def _next_prayer(self) -> dict[str, str]:
        now = datetime.now()
        date_key = now.strftime("%Y-%m-%d")
        times = self.prayer_times.get(date_key)
        if times is None:
            first_key = sorted(self.prayer_times.keys())[0]
            times = self.prayer_times[first_key]
            date_key = first_key

        suhoor = datetime.strptime(f"{date_key} {times.fajr}", "%Y-%m-%d %H:%M")
        iftar = datetime.strptime(f"{date_key} {times.maghrib}", "%Y-%m-%d %H:%M")

        next_name = "сухура"
        next_time = suhoor
        if now >= suhoor and now <= iftar:
            next_name = "ифтара"
            next_time = iftar
        elif now > iftar:
            next_name = "сухура"
            next_time = suhoor + timedelta(days=1)

        delta = next_time - now
        hours, rem = divmod(max(0, int(delta.total_seconds())), 3600)
        minutes = rem // 60
        return {"next": next_name, "countdown": f"{hours:02d}:{minutes:02d}", "suhoor": times.fajr, "iftar": times.maghrib}

    def show(self) -> dict[str, Any]:
        task = self.tasks[self.session.current_day - 1]
        next_prayer = self._next_prayer()
        return {
            "view": self.name,
            "current_day": self.session.current_day,
            "next_prayer": next_prayer,
            "today_task": task.text,
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "open_map":
            self.session.selected_day = self.session.current_day
            return "task_map"
        if command == "open_task":
            return "task"
        if command == "open_review":
            return "day_review"
        return None
