from __future__ import annotations

from datetime import datetime

import pytest

from models import Day, PrayerTimes, Session, Task
from states.base_screen_state import BaseScreenState


def test_palette_progress_remap_split_points():
    assert BaseScreenState._remap_palette_progress(0.0) == 0.0
    assert BaseScreenState._remap_palette_progress(0.9) == 0.1
    assert BaseScreenState._remap_palette_progress(1.0) == 1.0


def test_palette_progress_remap_slow_then_fast():
    early = BaseScreenState._remap_palette_progress(0.4)
    late = BaseScreenState._remap_palette_progress(0.95)

    assert early == pytest.approx(0.0444444444)
    assert late == pytest.approx(0.55)


def test_night_progress_uses_yesterday_iftar_schedule(monkeypatch):
    fake_now = datetime(2025, 3, 20, 3, 0, 0)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fake_now

    monkeypatch.setattr("states.base_screen_state.datetime", FrozenDateTime)

    session = Session(current_day=1, celebration_mode=False, children=[], days={1: Day()})
    state = BaseScreenState(
        session=session,
        tasks=[Task(day=1, text="task", type="обычное")],
        prayer_times={
            "2025-03-19": PrayerTimes(fajr="05:00", maghrib="21:00"),
            "2025-03-20": PrayerTimes(fajr="05:00", maghrib="18:00"),
            "2025-03-21": PrayerTimes(fajr="05:00", maghrib="18:00"),
        },
    )

    payload = state._times()

    assert payload["phase"] == "night"
    assert payload["next"] == "сухура"
    assert payload["countdown"].startswith("02:")
    assert payload["phase_progress"] == pytest.approx(0.75, abs=1e-3)
    assert BaseScreenState._remap_palette_progress(payload["phase_progress"]) < 0.2


def test_early_night_shows_iftar_for_today_date_block(monkeypatch):
    fake_now = datetime(2026, 2, 23, 3, 0, 0)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fake_now

    monkeypatch.setattr("states.base_screen_state.datetime", FrozenDateTime)

    session = Session(current_day=1, celebration_mode=False, children=[], days={1: Day()})
    state = BaseScreenState(
        session=session,
        tasks=[Task(day=1, text="task", type="обычное")],
        prayer_times={
            "2026-02-22": PrayerTimes(fajr="04:48", maghrib="17:02"),
            "2026-02-23": PrayerTimes(fajr="04:46", maghrib="17:04"),
            "2026-02-24": PrayerTimes(fajr="04:44", maghrib="17:06"),
        },
    )

    payload = state._times()

    assert payload["next"] == "сухура"
    assert payload["source_date"] == "2026-02-23"
    assert payload["suhoor"] == "04:46"
    assert payload["iftar"] == "17:04"


def test_times_payload_contains_source_date_when_year_differs(monkeypatch):
    fake_now = datetime(2025, 3, 20, 12, 0, 0)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fake_now

    monkeypatch.setattr("states.base_screen_state.datetime", FrozenDateTime)

    session = Session(current_day=1, celebration_mode=False, children=[], days={1: Day()})
    state = BaseScreenState(
        session=session,
        tasks=[Task(day=1, text="task", type="обычное")],
        prayer_times={
            "2026-03-20": PrayerTimes(fajr="05:11", maghrib="18:21"),
            "2026-03-21": PrayerTimes(fajr="05:09", maghrib="18:23"),
        },
    )

    payload = state._times()

    assert payload["source_date"] == "2026-03-20"


def test_prayer_lookup_falls_back_to_nearest_date():
    session = Session(current_day=1, celebration_mode=False, children=[], days={1: Day()})
    state = BaseScreenState(
        session=session,
        tasks=[Task(day=1, text="task", type="обычное")],
        prayer_times={
            "2025-03-10": PrayerTimes(fajr="05:10", maghrib="18:10"),
            "2025-03-30": PrayerTimes(fajr="04:50", maghrib="18:30"),
        },
    )

    nearest = state._prayer_times_for_date(datetime(2025, 3, 29).date())

    assert nearest.fajr == "04:50"


def test_prayer_lookup_matches_month_and_day_when_year_differs():
    session = Session(current_day=1, celebration_mode=False, children=[], days={1: Day()})
    state = BaseScreenState(
        session=session,
        tasks=[Task(day=1, text="task", type="обычное")],
        prayer_times={
            "2026-03-20": PrayerTimes(fajr="05:11", maghrib="18:21"),
            "2026-03-21": PrayerTimes(fajr="05:09", maghrib="18:23"),
        },
    )

    matched = state._prayer_times_for_date(datetime(2025, 3, 20).date())

    assert matched.fajr == "05:11"
    assert matched.maghrib == "18:21"
