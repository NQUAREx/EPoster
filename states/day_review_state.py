from __future__ import annotations

from typing import Any, List

from models import Session, Task
from states.base_state import BaseState


class DayReviewState(BaseState):
    name = "day_review"

    def __init__(self, session: Session, tasks: List[Task]):
        self.session = session
        self.tasks = tasks

    def _current_task(self) -> Task:
        return self.tasks[self.session.current_day - 1]

    def show(self) -> dict[str, Any]:
        day = self.session.days[self.session.current_day]
        task = self._current_task()
        return {
            "view": self.name,
            "screen": "ui/day_review.html",
            "day": self.session.current_day,
            "task": {"text": task.text, "type": task.type},
            "closed": day.closed,
            "scores": day.scores,
            "children": self.session.children,
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "open_map":
            return "task_map"
        if command == "open_summary":
            return "summary"
        return None
