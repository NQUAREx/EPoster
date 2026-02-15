from __future__ import annotations

from typing import Any, List

from models import AppSettings, Session, Task
from states.base_state import BaseState


class SummaryState(BaseState):
    name = "summary"

    def __init__(self, session: Session, tasks: List[Task], settings: AppSettings):
        self.session = session
        self.tasks = tasks
        self.settings = settings

    def _gift_ready(self) -> bool | None:
        if self.settings.gift_total_target is None:
            return None
        return all(self.session.total_score(child) >= self.settings.gift_total_target for child in self.session.children)

    def show(self) -> dict[str, Any]:
        day_data = self.session.days[self.session.current_day]
        return {
            "view": self.name,
            "screen": "ui/summary.html",
            "day": self.session.current_day,
            "day_scores": day_data.scores,
            "totals": {child: self.session.total_score(child) for child in self.session.children},
            "is_last_day": self.session.current_day == 30,
            "gift_total_target": self.settings.gift_total_target,
            "gift_ready": self._gift_ready(),
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
