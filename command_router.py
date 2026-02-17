from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CommandEvent:
    command: str
    payload: dict[str, Any] | None = None
    source: str = "manual"
    wake_word_detected: bool = False


class CommandRouter:
    """Normalizes commands from external inputs (voice, GPIO, UI)."""

    def __init__(self) -> None:
        self._aliases = {
            "open_map": "open_tasks_map",
            "карта": "open_tasks_map",
            "open_review": "open_day_review",
            "start_day_review": "open_day_review",
            "open_task": "open_task_info",
            "open_today_task": "open_task_info",
            "map": "open_tasks_map",
            "review": "open_day_review",
            "task": "open_task_info",
            "назад": "back",
            "+1": "next",
            "-1": "prev",
        }

    def normalize(self, command: str) -> str:
        key = " ".join(command.strip().lower().split())
        return self._aliases.get(key, key)

    def normalize_event(self, event: CommandEvent) -> CommandEvent:
        return CommandEvent(
            command=self.normalize(event.command),
            payload=event.payload,
            source=event.source,
            wake_word_detected=event.wake_word_detected,
        )
