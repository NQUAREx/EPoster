from __future__ import annotations

from typing import Any

from models import Session, Task
from states.base_state import BaseState


class TasksMapState(BaseState):
    name = "tasks_map_state"

    def __init__(self, session: Session, tasks: list[Task]):
        self.session = session
        self.tasks = tasks

    def _status(self, day_number: int) -> str:
        day = self.session.days[day_number]
        if day.closed:
            return "completed"
        if day.viewed or day_number <= self.session.current_day + 1:
            return "open"
        return "locked"

    def show(self) -> dict[str, Any]:
        return {
            "view": self.name,
            "current_day": self.session.current_day,
            "selected_day": self.session.selected_day,
            "warning": "",
            "circles": [
                {
                    "day": day,
                    "status": self._status(day),
                    "selected": day == self.session.selected_day,
                    "viewed": self.session.days[day].viewed,
                }
                for day in range(1, 31)
            ],
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command in {"next", "+1"}:
            self.session.selected_day = min(30, self.session.selected_day + 1)
            return None
        if command in {"prev", "-1"}:
            self.session.selected_day = max(1, self.session.selected_day - 1)
            return None
        if command in {"ok", "open_selected_day"}:
            if self.session.selected_day > self.session.current_day + 2:
                return None
            self.session.days[self.session.selected_day].viewed = True
            return "task_info_state"
        if command == "back":
            return "base_state"
        return None
