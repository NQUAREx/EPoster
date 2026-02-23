from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from models import PrayerTimes, Session, Task
from states.base_state import BaseState


class BaseScreenState(BaseState):
    name = "base_state"

    SLOW_PHASE_REAL_SHARE = 0.9
    SLOW_PHASE_COLOR_SHARE = 0.1

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

    @classmethod
    def _remap_palette_progress(cls, linear_progress: float) -> float:
        """Замедляет смену фона в начале и ускоряет за 2 часа до конца.

        Пример из запроса: при окне в 10 часов
        - первые 9 реальных часов покрывают только 10% цветового перехода;
        - последний 1 реальный час покрывает оставшиеся 90%.
        """
        p = min(1.0, max(0.0, linear_progress))
        split_real = cls.SLOW_PHASE_REAL_SHARE
        split_color = cls.SLOW_PHASE_COLOR_SHARE

        if p <= split_real:
            return (p / split_real) * split_color
        accelerated = (p - split_real) / (1.0 - split_real)
        return split_color + accelerated * (1.0 - split_color)

    def _times(self) -> dict[str, Any]:
        now = datetime.now()
        today = now.date()

        today_times = self._prayer_times_for_date(today)
        yesterday_times = self._prayer_times_for_date(today - timedelta(days=1))
        tomorrow_times = self._prayer_times_for_date(today + timedelta(days=1))

        suhoor_today = datetime.combine(today, datetime.strptime(today_times.fajr, "%H:%M").time())
        iftar_today = datetime.combine(today, datetime.strptime(today_times.maghrib, "%H:%M").time())
        suhoor_tomorrow = datetime.combine(today + timedelta(days=1), datetime.strptime(tomorrow_times.fajr, "%H:%M").time())
        iftar_yesterday = datetime.combine(today - timedelta(days=1), datetime.strptime(yesterday_times.maghrib, "%H:%M").time())

        if now >= iftar_today:
            target = suhoor_tomorrow
            next_name = "сухура"
            phase = "night"
            start = iftar_today
            end = suhoor_tomorrow
            schedule = today_times
        elif now >= suhoor_today:
            target = iftar_today
            next_name = "ифтара"
            phase = "day"
            start = suhoor_today
            end = iftar_today
            schedule = today_times
        else:
            target = suhoor_today
            next_name = "сухура"
            phase = "night"
            start = iftar_yesterday
            end = suhoor_today
            schedule = yesterday_times

        delta = max(0, int((target - now).total_seconds()))
        total = max(1, int((end - start).total_seconds()))
        progress = min(1.0, max(0.0, (now - start).total_seconds() / total))
        palette_progress = self._remap_palette_progress(progress)
        return {
            "next": next_name,
            "countdown": f"{delta // 3600:02d}:{(delta % 3600) // 60:02d}:{delta % 60:02d}",
            "phase": phase,
            "phase_progress": progress,
            "phase_total_seconds": total,
            "suhoor": today_times.fajr,
            "iftar": schedule.maghrib,
            "palette": self._phase_palette(phase, palette_progress),
        }

    def _prayer_times_for_date(self, target_date: date) -> PrayerTimes:
        date_key = target_date.strftime("%Y-%m-%d")
        exact = self.prayer_times.get(date_key)
        if exact:
            return exact

        parsed: list[tuple[date, PrayerTimes]] = []
        for key, value in self.prayer_times.items():
            try:
                parsed.append((datetime.strptime(key, "%Y-%m-%d").date(), value))
            except ValueError:
                continue

        if not parsed:
            raise ValueError("Prayer times are not configured")

        # Файл расписания может быть за конкретный год (например 2026),
        # тогда при несовпадении года сначала ищем совпадение по месяцу/дню.
        # Это позволяет показывать корректные времена в текущем году.
        by_month_day = [item for item in parsed if item[0].month == target_date.month and item[0].day == target_date.day]
        if by_month_day:
            return by_month_day[0][1]

        parsed.sort(key=lambda item: abs((item[0] - target_date).days))
        return parsed[0][1]

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
