from __future__ import annotations

from typing import Any, List

from models import Session, Task
from states.base_state import BaseState


class TaskState(BaseState):
    name = "task"

    def __init__(self, session: Session, tasks: List[Task]):
        self.session = session
        self.tasks = tasks

    def show(self) -> dict[str, Any]:
        task = self.tasks[self.session.current_day - 1]
        return {"view": self.name, "day": self.session.current_day, "task_text": task.text}

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        if command == "start_review":
            return "day_review"
        if command == "back":
            return "task_map"
        return None
