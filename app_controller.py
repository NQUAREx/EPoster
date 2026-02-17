from __future__ import annotations

from state_manager import StateManager
from storage import (
    create_session,
    load_children,
    load_prayer_times,
    load_session,
    load_settings,
    load_tasks,
    save_session,
    save_settings,
)


class AppController:
    def __init__(self):
        self.settings = load_settings()
        self.tasks = load_tasks()
        self.prayer_times = load_prayer_times()

        children = self.settings.children or load_children()
        session = load_session()
        if session is None:
            session = create_session(children)
        else:
            session.children = children

        self.session = session
        self.state_manager = StateManager(session, self.tasks, self.settings, self.prayer_times)

    def render(self) -> dict:
        ui_payload = self.state_manager.show()
        save_session(self.session)
        return ui_payload

    def dispatch(self, command: str, payload: dict | None = None) -> dict:
        ui_payload = self.state_manager.handle_command(command, payload)
        save_session(self.session)
        save_settings(self.settings)
        return ui_payload
