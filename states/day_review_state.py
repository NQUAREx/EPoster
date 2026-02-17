from __future__ import annotations

import random
from typing import Any

from models import Session, Task
from states.base_state import BaseState


class DayReviewState(BaseState):
    name = "day_review_state"

    def __init__(self, session: Session, tasks: list[Task]):
        self.session = session
        self.tasks = tasks
        self.completed = False

    def _remaining_children(self) -> list[str]:
        day_data = self.session.days[self.session.current_day]
        return [child for child in self.session.children if day_data.scores.get(child) is None]

    def show(self) -> dict[str, Any]:
        remaining = self._remaining_children()
        child = random.choice(remaining) if remaining else None
        return {
            "view": self.name,
            "day": self.session.current_day,
            "task_text": self.tasks[self.session.current_day - 1].text,
            "child": child,
            "completed": self.completed,
            "score_options": [
                {"score": 1, "emoji": "☹️", "label": "Плохо"},
                {"score": 2, "emoji": "🙂", "label": "Средне"},
                {"score": 3, "emoji": "😄", "label": "Хорошо"},
            ],
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "back":
            return "base_state"

        score = payload.get("score") if payload and command == "set_score" else None
        if command in {"score_1", "score_2", "score_3"}:
            score = int(command.split("_")[1])
        child = payload.get("child") if payload else None

        if score not in {1, 2, 3}:
            return None

        day_data = self.session.days[self.session.current_day]
        remaining = self._remaining_children()
        if not remaining:
            return "base_state"

        target_child = child if child in remaining else random.choice(remaining)
        day_data.scores[target_child] = score

        if not self._remaining_children():
            day_data.closed = True
            day_data.review_index = 0
            day_data.review_order = []
            self.completed = True
            if self.session.current_day < 30:
                self.session.current_day += 1
                self.session.selected_day = self.session.current_day
            return "base_state"
        return None
