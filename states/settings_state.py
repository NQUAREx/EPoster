from __future__ import annotations

from typing import Any

from models import AppSettings
from states.base_state import BaseState


class SettingsState(BaseState):
    name = "settings"

    def __init__(self, settings: AppSettings):
        self.settings = settings

    def show(self) -> dict[str, Any]:
        return {
            "view": self.name,
            "screen": "ui/settings.html",
            "language": "ru",
            "secret_celebration_command": self.settings.secret_celebration_command,
            "gift_total_target": self.settings.gift_total_target,
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        payload = payload or {}

        if command == "set_secret_command":
            secret = payload.get("secret")
            if isinstance(secret, str) and secret.strip():
                self.settings.secret_celebration_command = secret.strip()
            return None

        if command == "set_gift_total_target":
            target = payload.get("target")
            if isinstance(target, int) and target >= 0:
                self.settings.gift_total_target = target
            return None

        if command == "back":
            return "base"

        return None
