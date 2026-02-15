from __future__ import annotations

import json
from pathlib import Path
from typing import List

from models import Day, Session

DATA_DIR = Path("data")
SESSION_FILE = DATA_DIR / "session.json"
TASKS_FILE = DATA_DIR / "tasks.json"


def load_session() -> Session | None:
    if not SESSION_FILE.exists():
        return None
    with SESSION_FILE.open("r", encoding="utf-8") as file:
        return Session.from_dict(json.load(file))


def save_session(session: Session) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with SESSION_FILE.open("w", encoding="utf-8") as file:
        json.dump(session.to_dict(), file, ensure_ascii=False, indent=2)


def create_session(children: List[str]) -> Session:
    if not TASKS_FILE.exists():
        raise FileNotFoundError(f"{TASKS_FILE} не найден")

    with TASKS_FILE.open("r", encoding="utf-8") as file:
        tasks_data = json.load(file)

    if len(tasks_data) != 30:
        raise ValueError("tasks.json должен содержать 30 заданий")

    days = {i + 1: Day() for i in range(30)}
    session = Session(current_day=1, celebration_mode=False, children=children, days=days)
    save_session(session)
    return session


def is_session_completed(session: Session) -> bool:
    return session.celebration_mode and session.all_days_closed()
