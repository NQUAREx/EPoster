from __future__ import annotations

from typing import Any

from states.base_state import BaseState


class TaskMapState(BaseState):
    name = "task_map"

    def __init__(self, current_day: int):
        self.current_day = current_day

    def show(self) -> dict[str, Any]:
        return {"view": "task_map", "day": self.current_day}

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "finish_day":
            return "summary"
        return None
