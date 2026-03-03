from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List

from models import AppSettings, PrayerTimes, Session, Task
from states.base_state import BaseState


class BaseScreenState(BaseState):
    name = "base_state"

    SLOW_PHASE_REAL_SHARE = 0.8
    SLOW_PHASE_COLOR_SHARE = 0.2

    def __init__(
        self,
        session: Session,
        tasks: List[Task],
        prayer_times: Dict[str, PrayerTimes],
        settings: AppSettings,
        now_provider: Callable[[], datetime] | None = None,
        prayer_overrides_provider: Callable[[], dict[str, str]] | None = None,
    ):
        self.session = session
        self.tasks = tasks
        self.prayer_times = prayer_times
        self.settings = settings
        self._now_provider = now_provider or datetime.now
        self._prayer_overrides_provider = prayer_overrides_provider or (lambda: {})

    @staticmethod
    def _hex_to_rgb(value: str) -> tuple[int, int, int]:
        code = str(value or "").strip().lstrip("#")
        if len(code) != 6:
            raise ValueError(f"Invalid color '{value}'")
        return int(code[0:2], 16), int(code[2:4], 16), int(code[4:6], 16)

    @staticmethod
    def _lerp_rgb(start: tuple[int, int, int], end: tuple[int, int, int], progress: float) -> tuple[int, int, int]:
        p = min(1.0, max(0.0, progress))
        return (
            round(start[0] + (end[0] - start[0]) * p),
            round(start[1] + (end[1] - start[1]) * p),
            round(start[2] + (end[2] - start[2]) * p),
        )

    @staticmethod
    def _rgb_css(color: tuple[int, int, int]) -> str:
        return f"rgb({color[0]}, {color[1]}, {color[2]})"

    @staticmethod
    def _apply_offset(color: tuple[int, int, int], offset: tuple[int, int, int]) -> tuple[int, int, int]:
        return (
            min(255, max(0, color[0] + offset[0])),
            min(255, max(0, color[1] + offset[1])),
            min(255, max(0, color[2] + offset[2])),
        )

    def _phase_palette(self, phase: str, progress: float) -> dict[str, str]:
        suhoor_rgb = self._hex_to_rgb(self.settings.suhoor_color)
        iftar_rgb = self._hex_to_rgb(self.settings.iftar_color)

        # red -> green axis independent from current phase direction.
        red_to_green_progress = progress if phase == "day" else 1.0 - progress
        core = self._lerp_rgb(suhoor_rgb, iftar_rgb, red_to_green_progress)

        bg_offset = self._lerp_rgb((-212, -84, -88), (-92, -212, -142), red_to_green_progress)
        blob2_offset = self._lerp_rgb((-14, -55, -81), (-82, -54, -48), red_to_green_progress)
        blob3_offset = self._lerp_rgb((0, 59, 4), (-11, -31, -33), red_to_green_progress)

        return {
            "bg": self._rgb_css(self._apply_offset(core, bg_offset)),
            "blob1": self._rgb_css(core),
            "blob2": self._rgb_css(self._apply_offset(core, blob2_offset)),
            "blob3": self._rgb_css(self._apply_offset(core, blob3_offset)),
        }

    @classmethod
    def _remap_palette_progress(cls, linear_progress: float) -> float:
        """Замедляет смену фона в начале и ускоряет за 2 часа до конца.

        Пример из запроса: при окне в 10 часов
        - первые 8 реальных часов покрывают только 20% цветового перехода;
        - последние 2 реальных часа покрывают оставшиеся 80%.
        """
        p = min(1.0, max(0.0, linear_progress))
        split_real = cls.SLOW_PHASE_REAL_SHARE
        split_color = cls.SLOW_PHASE_COLOR_SHARE

        if p <= split_real:
            return (p / split_real) * split_color
        accelerated = (p - split_real) / (1.0 - split_real)
        return split_color + accelerated * (1.0 - split_color)

    def _times(self) -> dict[str, Any]:
        now = self._now_provider()
        today = now.date()

        today_source_date, today_times = self._prayer_times_for_date_with_source(today)
        _, yesterday_times = self._prayer_times_for_date_with_source(today - timedelta(days=1))
        _, tomorrow_times = self._prayer_times_for_date_with_source(today + timedelta(days=1))

        overrides = self._prayer_overrides_provider()
        suhoor_time = overrides.get("suhoor", today_times.fajr)
        iftar_time = overrides.get("iftar", today_times.maghrib)

        suhoor_today = datetime.combine(today, datetime.strptime(suhoor_time, "%H:%M").time())
        iftar_today = datetime.combine(today, datetime.strptime(iftar_time, "%H:%M").time())
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
            schedule = today_times

        delta = max(0, int((target - now).total_seconds()))
        total = max(1, int((end - start).total_seconds()))
        progress = min(1.0, max(0.0, (now - start).total_seconds() / total))
        palette_progress = self._remap_palette_progress(progress)
        return {
            "next": next_name,
            "source_date": today_source_date,
            "countdown": f"{delta // 3600:02d}:{(delta % 3600) // 60:02d}:{delta % 60:02d}",
            "phase": phase,
            "phase_progress": progress,
            "phase_total_seconds": total,
            "suhoor": suhoor_time,
            "iftar": iftar_time if schedule is today_times else schedule.maghrib,
            "palette": self._phase_palette(phase, palette_progress),
        }

    def _prayer_times_for_date(self, target_date: date) -> PrayerTimes:
        return self._prayer_times_for_date_with_source(target_date)[1]

    def _prayer_times_for_date_with_source(self, target_date: date) -> tuple[str, PrayerTimes]:
        date_key = target_date.strftime("%Y-%m-%d")
        exact = self.prayer_times.get(date_key)
        if exact:
            return date_key, exact

        parsed: list[tuple[str, date, PrayerTimes]] = []
        for key, value in self.prayer_times.items():
            try:
                parsed.append((key, datetime.strptime(key, "%Y-%m-%d").date(), value))
            except ValueError:
                continue

        if not parsed:
            raise ValueError("Prayer times are not configured")

        by_month_day = [item for item in parsed if item[1].month == target_date.month and item[1].day == target_date.day]
        if by_month_day:
            return by_month_day[0][0], by_month_day[0][2]

        parsed.sort(key=lambda item: abs((item[1] - target_date).days))
        return parsed[0][0], parsed[0][2]

    def _ramadan_elapsed_days(self) -> float:
        now = self._now_provider()
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
