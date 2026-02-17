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
        day = self.session.days[self.session.current_day]
        if not day.review_order:
            day.review_order = list(self.session.children)
            random.shuffle(day.review_order)
            day.review_index = 0

    def show(self) -> dict[str, Any]:
        day_data = self.session.days[self.session.current_day]
        child = None if day_data.review_index >= len(day_data.review_order) else day_data.review_order[day_data.review_index]
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

        day_data = self.session.days[self.session.current_day]
        score = payload.get("score") if payload and command == "set_score" else None
        if command in {"score_1", "score_2", "score_3"}:
            score = int(command.split("_")[1])

        if score not in {1, 2, 3}:
            return None

        if day_data.review_index < len(day_data.review_order):
            child = day_data.review_order[day_data.review_index]
            day_data.scores[child] = score
            day_data.review_index += 1

        if day_data.review_index >= len(day_data.review_order):
            day_data.closed = True
            day_data.review_index = 0
            day_data.review_order = []
            self.completed = True
            if self.session.current_day < 30:
                self.session.current_day += 1
                self.session.selected_day = self.session.current_day
            return "base_state"
        return None
