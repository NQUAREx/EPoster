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
            "открой карту": "open_tasks_map",
            "покажи карту": "open_tasks_map",
            "режим карты": "open_tasks_map",
            "open_review": "open_day_review",
            "start_day_review": "open_day_review",
            "проверка": "open_day_review",
            "режим проверки": "open_day_review",
            "оценивание": "open_day_review",
            "open_task": "open_task_info",
            "open_today_task": "open_task_info",
            "задание": "open_task_info",
            "открой задание": "open_task_info",
            "покажи задание": "open_task_info",
            "map": "open_tasks_map",
            "review": "open_day_review",
            "task": "open_task_info",
            "назад": "back",
            "вернуться": "back",
            "домой": "back",
            "+1": "next",
            "-1": "prev",
            "вперед": "next",
            "дальше": "next",
            "следующий": "next",
            "назад день": "prev",
            "предыдущий": "prev",
            "раньше": "prev",
            "ок": "ok",
            "подтвердить": "ok",
            "выбрать": "ok",
            "score 1": "score_1",
            "score 2": "score_2",
            "score 3": "score_3",
            "skip": "score_skip",
            "плохо": "score_1",
            "средне": "score_2",
            "хорошо": "score_3",
            "отлично": "score_3",
            "пропустить": "score_skip",
            "скип": "score_skip",
            "эмбилайт стандарт": "ambilight_effect_wake_blink",
            "эффект эмбилайт стандарт": "ambilight_effect_wake_blink",
            "эмбилайт без эффекта": "ambilight_effect_none",
            "эффект эмбилайт выключить": "ambilight_effect_none",
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
