from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List

from models import AppSettings, Day, Session, Task

DATA_DIR = Path("data")
SESSION_FILE = DATA_DIR / "session.json"
TASKS_FILE = DATA_DIR / "tasks.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
CHILDREN_FILE = DATA_DIR / "children.json"


def _build_empty_scores(children: list[str]) -> dict[str, int | None]:
    return {child: None for child in children}


def _build_review_order(children: list[str]) -> list[str]:
    order = list(children)
    random.shuffle(order)
    return order


def load_children() -> list[str]:
    if not CHILDREN_FILE.exists():
        raise FileNotFoundError(f"{CHILDREN_FILE} не найден")
    with CHILDREN_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list) or not all(isinstance(i, str) and i.strip() for i in data):
        raise ValueError("children.json должен содержать массив строк")
    return [item.strip() for item in data]


def _normalize_session(session: Session) -> Session:
    for day in session.days.values():
        for child in session.children:
            day.scores.setdefault(child, None)

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
    if not SESSION_FILE.exists():
        return None
    with SESSION_FILE.open("r", encoding="utf-8") as file:
        return _normalize_session(Session.from_dict(json.load(file)))


def save_session(session: Session) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with SESSION_FILE.open("w", encoding="utf-8") as file:
        json.dump(session.to_dict(), file, ensure_ascii=False, indent=2)


def load_settings() -> AppSettings:
    if not SETTINGS_FILE.exists():
        raise FileNotFoundError(f"{SETTINGS_FILE} не найден")
    with SETTINGS_FILE.open("r", encoding="utf-8") as file:
        return AppSettings.from_dict(json.load(file))


def save_settings(settings: AppSettings) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with SETTINGS_FILE.open("w", encoding="utf-8") as file:
        json.dump(settings.to_dict(), file, ensure_ascii=False, indent=2)


def load_tasks() -> List[Task]:
    if not TASKS_FILE.exists():
        raise FileNotFoundError(f"{TASKS_FILE} не найден")

    with TASKS_FILE.open("r", encoding="utf-8") as file:
        tasks_data = json.load(file)

    tasks = [Task.from_dict(item) for item in tasks_data]
    if len(tasks) != 30:
        raise ValueError("tasks.json должен содержать 30 заданий")

    expected_days = set(range(1, 31))
    real_days = {task.day for task in tasks}
    if real_days != expected_days:
        raise ValueError("tasks.json должен содержать задания для дней 1..30")

    return sorted(tasks, key=lambda task: task.day)


def create_session(children: List[str]) -> Session:
    days = {
        i + 1: Day(scores=_build_empty_scores(children), closed=False, review_order=_build_review_order(children), review_index=0)
        for i in range(30)
    }
    session = Session(current_day=1, celebration_mode=False, children=children, days=days)
    save_session(session)
    return session


def is_session_completed(session: Session) -> bool:
    return session.celebration_mode and session.all_days_closed()
