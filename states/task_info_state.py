from __future__ import annotations

from typing import Any

from models import Session, Task
from states.base_state import BaseState


class TaskInfoState(BaseState):
    name = "task_info_state"

    def __init__(self, session: Session, tasks: list[Task]):
        self.session = session
        self.tasks = tasks

    def show(self) -> dict[str, Any]:
        day_num = self.session.selected_day
        day = self.session.days[day_num]
        return {
            "view": self.name,
            "day": day_num,
            "task_text": self.tasks[day_num - 1].text,
            "closed": day.closed,
            "scores_line": [f"{child}: {self._emoji(score)}" for child, score in day.scores.items() if score is not None],
        }

    def _emoji(self, score: int | None) -> str:
        return {1: "☹️", 2: "🙂", 3: "😄"}.get(score, "—")

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "back":
            return "base_state"
        return None
