from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LightState:
    mode: str = "idle"
    brightness: int = 50
    color: str = "white"


class LightController:
    """Stub light controller: logs and prints accepted commands."""

    def __init__(self):
        self.state = LightState()
        self.command_log: list[str] = []

    def _accept(self, command: str) -> None:
        self.command_log.append(command)
        print(f"[LIGHT_STUB] {command}")

    def set_idle(self) -> None:
        self.state.mode = "idle"
        self.state.color = "white"
        self._accept("set_idle")

    def set_review(self) -> None:
        self.state.mode = "review"
        self.state.color = "blue"
        self._accept("set_review")

    def set_celebration(self) -> None:
        self.state.mode = "celebration"
        self.state.color = "gold"
        self._accept("set_celebration")

    def set_brightness(self, value: int) -> None:
        self.state.brightness = max(0, min(100, int(value)))
        self._accept(f"set_brightness:{self.state.brightness}")
