from __future__ import annotations

from datetime import date

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

        children = load_children()
        session = load_session()
        if session is None:
            session = create_session(children)

        self.session = session
        self.state_manager = StateManager(session, self.tasks, self.settings, self.prayer_times)
        self._sync_ramadan_day()

    def _sync_ramadan_day(self) -> None:
        today = date.today()
        today_str = today.isoformat()
        saved_date = self.settings.ramadan_day_updated_on

        if not saved_date:
            self.settings.ramadan_day_updated_on = today_str
            settings_changed = True
        else:
            settings_changed = False
            if saved_date != today_str:
                try:
                    previous = date.fromisoformat(saved_date)
                    days_passed = max(0, (today - previous).days)
                except ValueError:
                    days_passed = 0
                self.settings.ramadan_day = min(30, max(1, self.settings.ramadan_day + days_passed))
                self.settings.ramadan_day_updated_on = today_str
                settings_changed = True

        current_day = min(30, max(1, int(self.settings.ramadan_day)))
        if self.settings.ramadan_day != current_day:
            self.settings.ramadan_day = current_day
            settings_changed = True

        session_changed = False
        if self.session.current_day != current_day:
            self.session.current_day = current_day
            session_changed = True
        if self.session.selected_day < 1 or self.session.selected_day > 30:
            self.session.selected_day = current_day
            session_changed = True

        if settings_changed:
            save_settings(self.settings)
        if session_changed:
            save_session(self.session)

    def _reload_runtime_data(self) -> None:
        self.tasks = load_tasks()
        self.prayer_times = load_prayer_times()
        self.state_manager.refresh_data(self.tasks, self.prayer_times)

    def render(self) -> dict:
        self._reload_runtime_data()
        self._sync_ramadan_day()
        ui_payload = self.state_manager.show()
        ui_payload["wake_active"] = False
        save_session(self.session)
        return ui_payload

    def dispatch(self, command: str, payload: dict | None = None) -> dict:
        self._reload_runtime_data()
        self._sync_ramadan_day()
        event = self.command_router.normalize_event(CommandEvent(command=command, payload=payload))
        ui_payload = self.state_manager.handle_command(event.command, event.payload)
        ui_payload["command_source"] = event.source
        ui_payload["wake_active"] = event.wake_word_detected
        save_session(self.session)
        save_settings(self.settings)
        return ui_payload

    def dispatch_event(self, event: CommandEvent) -> dict:
        self._reload_runtime_data()
        self._sync_ramadan_day()
        normalized = self.command_router.normalize_event(event)
        ui_payload = self.state_manager.handle_command(normalized.command, normalized.payload)
        ui_payload["command_source"] = normalized.source
        ui_payload["wake_active"] = normalized.wake_word_detected
        save_session(self.session)
        save_settings(self.settings)
        return ui_payload
