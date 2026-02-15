from __future__ import annotations

from typing import Any

from models import Session
from states.base_state import BaseState


class CelebrationState(BaseState):
    name = "celebration"

    def __init__(self, session: Session):
        self.session = session

    def show(self) -> dict[str, Any]:
        return {
            "view": self.name,
            "message": "Рамадан завершён! Молодцы!",
            "leaderboard": self.session.leaderboard(),
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "restart":
            self.session.current_day = 1
            self.session.celebration_mode = False
            for day in self.session.days.values():
                day.closed = False
                day.scores.clear()
            return "day_review"
        return None
