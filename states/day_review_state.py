from __future__ import annotations

import random
from typing import Any, List

from models import Session, Task
from states.base_state import BaseState


class DayReviewState(BaseState):
    name = "day_review"

    def __init__(self, session: Session, tasks: list[Task]):
        self.session = session
        self.tasks = tasks
        self.review_order: list[str] = random.sample(self.session.children, len(self.session.children))
        self.current_index = 0
        self.score_dialog_open = False

    def _current_child(self) -> str:
        return self.review_order[self.current_index]

    def _active_child(self) -> str | None:
        day = self.session.days[self.session.current_day]
        if day.review_index >= len(day.review_order):
            return None
        return day.review_order[day.review_index]

    def show(self) -> dict[str, Any]:
        return {
            "view": self.name,
            "day": self.session.current_day,
            "current_child": self._current_child(),
            "review_order": self.review_order,
            "current_index": self.current_index,
            "score_dialog_open": self.score_dialog_open,
            "score_options": [
                {"score": 1, "emoji": "😟", "color": "red"},
                {"score": 2, "emoji": "🙂", "color": "yellow"},
                {"score": 3, "emoji": "😄", "color": "green"},
            ],
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        payload = payload or {}
        day_data = self.session.days[self.session.current_day]

        if command == "set_points":
            self.score_dialog_open = True
            return None

        score = payload.get("score") if command == "set_score" else None
        if command in {"score_1", "score_2", "score_3"}:
            score = int(command.split("_")[1])

        if isinstance(score, int) and score in {1, 2, 3}:
            day_data.scores[self._current_child()] = score
            self.score_dialog_open = False
            self.current_index += 1
            if self.current_index >= len(self.review_order):
                day_data.closed = True
                if self.session.current_day >= 30:
                    self.session.celebration_mode = True
                    return "eid"
                self.session.current_day += 1
                self.session.selected_day = self.session.current_day
                return "task_map"
        return None
