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
            "language": self.settings.language,
            "secret_celebration_command": self.settings.secret_celebration_command,
            "children": self.settings.children,
        }

    def handle_command(self, command: str, payload: dict[str, Any] | None = None) -> str | None:
        payload = payload or {}

        if command == "set_language":
            language = payload.get("language")
            if isinstance(language, str) and language:
                self.settings.language = language
            return None

        if command == "set_secret_command":
            secret = payload.get("secret")
            if isinstance(secret, str) and secret.strip():
                self.settings.secret_celebration_command = secret.strip()
            return None

        if command == "back":
            return "day_review"

        return None
