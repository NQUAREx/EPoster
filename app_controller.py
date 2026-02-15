from __future__ import annotations

import json
from pathlib import Path

from state_manager import StateManager
from storage import create_session, load_session, save_session

SETTINGS_FILE = Path("data/settings.json")


class AppController:
    def __init__(self):
        session = load_session()
        if session is None:
            with SETTINGS_FILE.open("r", encoding="utf-8") as file:
                settings = json.load(file)
            session = create_session(settings.get("children", []))

        self.session = session
        self.state_manager = StateManager(session)

    def render(self) -> dict:
        return self.state_manager.show()

    def dispatch(self, command: str, payload: dict | None = None) -> dict:
        ui_payload = self.state_manager.handle_command(command, payload)
        save_session(self.session)
        return ui_payload
