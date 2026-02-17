from __future__ import annotations

from typing import Any, List

from models import Session, Task
from states.base_state import BaseState


class TaskMapState(BaseState):
    name = "task_map"

    def __init__(self, session: Session, tasks: List[Task]):
        self.session = session
        self.tasks = tasks

    def _all_children_scored(self) -> bool:
        day_data = self.session.days[self.session.current_day]
        return all(day_data.scores.get(child) is not None for child in self.session.children)

    def show(self) -> dict[str, Any]:
        day_data = self.session.days[self.session.current_day]
        return {
            "view": self.name,
            "screen": "ui/task_map.html",
            "day": self.session.current_day,
            "children": self.session.children,
            "scores": day_data.scores,
            "closed": day_data.closed,
            "can_close_day": self._all_children_scored(),
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        payload = payload or {}
        day_data = self.session.days[self.session.current_day]

        if command == "set_score":
            child = payload.get("child")
            score = payload.get("score")
            if child in self.session.children and isinstance(score, int) and 0 <= score <= 3:
                day_data.scores[child] = score
            return None

        if command == "clear_score":
            child = payload.get("child")
            if child in self.session.children:
                day_data.scores[child] = None
            return None

        if command == "finish_day":
            if not self._all_children_scored():
                return None
            day_data.closed = True
            return "summary"

        if command == "back":
            return "day_review"

        return None
