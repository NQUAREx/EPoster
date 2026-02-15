from __future__ import annotations

from typing import Any, List

from models import Session, Task
from states.base_state import BaseState


class TaskMapState(BaseState):
    name = "task_map"

    def __init__(self, session: Session, tasks: List[Task]):
        self.session = session
        self.tasks = tasks

    def show(self) -> dict[str, Any]:
        day_data = self.session.days[self.session.current_day]
        return {
            "view": self.name,
            "day": self.session.current_day,
            "children": self.session.children,
            "scores": day_data.scores,
            "closed": day_data.closed,
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        payload = payload or {}
        day_data = self.session.days[self.session.current_day]

        if command == "set_score":
            child = payload.get("child")
            score = payload.get("score")
            if child in self.session.children and isinstance(score, int) and 0 <= score <= 5:
                day_data.scores[child] = score
            return None

        if command == "finish_day":
            for child in self.session.children:
                day_data.scores.setdefault(child, 0)
            day_data.closed = True
            return "summary"

        if command == "back":
            return "day_review"

        return None
