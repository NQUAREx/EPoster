from __future__ import annotations

import random
from typing import Any

from models import Session, Task
from states.base_state import BaseState


class DayReviewState(BaseState):
    name = "day_review_state"
    _SCORES = list(range(10))
    _SCORE_SKIP = None

    def __init__(self, session: Session, tasks: list[Task]):
        self.session = session
        self.tasks = tasks
        self.completed = False
        self._prepared_index: int | None = None

    def _ensure_random_order(self) -> None:
        day_data = self.session.days[self.session.selected_day]
        if not day_data.review_order:
            day_data.review_order = list(self.session.children)
            random.shuffle(day_data.review_order)
            day_data.review_index = 0

    def _prepare_current_child(self) -> None:
        day_data = self.session.days[self.session.selected_day]
        if day_data.review_index >= len(day_data.review_order):
            return
        if self._prepared_index == day_data.review_index:
            return

        random_pos = random.randrange(day_data.review_index, len(day_data.review_order))
        day_data.review_order[day_data.review_index], day_data.review_order[random_pos] = (
            day_data.review_order[random_pos],
            day_data.review_order[day_data.review_index],
        )
        self._prepared_index = day_data.review_index

    def _current_child(self) -> str | None:
        self._ensure_random_order()
        day_data = self.session.days[self.session.selected_day]
        if day_data.review_index >= len(day_data.review_order):
            return None
        self._prepare_current_child()
        return day_data.review_order[day_data.review_index]


    def _remaining_children(self) -> int:
        day_data = self.session.days[self.session.selected_day]
        return max(0, len(day_data.review_order) - day_data.review_index)

    def _score_options(self) -> list[int | None]:
        return [*self._SCORES, self._SCORE_SKIP]

    def _move_cursor(self, direction: int) -> None:
        day_data = self.session.days[self.session.selected_day]
        options_count = len(self._score_options())
        day_data.review_score_cursor = (day_data.review_score_cursor + direction) % options_count

    def _selected_score(self) -> int | None:
        day_data = self.session.days[self.session.selected_day]
        return self._score_options()[day_data.review_score_cursor]

    def _resolve_score(self, command: str, payload: dict[str, Any] | None) -> int | None | str:
        if command == "ok":
            return self._selected_score()
        if command == "score_skip":
            return self._SCORE_SKIP

        if command == "set_score" and payload:
            if payload.get("score") is None:
                return self._SCORE_SKIP
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
                {
                    "score": score,
                    "label": "Пропуск" if score is None else str(score),
                    "selected": self.session.days[self.session.selected_day].review_score_cursor == index,
                }
                for index, score in enumerate(self._score_options())
            ],
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "back":
            return "base_state"
        if command in {"next", "+1"}:
            self._move_cursor(1)
            return None
        if command in {"prev", "-1"}:
            self._move_cursor(-1)
            return None

        score = self._resolve_score(command, payload)
        if score == "invalid" or score not in {*self._SCORES, self._SCORE_SKIP}:
            return None

        day_data = self.session.days[self.session.selected_day]
        child = self._current_child()
        if child is None:
            return "base_state"

        day_data.scores[child] = score
        day_data.review_index += 1
        self._prepared_index = None

        if not self._remaining_children():
            day_data.closed = all(child_score is not None for child_score in day_data.scores.values())
            day_data.review_index = 0
            day_data.review_order = []
            self.completed = day_data.closed
            return "base_state"
        return None
