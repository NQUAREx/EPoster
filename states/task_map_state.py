from __future__ import annotations

from typing import Any, List

from models import Session, Task
from states.base_state import BaseState


class TaskMapState(BaseState):
    name = "task_map"

    def __init__(self, session: Session, tasks: List[Task]):
        self.session = session
        self.tasks = tasks

    def _status(self, day_number: int) -> str:
        if self.session.days[day_number].closed:
            return "completed"
        if day_number == self.session.current_day:
            return "open"
        return "locked"

    def show(self) -> dict[str, Any]:
        circles = []
        for index in range(30):
            day_number = index + 1
            circles.append(
                {
                    "day": day_number,
                    "status": self._status(day_number),
                    "selected": day_number == self.session.selected_day,
                }
            )
        return {
            "view": self.name,
            "current_day": self.session.current_day,
            "selected_day": self.session.selected_day,
            "circles": circles,
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command in {"next", "forward"}:
            self.session.selected_day = min(30, self.session.selected_day + 1)
            return None
        if command in {"prev", "back"}:
            self.session.selected_day = max(1, self.session.selected_day - 1)
            return None
        if command == "open_selected_day" and self.session.selected_day == self.session.current_day:
            return "task"
        if command == "home":
            return "base"
        return None
