from datetime import date
from pathlib import Path
import json
import shutil
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))

from app_controller import AppController


@pytest.fixture()
def isolated_app(tmp_path, monkeypatch):
    shutil.copytree(REPO_ROOT / "data", tmp_path / "data")
    monkeypatch.setenv("EPOSTER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)
    return AppController()


def test_initial_state_is_base(isolated_app):
    payload = isolated_app.render()
    assert payload["view"] == "base_state"
    assert "today_task" in payload


def test_day_review_scores_and_moves_to_base(isolated_app):
    app = isolated_app
    app.session.selected_day = 2
    app.dispatch("open_day_review")

    for _ in app.session.children:
        payload = app.dispatch("score_3")

    assert payload["view"] == "base_state"
    assert app.session.days[2].closed is True


def test_map_navigation_and_open_selected_day(isolated_app):
    app = isolated_app
    app.dispatch("open_tasks_map")
    app.dispatch("next")
    app.dispatch("prev")
    payload = app.dispatch("ok")
    assert payload["view"] == "task_info_state"


def test_map_shows_warning_for_locked_day(isolated_app):
    app = isolated_app
    app.dispatch("open_tasks_map")
    for _ in range(6):
        app.dispatch("next")
    payload = app.dispatch("ok")
    assert payload["view"] == "tasks_map_state"
    assert payload["warning"] == "Задание открыть нельзя!"


def test_map_unlocks_tasks_by_last_completed_day(isolated_app):
    app = isolated_app
    app.session.days[4].closed = True
    app.dispatch("open_tasks_map")

    circles = app.render()["circles"]
    status_by_day = {item["day"]: item["status"] for item in circles}

    assert status_by_day[6] == "open"
    assert status_by_day[7] == "locked"


def test_open_day_review_skips_completed_task_and_uses_first_open(isolated_app):
    app = isolated_app
    app.session.days[1].closed = True
    app.session.selected_day = 1

    payload = app.dispatch("open_day_review")
    assert payload["view"] == "day_review_state"
    assert payload["day"] == 2


def test_base_view_falls_back_to_last_open_when_selected_is_locked(isolated_app):
    app = isolated_app
    app.session.selected_day = 20

    payload = app.render()
    assert payload["task_day"] == 2


def test_base_view_falls_back_to_first_open_when_selected_is_completed(isolated_app):
    app = isolated_app
    app.session.days[1].closed = True
    app.session.selected_day = 1

    payload = app.render()
    assert payload["task_day"] == 2


def test_real_ramadan_day_is_based_on_18_february():
    assert AppController._real_ramadan_day(date(2026, 2, 18)) == 1
    assert AppController._real_ramadan_day(date(2026, 2, 22)) == 5


def test_base_view_task_text_comes_from_tasks_json(tmp_path, monkeypatch):
    source_data = REPO_ROOT / "data"
    shutil.copytree(source_data, tmp_path / "data")
    monkeypatch.setenv("EPOSTER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)

    tasks_file = tmp_path / "data" / "tasks.json"
    tasks_payload = json.loads(tasks_file.read_text(encoding="utf-8"))
    custom_text = "ТЕСТ: задание загружено из tasks.json"
    tasks_payload[0]["text"] = custom_text
    tasks_file.write_text(json.dumps(tasks_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    app = AppController()
    payload = app.render()
    assert payload["view"] == "base_state"
    assert payload["today_task"] == custom_text


def test_children_list_is_strict_and_has_no_extra_names(isolated_app):
    app = isolated_app
    assert app.session.children == ["Камила", "Самир", "Амалия", "Сулейман", "Айя"]
    app.dispatch("open_day_review")
    view = app.render()
    assert view["view"] == "day_review_state"
    assert view["child"] in app.session.children
