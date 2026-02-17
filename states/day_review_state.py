from __future__ import annotations

from typing import Any

from models import Session, Task
from states.base_state import BaseState


class DayReviewState(BaseState):
    name = "day_review"

    def __init__(self, session: Session, tasks: list[Task]):
        self.session = session
        self.tasks = tasks

    def _current_task(self) -> Task:
        return self.tasks[self.session.current_day - 1]

    def _active_child(self) -> str | None:
        day = self.session.days[self.session.current_day]
        if day.review_index >= len(day.review_order):
            return None
        return day.review_order[day.review_index]

    def show(self) -> dict[str, Any]:
        day = self.session.days[self.session.current_day]
        return {
            "view": self.name,
            "screen": "ui/day_review.html",
            "fullscreen": True,
            "day": self.session.current_day,
            "task": {"text": self._current_task().text, "type": self._current_task().type},
            "active_child": self._active_child(),
            "review_order": day.review_order,
            "review_index": day.review_index,
            "scores": day.scores,
            "ready_for_summary": self._active_child() is None,
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        day = self.session.days[self.session.current_day]
        payload = payload or {}

        if command == "set_score":
            score = payload.get("score")
            child = self._active_child()
            if child is not None and isinstance(score, int) and 0 <= score <= 3:
                day.scores[child] = score
                day.review_index += 1
                if day.review_index >= len(day.review_order):
                    day.closed = True
                    return "summary"
            return None

        if command == "open_map":
            return "task_map"
        if command == "open_summary":
            return "summary"
        if command == "back":
            return "base"
        return None
