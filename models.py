from __future__ import annotations

from dataclasses import asdict, dataclass, field
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

    @staticmethod
    def from_dict(data: dict) -> "AppSettings":
        return AppSettings(
            language="ru",
            secret_celebration_command=data.get("secret_celebration_command", "eid-mode"),
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["language"] = "ru"
        return payload


@dataclass
class Day:
    scores: Dict[str, int | None] = field(default_factory=dict)
    closed: bool = False
    review_order: List[str] = field(default_factory=list)
    review_index: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Day":
        scores_data = data.get("scores", {})
        normalized: Dict[str, int | None] = {}
        for child, score in scores.items():
            normalized[child] = score if isinstance(score, int) else None
        return Day(scores=normalized, closed=data.get("closed", False))


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
