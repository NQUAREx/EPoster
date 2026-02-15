from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseState(ABC):
    name = "base"

    @abstractmethod
    def show(self) -> dict[str, Any]:
        """Returns UI payload for rendering."""

    @abstractmethod
    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        """Handles button/voice command and optionally returns next state name."""
