from __future__ import annotations

import random
from typing import Any

from models import Session, Task
from states.base_state import BaseState


class DayReviewState(BaseState):
    name = "day_review_state"
    _SCORE_COMMANDS = {
        "score_1": 1,
        "score_2": 2,
        "score_3": 3,
        "score_skip": None,
    }

    def __init__(self, session: Session, tasks: list[Task]):
        self.session = session
        self.tasks = tasks
        self.completed = False

    def _ensure_random_order(self) -> None:
        day_data = self.session.days[self.session.selected_day]
        if not day_data.review_order:
            day_data.review_order = list(self.session.children)
            random.shuffle(day_data.review_order)
            day_data.review_index = 0

    def _current_child(self) -> str | None:
        self._ensure_random_order()
        day_data = self.session.days[self.session.selected_day]
        if day_data.review_index >= len(day_data.review_order):
            return None
        return day_data.review_order[day_data.review_index]


    def _remaining_children(self) -> int:
        day_data = self.session.days[self.session.selected_day]
        return max(0, len(day_data.review_order) - day_data.review_index)

    def _resolve_score(self, command: str, payload: dict[str, Any] | None) -> int | None | str:
        if command in self._SCORE_COMMANDS:
            return self._SCORE_COMMANDS[command]

        if command == "set_score" and payload:
            if payload.get("score") is None:
                return None
            try:
                return int(payload["score"])
            except (TypeError, ValueError):
                return "invalid"

        return "invalid"

    def show(self) -> dict[str, Any]:
        return {
            "view": self.name,
            "day": self.session.selected_day,
            "task_text": self.tasks[self.session.selected_day - 1].text,
            "task_type": self.tasks[self.session.selected_day - 1].type,
            "child": self._current_child(),
            "completed": self.completed,
            "score_options": [
                {"score": 1, "emoji": "☹️", "label": "Плохо"},
                {"score": 2, "emoji": "🙂", "label": "Не очень"},
                {"score": 3, "emoji": "😄", "label": "Хорошо"},
                {"score": None, "emoji": "⏭️", "label": "Пропустить"},
            ],
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "back":
            return "base_state"

        score = self._resolve_score(command, payload)
        if score == "invalid" or score not in {1, 2, 3, None}:
            return None

        day_data = self.session.days[self.session.selected_day]
        child = self._current_child()
        if child is None:
            return "base_state"

        day_data.scores[child] = score
        day_data.review_index += 1

        if not self._remaining_children():
            day_data.closed = all(child_score in {1, 2, 3} for child_score in day_data.scores.values())
            day_data.review_index = 0
            day_data.review_order = []
            self.completed = day_data.closed
            return "base_state"
        return None
