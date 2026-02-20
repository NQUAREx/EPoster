from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class Task:
    day: int
    text: str
    type: str

    @staticmethod
    def from_dict(data: dict) -> "Task":
        return Task(day=int(data["day"]), text=data["text"], type=data.get("type", "обычное"))


@dataclass
class PrayerTimes:
    fajr: str
    maghrib: str

    @staticmethod
    def from_dict(data: dict) -> "PrayerTimes":
        return PrayerTimes(fajr=data["fajr"], maghrib=data["maghrib"])


@dataclass
class AppSettings:
    language: str = "ru"
    secret_celebration_command: str = "eid-mode"
    children: List[str] = field(default_factory=list)
    ramadan_day: int = 1
    ramadan_day_updated_on: str = ""

    @staticmethod
    def from_dict(data: dict) -> "AppSettings":
        raw_day = data.get("ramadan_day", 1)
        try:
            ramadan_day = int(raw_day)
        except (TypeError, ValueError):
            ramadan_day = 1
        ramadan_day = min(30, max(1, ramadan_day))

        updated_on = data.get("ramadan_day_updated_on", "")
        if not isinstance(updated_on, str):
            updated_on = ""
        if updated_on:
            try:
                datetime.strptime(updated_on, "%Y-%m-%d")
            except ValueError:
                updated_on = ""

        return AppSettings(
            language="ru",
            secret_celebration_command=data.get("secret_celebration_command", "eid-mode"),
            children=[name.strip() for name in data.get("children", []) if isinstance(name, str) and name.strip()],
            ramadan_day=ramadan_day,
            ramadan_day_updated_on=updated_on,
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["language"] = "ru"
        return payload


@dataclass
class Day:
    scores: Dict[str, int | None] = field(default_factory=dict)
    closed: bool = False
    viewed: bool = False
    review_order: List[str] = field(default_factory=list)
    review_index: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Day":
        scores_data = data.get("scores", {})
        normalized: Dict[str, int | None] = {}
        for child, score in scores_data.items():
            normalized[child] = score if isinstance(score, int) else None
        return Day(
            scores=normalized,
            closed=data.get("closed", False),
            viewed=bool(data.get("viewed", False)),
            review_order=[name for name in data.get("review_order", []) if isinstance(name, str)],
            review_index=int(data.get("review_index", 0) or 0),
        )


@dataclass
class Session:
    current_day: int
    celebration_mode: bool
    children: List[str]
    selected_day: int = 1
    days: Dict[int, Day] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "current_day": self.current_day,
            "selected_day": self.selected_day,
            "celebration_mode": self.celebration_mode,
            "children": self.children,
            "days": {str(day_num): day.to_dict() for day_num, day in self.days.items()},
        }

    @staticmethod
    def from_dict(data: dict) -> "Session":
        days = {int(k): Day.from_dict(v) for k, v in data.get("days", {}).items()}
        return Session(
            current_day=data.get("current_day", 1),
            selected_day=data.get("selected_day", data.get("current_day", 1)),
            celebration_mode=data.get("celebration_mode", False),
            children=data.get("children", []),
            days=days,
        )

    def total_score(self, child: str) -> int:
        return sum((day.scores.get(child) or 0) for day in self.days.values())

    def total_score_all(self) -> int:
        return sum(self.total_score(child) for child in self.children)

    def last_completed_day(self) -> int:
        completed = [day_num for day_num, day in self.days.items() if day.closed]
        return max(completed, default=0)

    def max_unlocked_day(self) -> int:
        return min(30, max(1, self.last_completed_day() + 2))

    def is_task_locked(self, day_num: int) -> bool:
        return day_num > self.max_unlocked_day()

    def open_task_days(self) -> list[int]:
        return [day for day in range(1, 31) if not self.is_task_locked(day) and not self.days[day].closed]

    def first_open_task_day(self) -> int:
        open_days = self.open_task_days()
        return open_days[0] if open_days else 1

    def last_open_task_day(self) -> int:
        open_days = self.open_task_days()
        return open_days[-1] if open_days else 1

    def base_task_day(self) -> int:
        selected_day = min(30, max(1, int(self.selected_day or 1)))
        selected = self.days[selected_day]

        if self.is_task_locked(selected_day):
            return self.last_open_task_day()
        if selected.closed:
            return self.first_open_task_day()
        return selected_day
