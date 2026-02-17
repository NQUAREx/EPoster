from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from models import AppSettings, Day, PrayerTimes, Session, Task

DATA_DIR = Path("data")
SESSION_FILE = DATA_DIR / "session.json"
TASKS_FILE = DATA_DIR / "tasks.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
PRAYER_TIMES_FILE = DATA_DIR / "prayer_times_2026.json"


def _build_empty_scores(children: list[str]) -> dict[str, int | None]:
    return {child: None for child in children}


def _normalize_session(session: Session) -> Session:
    if session.selected_day < 1 or session.selected_day > 30:
        session.selected_day = session.current_day
    for day in session.days.values():
        for child in session.children:
            day.scores.setdefault(child, None)
    return session


def load_session() -> Session | None:
    if not SESSION_FILE.exists():
        return None
    with SESSION_FILE.open("r", encoding="utf-8") as file:
        return _normalize_session(Session.from_dict(json.load(file)))


def save_session(session: Session) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with SESSION_FILE.open("w", encoding="utf-8") as file:
        json.dump(session.to_dict(), file, ensure_ascii=False, indent=2)


def load_settings() -> AppSettings:
    with SETTINGS_FILE.open("r", encoding="utf-8") as file:
        return AppSettings.from_dict(json.load(file))


def save_settings(settings: AppSettings) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with SETTINGS_FILE.open("w", encoding="utf-8") as file:
        json.dump(settings.to_dict(), file, ensure_ascii=False, indent=2)


def load_tasks() -> List[Task]:
    with TASKS_FILE.open("r", encoding="utf-8") as file:
        tasks = [Task.from_dict(item) for item in json.load(file)]
    return sorted(tasks, key=lambda task: task.day)


def load_prayer_times() -> Dict[str, PrayerTimes]:
    with PRAYER_TIMES_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return {date: PrayerTimes.from_dict(times) for date, times in data.items()}


def create_session(children: List[str]) -> Session:
    days = {i + 1: Day(scores=_build_empty_scores(children)) for i in range(30)}
    session = Session(current_day=1, selected_day=1, celebration_mode=False, children=children, days=days)
    save_session(session)
    return session
