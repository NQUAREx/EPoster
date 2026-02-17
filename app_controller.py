from __future__ import annotations

from command_router import CommandEvent, CommandRouter
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
        self.command_router = CommandRouter()
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

    def _reload_runtime_data(self) -> None:
        self.tasks = load_tasks()
        self.prayer_times = load_prayer_times()
        self.state_manager.refresh_data(self.tasks, self.prayer_times)

    def render(self) -> dict:
        self._reload_runtime_data()
        ui_payload = self.state_manager.show()
        ui_payload["wake_active"] = False
        save_session(self.session)
        return ui_payload

    def dispatch(self, command: str, payload: dict | None = None) -> dict:
        self._reload_runtime_data()
        event = self.command_router.normalize_event(CommandEvent(command=command, payload=payload))
        ui_payload = self.state_manager.handle_command(event.command, event.payload)
        ui_payload["command_source"] = event.source
        ui_payload["wake_active"] = event.wake_word_detected
        save_session(self.session)
        save_settings(self.settings)
        return ui_payload

    def dispatch_event(self, event: CommandEvent) -> dict:
        self._reload_runtime_data()
        normalized = self.command_router.normalize_event(event)
        ui_payload = self.state_manager.handle_command(normalized.command, normalized.payload)
        ui_payload["command_source"] = normalized.source
        ui_payload["wake_active"] = normalized.wake_word_detected
        save_session(self.session)
        save_settings(self.settings)
        return ui_payload
