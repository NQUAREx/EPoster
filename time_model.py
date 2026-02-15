from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Dict

PRAYER_FILE = Path("data/prayer_times_2026.json")


def get_prayer_times(target_date: date) -> Dict[str, str]:
    """Returns prayer times for a date from file storage."""

    with PRAYER_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    date_key = target_date.isoformat()
    if date_key not in data:
        raise KeyError(f"Для даты {date_key} не найдено расписание намазов")

    return data[date_key]
