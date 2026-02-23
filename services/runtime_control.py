from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import RLock
from typing import Any


@dataclass
class RuntimeControlState:
    active: bool = False
    started_at: datetime | None = None
    base_virtual_time: datetime | None = None
    time_multiplier: float = 1.0
    suhoor_override: str | None = None
    iftar_override: str | None = None


class RuntimeControl:
    """Runtime test control bridge for temporary in-process overrides."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._state = RuntimeControlState()

    def start(self) -> RuntimeControlState:
        with self._lock:
            now = datetime.now()
            self._state.active = True
            self._state.started_at = now
            self._state.base_virtual_time = now
            self._state.time_multiplier = 1.0
            self._state.suhoor_override = None
            self._state.iftar_override = None
            return self._snapshot()

    def stop(self) -> RuntimeControlState:
        with self._lock:
            self._state = RuntimeControlState()
            return self._snapshot()

    def status(self) -> dict[str, Any]:
        with self._lock:
            now = self._now_locked()
            return {
                "active": self._state.active,
                "virtual_now": now.isoformat(),
                "time_multiplier": self._state.time_multiplier,
                "overrides": {
                    "suhoor": self._state.suhoor_override,
                    "iftar": self._state.iftar_override,
                },
            }

    def set_prayer_overrides(self, suhoor: str, iftar: str) -> RuntimeControlState:
        with self._lock:
            self._state.suhoor_override = suhoor
            self._state.iftar_override = iftar
            return self._snapshot()

    def clear_prayer_overrides(self) -> RuntimeControlState:
        with self._lock:
            self._state.suhoor_override = None
            self._state.iftar_override = None
            return self._snapshot()

    def start_time_acceleration(self, multiplier: float) -> RuntimeControlState:
        with self._lock:
            current_virtual = self._now_locked()
            self._state.base_virtual_time = current_virtual
            self._state.started_at = datetime.now()
            self._state.time_multiplier = max(1.0, multiplier)
            return self._snapshot()

    def stop_time_acceleration(self) -> RuntimeControlState:
        with self._lock:
            current_virtual = self._now_locked()
            self._state.base_virtual_time = current_virtual
            self._state.started_at = datetime.now()
            self._state.time_multiplier = 1.0
            return self._snapshot()

    def runtime_now(self) -> datetime:
        with self._lock:
            return self._now_locked()

    def is_active(self) -> bool:
        with self._lock:
            return self._state.active

    def prayer_overrides(self) -> dict[str, str]:
        with self._lock:
            if not self._state.active:
                return {}
            result: dict[str, str] = {}
            if self._state.suhoor_override:
                result["suhoor"] = self._state.suhoor_override
            if self._state.iftar_override:
                result["iftar"] = self._state.iftar_override
            return result

    def _now_locked(self) -> datetime:
        if not self._state.active:
            return datetime.now()
        if not self._state.base_virtual_time or not self._state.started_at:
            return datetime.now()
        elapsed = datetime.now() - self._state.started_at
        accelerated = elapsed.total_seconds() * self._state.time_multiplier
        return self._state.base_virtual_time + timedelta(seconds=accelerated)

    def _snapshot(self) -> RuntimeControlState:
        return RuntimeControlState(
            active=self._state.active,
            started_at=self._state.started_at,
            base_virtual_time=self._state.base_virtual_time,
            time_multiplier=self._state.time_multiplier,
            suhoor_override=self._state.suhoor_override,
            iftar_override=self._state.iftar_override,
        )
