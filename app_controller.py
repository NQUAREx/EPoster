from __future__ import annotations

from datetime import date
import json
import os
import time
from pathlib import Path

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
        self._tasks_mtime = self._safe_mtime(self._runtime_data_file("tasks.json"))
        self._prayer_times_mtime = self._safe_mtime(self._runtime_data_file("prayer_times_2026.json"))
        self._session_snapshot = self._snapshot_session()
        self._settings_snapshot = self._snapshot_settings()
        self._sync_ramadan_day()

    @staticmethod
    def _safe_mtime(path: Path) -> float | None:
        try:
            return path.stat().st_mtime
        except OSError:
            return None

    @staticmethod
    def _json_dump(payload: dict) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _runtime_data_file(name: str) -> Path:
        data_dir = Path(os.getenv("EPOSTER_DATA_DIR", str(Path(__file__).resolve().parent / "data"))).resolve()
        return data_dir / name

    def _snapshot_session(self) -> str:
        return self._json_dump(self.session.to_dict())

    def _snapshot_settings(self) -> str:
        return self._json_dump(self.settings.to_dict())

    def _save_session_if_changed(self) -> None:
        snapshot = self._snapshot_session()
        if snapshot == self._session_snapshot:
            return
        save_session(self.session)
        self._session_snapshot = snapshot

    def _save_settings_if_changed(self) -> None:
        snapshot = self._snapshot_settings()
        if snapshot == self._settings_snapshot:
            return
        save_settings(self.settings)
        self._settings_snapshot = snapshot


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
            self._save_settings_if_changed()
        if session_changed:
            self._save_session_if_changed()

    def _reload_runtime_data(self) -> None:
        tasks_path = self._runtime_data_file("tasks.json")
        prayer_times_path = self._runtime_data_file("prayer_times_2026.json")

        tasks_mtime = self._safe_mtime(tasks_path)
        prayer_times_mtime = self._safe_mtime(prayer_times_path)

        should_refresh_tasks = tasks_mtime != self._tasks_mtime
        should_refresh_prayer_times = prayer_times_mtime != self._prayer_times_mtime

        if should_refresh_tasks:
            self.tasks = load_tasks()
            self._tasks_mtime = tasks_mtime
        if should_refresh_prayer_times:
            self.prayer_times = load_prayer_times()
            self._prayer_times_mtime = prayer_times_mtime

        if should_refresh_tasks or should_refresh_prayer_times:
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
        self._save_session_if_changed()
        return ui_payload

    def dispatch(self, command: str, payload: dict | None = None) -> dict:
        self._reload_runtime_data()
        self._sync_ramadan_day()
        event = self.command_router.normalize_event(CommandEvent(command=command, payload=payload))
        ui_payload = self.state_manager.handle_command(event.command, event.payload)
        ui_payload["command_source"] = event.source
        ui_payload["wake_active"] = event.wake_word_detected
        self._save_session_if_changed()
        self._save_settings_if_changed()
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
        self._save_session_if_changed()
        self._save_settings_if_changed()
        return ui_payload
