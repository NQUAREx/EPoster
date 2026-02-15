from __future__ import annotations

from typing import Any

from states.base_state import BaseState


class CelebrationState(BaseState):
    name = "celebration"

    def show(self) -> dict[str, Any]:
        return {"view": "celebration"}

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        return None
