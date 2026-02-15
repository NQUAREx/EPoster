from __future__ import annotations

from typing import Any, List

from models import Session, Task
from states.base_state import BaseState


class SummaryState(BaseState):
    name = "summary"

    def __init__(self, session: Session, tasks: List[Task]):
        self.session = session
        self.tasks = tasks

    def show(self) -> dict[str, Any]:
        day_data = self.session.days[self.session.current_day]
        return {
            "view": self.name,
            "day": self.session.current_day,
            "day_scores": day_data.scores,
            "leaderboard": self.session.leaderboard(),
            "is_last_day": self.session.current_day == 30,
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "next_day":
            if self.session.current_day < 30:
                self.session.current_day += 1
                return "day_review"
            self.session.celebration_mode = True
            return "celebration"

        if command == "back":
            return "task_map"

        return None
