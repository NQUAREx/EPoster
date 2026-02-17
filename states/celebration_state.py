from __future__ import annotations

from typing import Any

from models import Session
from states.base_state import BaseState


class CelebrationState(BaseState):
    name = "eid"

    def __init__(self, session: Session):
        self.session = session

    def show(self) -> dict[str, Any]:
        return {
            "view": self.name,
            "message": "🎉 С праздником Ид!",
            "children_totals": {child: self.session.total_score(child) for child in self.session.children},
            "total_points": self.session.total_score_all(),
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "home":
            return "base"
        return None
