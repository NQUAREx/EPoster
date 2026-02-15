from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VoiceCommand:
    text: str
    confidence: float = 1.0


class VoiceRecognizer:
    """Queue-based recognizer stub for offline tests and integration."""

    def __init__(self):
        self._queue: list[VoiceCommand] = []

    def push_simulated(self, text: str, confidence: float = 1.0) -> None:
        self._queue.append(VoiceCommand(text=text, confidence=confidence))

    def listen(self) -> VoiceCommand | None:
        if not self._queue:
            return None
        return self._queue.pop(0)
