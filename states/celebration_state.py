from __future__ import annotations

from typing import Any

from models import AppSettings, Session
from states.base_state import BaseState


class CelebrationState(BaseState):
    name = "celebration"

    def __init__(self, session: Session, settings: AppSettings):
        self.session = session
        self.settings = settings

    def _gift_ready(self) -> bool | None:
        if self.settings.gift_total_target is None:
            return None
        return all(self.session.total_score(child) >= self.settings.gift_total_target for child in self.session.children)

    def show(self) -> dict[str, Any]:
        return {
            "view": self.name,
            "screen": "ui/celebration.html",
            "message": "Рамадан завершён! Молодцы!",
            "totals": {child: self.session.total_score(child) for child in self.session.children},
            "gift_total_target": self.settings.gift_total_target,
            "gift_ready": self._gift_ready(),
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "restart":
            self.session.current_day = 1
            self.session.celebration_mode = False
            for day in self.session.days.values():
                day.closed = False
                for child in self.session.children:
                    day.scores[child] = None
            return "day_review"
        return None
