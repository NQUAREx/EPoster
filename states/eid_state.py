from __future__ import annotations

from typing import Any

from models import Session
from states.base_state import BaseState


class EidState(BaseState):
    name = "eid_state"

    def __init__(self, session: Session):
        self.session = session

    def show(self) -> dict[str, Any]:
        return {"view": self.name, "message": "eid mubarak"}

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "back":
            return "base_state"
        return None
