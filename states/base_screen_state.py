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
        day_palette = {
            "bg": self._lerp_color((43, 10, 10), (22, 7, 28), progress),
            "blob1": self._lerp_color((255, 94, 98), (255, 146, 70), progress),
            "blob2": self._lerp_color((255, 153, 102), (255, 94, 98), progress),
            "blob3": self._lerp_color((241, 39, 17), (196, 56, 122), progress),
        }
        night_palette = {
            "bg": self._lerp_color((5, 11, 20), (14, 7, 32), progress),
            "blob1": self._lerp_color((0, 198, 255), (84, 130, 255), progress),
            "blob2": self._lerp_color((0, 114, 255), (120, 70, 220), progress),
            "blob3": self._lerp_color((31, 28, 44), (4, 26, 56), progress),
        }
        return night_palette if phase == "night" else day_palette

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
    def _ramadan_progress() -> float:
        now = datetime.now()
        ramadan_start = datetime(now.year, 2, 18, 0, 0, 0)
        ramadan_total_seconds = 30 * 24 * 3600
        elapsed_seconds = (now - ramadan_start).total_seconds()
        return min(1.0, max(0.0, elapsed_seconds / ramadan_total_seconds))

    def show(self) -> dict[str, Any]:
        times = self._times()
        return {
            "view": self.name,
            "day": self.session.current_day,
            "ramadan_progress": self._ramadan_progress(),
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
