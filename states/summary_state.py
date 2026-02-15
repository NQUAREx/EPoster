from __future__ import annotations

from typing import Any

from states.base_state import BaseState


class SummaryState(BaseState):
    name = "summary"

    def __init__(self, current_day: int):
        self.current_day = current_day

    def show(self) -> dict[str, Any]:
        return {"view": "summary", "day": self.current_day}

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "next_day":
            return "day_review"
        return None
