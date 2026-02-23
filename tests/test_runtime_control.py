from __future__ import annotations

from datetime import datetime

from services.runtime_control import RuntimeControl
from states.base_screen_state import BaseScreenState
from models import Day, PrayerTimes, Session, Task


def test_runtime_control_time_acceleration_advances_virtual_clock() -> None:
    control = RuntimeControl()
    control.start()
    before = control.runtime_now()
    control.start_time_acceleration(3600.0)
    after = control.runtime_now()

    assert after >= before
    assert control.status()["time_multiplier"] == 3600.0


def test_base_state_uses_runtime_prayer_overrides() -> None:
    fixed_now = datetime(2026, 2, 23, 12, 0, 0)
    state = BaseScreenState(
        session=Session(current_day=1, celebration_mode=False, children=[], days={1: Day()}),
        tasks=[Task(day=1, text="task", type="обычное")],
        prayer_times={
            "2026-02-22": PrayerTimes(fajr="04:48", maghrib="17:02"),
            "2026-02-23": PrayerTimes(fajr="04:46", maghrib="17:04"),
            "2026-02-24": PrayerTimes(fajr="04:44", maghrib="17:06"),
        },
        now_provider=lambda: fixed_now,
        prayer_overrides_provider=lambda: {"suhoor": "06:00", "iftar": "20:00"},
    )

    payload = state._times()

    assert payload["suhoor"] == "06:00"
    assert payload["iftar"] == "20:00"
