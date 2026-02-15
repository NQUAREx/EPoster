from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LightState:
    mode: str = "idle"
    brightness: int = 50
    color: str = "white"


class LightController:
    """In-memory light controller with Raspberry Pi friendly interface."""

    def __init__(self):
        self.state = LightState()

    def set_idle(self) -> None:
        self.state.mode = "idle"
        self.state.color = "white"

    def set_review(self) -> None:
        self.state.mode = "review"
        self.state.color = "blue"

    def set_celebration(self) -> None:
        self.state.mode = "celebration"
        self.state.color = "gold"

    def set_brightness(self, value: int) -> None:
        self.state.brightness = max(0, min(100, int(value)))
