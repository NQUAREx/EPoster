from __future__ import annotations

from pydantic import BaseModel


class CommandRequest(BaseModel):
    command: str
    payload: dict | None = None
    source: str = "manual"
    wake_word_detected: bool = False


class WakeRequest(BaseModel):
    source: str = "voice"
