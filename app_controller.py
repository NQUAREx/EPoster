from __future__ import annotations

from datetime import date
import json
import time

from command_router import CommandEvent, CommandRouter
from hardware.ambilight import AmbilightConfig, AmbilightController
from hardware.cursor import move_cursor_to_bottom_right
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
    def __init__(self) -> None:
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
        self._ambilight = self._create_ambilight_controller()
        self._session_snapshot = self._snapshot_session()
        self._settings_snapshot = self._snapshot_settings()
        self._sync_ramadan_day()
        self._init_cursor_position()

    def _create_ambilight_controller(self) -> AmbilightController:
        config = AmbilightConfig(
            enabled=self.settings.ambilight_enabled,
            gpio_pin=self.settings.ambilight_gpio_pin,
            led_count=self.settings.ambilight_led_count,
            brightness=self.settings.ambilight_brightness,
            color_order=self.settings.ambilight_order,
        )
        try:
            return AmbilightController(config)
        except Exception:
            safe_config = AmbilightConfig(
                enabled=False,
                gpio_pin=config.gpio_pin,
                led_count=config.led_count,
                brightness=config.brightness,
                color_order=config.color_order,
            )
            return AmbilightController(safe_config)

    @staticmethod
    def _init_cursor_position() -> None:
        try:
            move_cursor_to_bottom_right()
        except Exception:
            return

    @staticmethod
    def _json_dump(payload: dict) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

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

    def _wake_is_active(self) -> bool:
        return time.monotonic() < self._wake_active_until

    def mark_wake_detected(self, duration_seconds: float = 6.0) -> None:
        self._wake_active_until = max(self._wake_active_until, time.monotonic() + duration_seconds)
        self._ambilight.trigger_wake_effect(duration_seconds)

    def render(self) -> dict:
        self._sync_ramadan_day()
        ui_payload = self.state_manager.show()
        ui_payload["wake_active"] = self._wake_is_active()
        self._save_session_if_changed()
        return ui_payload

    def dispatch(self, command: str, payload: dict | None = None) -> dict:
        self._sync_ramadan_day()
        event = self.command_router.normalize_event(CommandEvent(command=command, payload=payload))
        ui_payload = self.state_manager.handle_command(event.command, event.payload)
        ui_payload["command_source"] = event.source
        ui_payload["wake_active"] = event.wake_word_detected
        self._save_session_if_changed()
        self._save_settings_if_changed()
        return ui_payload

    def ambilight_config(self) -> dict:
        effect_status = self._ambilight.effect_status()
        return {
            "enabled": self.settings.ambilight_enabled,
            "led_count": self.settings.ambilight_led_count,
            "effect": effect_status["current"],
            "effects": effect_status["available"],
        }

    def set_ambilight_effect(self, effect_name: str) -> bool:
        return self._ambilight.set_effect_mode(effect_name)

    def apply_ambilight_frame(self, edge_colors: dict, viewport: dict | None = None) -> int:
        return self._ambilight.apply_frame(edge_colors=edge_colors, viewport=viewport)

    def shutdown(self) -> None:
        self._ambilight.shutdown()

    def dispatch_event(self, event: CommandEvent) -> dict:
        self._sync_ramadan_day()
        normalized = self.command_router.normalize_event(event)
        if normalized.wake_word_detected:
            self.mark_wake_detected()

        if normalized.command.startswith("ambilight_effect_"):
            effect_name = normalized.command.removeprefix("ambilight_effect_")
            self.set_ambilight_effect(effect_name)

        ui_payload = self.state_manager.handle_command(normalized.command, normalized.payload)
        ui_payload["command_source"] = normalized.source
        ui_payload["wake_active"] = self._wake_is_active()
        self._save_session_if_changed()
        self._save_settings_if_changed()
        return ui_payload
