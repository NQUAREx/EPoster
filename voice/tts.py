from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TTSMessage:
    text: str
    language: str
    created_at: str


@dataclass
class TTSService:
    """Simple in-memory TTS adapter.

    На Raspberry Pi можно заменить на pyttsx3/espeak или облачный TTS.
    """

    default_language: str = "ru"
    history: list[TTSMessage] = field(default_factory=list)

    def speak(self, text: str, language: str | None = None) -> TTSMessage:
        message = TTSMessage(
            text=text,
            language=language or self.default_language,
            created_at=datetime.utcnow().isoformat(),
        )
        self.history.append(message)
        return message
