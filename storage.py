from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Dict, List

from models import AppSettings, Day, PrayerTimes, Session, Task
from hardware.color_profile import ColorProfile

BASE_DIR = Path(__file__).resolve().parent
LEGACY_DATA_DIR = BASE_DIR / "data"
DEFAULT_DATA_DIR = LEGACY_DATA_DIR
DEFAULT_CHILDREN = ["Камила", "Самир", "Амалия", "Сулейман", "Айя"]


def _data_dir() -> Path:
    return Path(os.getenv("EPOSTER_DATA_DIR", str(DEFAULT_DATA_DIR))).resolve()


def _session_file() -> Path:
    return _data_dir() / "session.json"


def _tasks_file() -> Path:
    return _data_dir() / "tasks.json"


def _settings_file() -> Path:
    return _data_dir() / "settings.json"


def _prayer_times_file() -> Path:
    return _data_dir() / "prayer_times_2026.json"


def _children_file() -> Path:
    return _data_dir() / "children.json"


def _resolve_profile_file(file_name: str) -> Path:
    safe_name = str(file_name or "ambilight_color_profile.json").strip() or "ambilight_color_profile.json"
    return (_data_dir() / safe_name).resolve()


def _build_empty_scores(children: list[str]) -> dict[str, int | None]:
    return {child: None for child in children}


def _build_review_order(children: list[str]) -> list[str]:
    order = list(children)
    random.shuffle(order)
    return order


def load_children() -> list[str]:
    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    children_file = _children_file()

    if children_file.exists():
        with children_file.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        if isinstance(payload, list):
            normalized = [name.strip() for name in payload if isinstance(name, str) and name.strip()]
            if normalized:
                return normalized

    children = list(DEFAULT_CHILDREN)
    with children_file.open("w", encoding="utf-8") as file:
        json.dump(children, file, ensure_ascii=False, indent=2)
    return children


def _normalize_session(session: Session, children: list[str]) -> Session:
    session.children = list(children)
    session.current_day = min(30, max(1, int(session.current_day or 1)))
    if session.selected_day < 1 or session.selected_day > 30:
        session.selected_day = session.current_day
    if not session.days:
        session.days = {i + 1: Day(scores=_build_empty_scores(session.children)) for i in range(30)}
    for day_num in range(1, 31):
        if day_num not in session.days:
            session.days[day_num] = Day(scores=_build_empty_scores(session.children))

    for day in session.days.values():
        day.viewed = bool(day.viewed)
        day.scores = {child: day.scores.get(child) for child in session.children}

        day.review_order = [child for child in day.review_order if child in session.children]
        for child in session.children:
            if child not in day.review_order:
                day.review_order.append(child)

        if not day.review_order:
            day.review_order = _build_review_order(session.children)

        if day.review_index < 0:
            day.review_index = 0
        if day.review_index > len(day.review_order):
            day.review_index = len(day.review_order)

    return session


def load_session() -> Session | None:
    session_file = _session_file()
    if not session_file.exists():
        return None
    children = load_children()
    with session_file.open("r", encoding="utf-8") as file:
        return _normalize_session(Session.from_dict(json.load(file)), children)


def migrate_legacy_data_if_needed() -> None:
    """Сохраняем совместимость со старым внешним каталогом ~/.eposter/data.

    Текущий источник истины — data/ внутри репозитория.
    При первом запуске, если найдено старое состояние, переносим только session.json.
    """
    if os.getenv("EPOSTER_DATA_DIR"):
        return

    target_dir = _data_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    old_external_dir = Path.home() / ".eposter" / "data"
    source = old_external_dir / "session.json"
    target = target_dir / "session.json"
    if source.exists() and not target.exists():
        with source.open("rb") as src, target.open("wb") as dst:
            dst.write(src.read())


def save_session(session: Session) -> None:
    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    with _session_file().open("w", encoding="utf-8") as file:
        json.dump(session.to_dict(), file, ensure_ascii=False, indent=2)


def load_settings() -> AppSettings:
    with _settings_file().open("r", encoding="utf-8") as file:
        return AppSettings.from_dict(json.load(file))


def save_settings(settings: AppSettings) -> None:
    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    with _settings_file().open("w", encoding="utf-8") as file:
        json.dump(settings.to_dict(), file, ensure_ascii=False, indent=2)


def load_color_profile(file_name: str) -> ColorProfile:
    profile_file = _resolve_profile_file(file_name)
    if not profile_file.exists():
        return ColorProfile.identity()
    with profile_file.open("r", encoding="utf-8") as file:
        return ColorProfile.from_dict(json.load(file))


def save_color_profile(file_name: str, profile: ColorProfile) -> None:
    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    profile_file = _resolve_profile_file(file_name)
    with profile_file.open("w", encoding="utf-8") as file:
        json.dump(profile.to_dict(), file, ensure_ascii=False, indent=2)


def load_tasks() -> List[Task]:
    with _tasks_file().open("r", encoding="utf-8") as file:
        tasks = [Task.from_dict(item) for item in json.load(file)]
    return sorted(tasks, key=lambda task: task.day)


def load_prayer_times() -> Dict[str, PrayerTimes]:
    with _prayer_times_file().open("r", encoding="utf-8") as file:
        data = json.load(file)
    return {date: PrayerTimes.from_dict(times) for date, times in data.items()}


def create_session(children: List[str]) -> Session:
    days = {i + 1: Day(scores=_build_empty_scores(children)) for i in range(30)}
    session = Session(current_day=1, selected_day=1, celebration_mode=False, children=children, days=days)
    save_session(session)
    return session
