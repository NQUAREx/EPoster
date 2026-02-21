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

    @staticmethod
    def _lerp_color(start: tuple[int, int, int], end: tuple[int, int, int], progress: float) -> str:
        p = min(1.0, max(0.0, progress))
        r = round(start[0] + (end[0] - start[0]) * p)
        g = round(start[1] + (end[1] - start[1]) * p)
        b = round(start[2] + (end[2] - start[2]) * p)
        return f"rgb({r}, {g}, {b})"

    def _phase_palette(self, phase: str, progress: float) -> dict[str, str]:
        # Требуемая схема:
        # day (от сухура до ифтара): красный -> зеленый
        # night (от ифтара до сухура): зеленый -> красный
        red_to_green = {
            "bg": self._lerp_color((43, 10, 10), (10, 43, 18), progress),
            "blob1": self._lerp_color((255, 98, 102), (86, 246, 150), progress),
            "blob2": self._lerp_color((232, 34, 24), (18, 178, 104), progress),
            "blob3": self._lerp_color((255, 164, 110), (116, 232, 140), progress),
        }
        green_to_red = {
            "bg": self._lerp_color((10, 43, 18), (43, 10, 10), progress),
            "blob1": self._lerp_color((86, 246, 150), (255, 98, 102), progress),
            "blob2": self._lerp_color((18, 178, 104), (232, 34, 24), progress),
            "blob3": self._lerp_color((116, 232, 140), (255, 164, 110), progress),
        }
        return green_to_red if phase == "night" else red_to_green

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
        return {
            "next": next_name,
            "countdown": f"{delta // 3600:02d}:{(delta % 3600) // 60:02d}:{delta % 60:02d}",
            "phase": phase,
            "phase_progress": progress,
            "phase_total_seconds": total,
            "suhoor": data.fajr,
            "iftar": data.maghrib,
            "palette": self._phase_palette(phase, progress),
        }

    @staticmethod
    def _ramadan_elapsed_days() -> float:
        now = datetime.now()
        ramadan_start = datetime(now.year, 2, 18, 0, 0, 0)
        elapsed_days = (now - ramadan_start).total_seconds() / 86400
        return min(30.0, max(0.0, elapsed_days))

    def show(self) -> dict[str, Any]:
        times = self._times()
        ramadan_elapsed_days = self._ramadan_elapsed_days()
        base_task_day = self.session.base_task_day()
        return {
            "view": self.name,
            "day": self.session.current_day,
            "ramadan_elapsed_days": ramadan_elapsed_days,
            "ramadan_progress_percent": (ramadan_elapsed_days / 30.0) * 100.0,
            "today_task": self.tasks[base_task_day - 1].text,
            "today_task_type": self.tasks[base_task_day - 1].type,
            "task_day": base_task_day,
            "next_prayer": times,
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "open_task_info":
            self.session.selected_day = self.session.base_task_day()
            return "task_info_state"
        if command == "open_tasks_map":
            return "tasks_map_state"
        if command == "open_day_review":
            review_day = self.session.base_task_day()
            if self.session.days[review_day].closed:
                return None
            self.session.selected_day = review_day
            return "day_review_state"
        if command == "open_eid":
            return "eid_state"
        return None
