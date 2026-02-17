from __future__ import annotations

from datetime import datetime, time
from typing import Any

from models import Session, Task
from states.base_state import BaseState


class BaseHomeState(BaseState):
    name = "base"

    def __init__(self, session: Session, tasks: list[Task]):
        self.session = session
        self.tasks = tasks

    def _time_left(self, target: time) -> str:
        now = datetime.now()
        target_dt = datetime.combine(now.date(), target)
        if now >= target_dt:
            return "время прошло"
        delta = target_dt - now
        minutes = int(delta.total_seconds() // 60)
        return f"{minutes // 60} ч {minutes % 60} мин"

    def show(self) -> dict[str, Any]:
        task = self.tasks[self.session.current_day - 1]
        return {
            "view": self.name,
            "screen": "ui/base_home.html",
            "day": self.session.current_day,
            "today_task": task.text,
            "time_to_suhur": self._time_left(time(4, 30)),
            "time_to_iftar": self._time_left(time(19, 15)),
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "start_day_review":
            return "day_review"
        if command == "open_map":
            return "task_map"
        if command == "open_summary":
            return "summary"
        return None
