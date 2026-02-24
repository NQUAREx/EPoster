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
        day.viewed = True
        return {
            "view": self.name,
            "day": day_num,
            "task_text": self.tasks[day_num - 1].text,
            "task_type": self.tasks[day_num - 1].type,
            "closed": day.closed,
            "scores_line": [
                {"child": child, "score": self._format_score(score)}
                for child, score in day.scores.items()
                if score is not None
            ],
        }

    def _format_score(self, score: int | None) -> str:
        return "—" if score is None else str(score)

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "back":
            return "base_state"
        return None
