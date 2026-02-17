from __future__ import annotations

from typing import Any

from models import Session, Task
from states.base_state import BaseState


class TaskMapState(BaseState):
    name = "task_map"

    def __init__(self, session: Session, tasks: list[Task]):
        self.session = session
        self.tasks = tasks

    def show(self) -> dict[str, Any]:
        day_data = self.session.days[self.session.current_day]
        return {
            "view": self.name,
            "screen": "ui/task_map.html",
            "day": self.session.current_day,
            "children": self.session.children,
            "scores": day_data.scores,
            "closed": day_data.closed,
            "review_order": day_data.review_order,
            "review_index": day_data.review_index,
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "start_day_review":
            return "day_review"
        if command == "back":
            return "base"
        return None
