from __future__ import annotations

from datetime import date
import time

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
        self._wake_active_until = 0.0
        self._sync_ramadan_day()


    @staticmethod
    def _real_ramadan_day(today: date) -> int:
        ramadan_start = date(today.year, 2, 18)
        elapsed_days = (today - ramadan_start).days
        return min(30, max(1, elapsed_days + 1))

    def _sync_ramadan_day(self) -> None:
        today = date.today()
        today_str = today.isoformat()
        real_ramadan_day = self._real_ramadan_day(today)

        settings_changed = False
        if self.settings.ramadan_day != real_ramadan_day:
            self.settings.ramadan_day = real_ramadan_day
            settings_changed = True
        if self.settings.ramadan_day_updated_on != today_str:
            self.settings.ramadan_day_updated_on = today_str
            settings_changed = True

        session_changed = False
        if self.session.current_day != real_ramadan_day:
            self.session.current_day = real_ramadan_day
            session_changed = True
        if self.session.selected_day < 1 or self.session.selected_day > 30:
            self.session.selected_day = self.session.first_open_task_day()
            session_changed = True

        if settings_changed:
            save_settings(self.settings)
        if session_changed:
            save_session(self.session)

    def _reload_runtime_data(self) -> None:
        self.tasks = load_tasks()
        self.prayer_times = load_prayer_times()
        self.state_manager.refresh_data(self.tasks, self.prayer_times)

    def _wake_is_active(self) -> bool:
        return time.monotonic() < self._wake_active_until

    def mark_wake_detected(self, duration_seconds: float = 6.0) -> None:
        self._wake_active_until = max(self._wake_active_until, time.monotonic() + duration_seconds)

    def render(self) -> dict:
        self._reload_runtime_data()
        self._sync_ramadan_day()
        ui_payload = self.state_manager.show()
        ui_payload["wake_active"] = self._wake_is_active()
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
        if normalized.wake_word_detected:
            self.mark_wake_detected()

        ui_payload = self.state_manager.handle_command(normalized.command, normalized.payload)
        ui_payload["command_source"] = normalized.source
        ui_payload["wake_active"] = self._wake_is_active()
        save_session(self.session)
        save_settings(self.settings)
        return ui_payload
