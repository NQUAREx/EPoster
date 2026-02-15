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
class AppSettings:
    children: List[str] = field(default_factory=list)
    language: str = "ru"
    secret_celebration_command: str = "eid-mode"

    @staticmethod
    def from_dict(data: dict) -> "AppSettings":
        return AppSettings(
            children=list(data.get("children", [])),
            language=data.get("language", "ru"),
            secret_celebration_command=data.get("secret_celebration_command", "eid-mode"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Day:
    """Mutable state for one Ramadan day."""

    scores: Dict[str, int] = field(default_factory=dict)
    closed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Day":
        return Day(scores=data.get("scores", {}), closed=data.get("closed", False))


@dataclass
class Session:
    """Global mutable session state."""

    current_day: int
    celebration_mode: bool
    children: List[str]
    days: Dict[int, Day] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "current_day": self.current_day,
            "celebration_mode": self.celebration_mode,
            "children": self.children,
            "days": {str(day_num): day.to_dict() for day_num, day in self.days.items()},
        }

    @staticmethod
    def from_dict(data: dict) -> "Session":
        days = {int(k): Day.from_dict(v) for k, v in data.get("days", {}).items()}
        return Session(
            current_day=data.get("current_day", 1),
            celebration_mode=data.get("celebration_mode", False),
            children=data.get("children", []),
            days=days,
        )

    def all_days_closed(self) -> bool:
        return bool(self.days) and all(day.closed for day in self.days.values())

    def total_score(self, child: str) -> int:
        return sum(day.scores.get(child, 0) for day in self.days.values())

    def leaderboard(self) -> List[dict]:
        board = [{"child": child, "total": self.total_score(child)} for child in self.children]
        return sorted(board, key=lambda item: (-item["total"], item["child"]))
