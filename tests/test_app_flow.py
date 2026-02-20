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
    start_day = app.session.current_day
    app.dispatch("open_day_review")

    for _ in app.session.children:
        payload = app.dispatch("score_3")

    assert payload["view"] == "base_state"
    assert app.session.days[start_day].closed is True
    assert app.session.current_day == start_day


def test_map_navigation_and_open_selected_day(isolated_app):
    app = isolated_app
    app.dispatch("open_tasks_map")
    app.dispatch("next")
    app.dispatch("prev")
    payload = app.dispatch("ok")
    assert payload["view"] == "task_info_state"


def test_map_shows_warning_for_far_future_day(isolated_app):
    app = isolated_app
    app.dispatch("open_tasks_map")
    for _ in range(6):
        app.dispatch("next")
    payload = app.dispatch("ok")
    assert payload["view"] == "tasks_map_state"
    assert payload["warning"] == "Задание открыть нельзя!"


def test_map_allows_opening_closed_day(isolated_app):
    app = isolated_app
    current_day = app.session.current_day
    app.session.days[current_day].closed = True
    app.dispatch("open_tasks_map")
    payload = app.dispatch("ok")
    assert payload["view"] == "task_info_state"


def test_session_current_day_comes_from_settings(tmp_path, monkeypatch):
    source_data = REPO_ROOT / "data"
    shutil.copytree(source_data, tmp_path / "data")
    monkeypatch.setenv("EPOSTER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)

    settings_file = tmp_path / "data" / "settings.json"
    settings_payload = json.loads(settings_file.read_text(encoding="utf-8"))
    settings_payload["ramadan_day"] = 10
    settings_payload["ramadan_day_updated_on"] = date.today().isoformat()
    settings_file.write_text(json.dumps(settings_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    app = AppController()
    assert app.session.current_day == 10


def test_ramadan_day_rolls_over_at_midnight(tmp_path, monkeypatch):
    source_data = REPO_ROOT / "data"
    shutil.copytree(source_data, tmp_path / "data")
    monkeypatch.setenv("EPOSTER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)

    settings_file = tmp_path / "data" / "settings.json"
    yesterday = date.fromordinal(date.today().toordinal() - 1)
    settings_payload = json.loads(settings_file.read_text(encoding="utf-8"))
    settings_payload["ramadan_day"] = 7
    settings_payload["ramadan_day_updated_on"] = yesterday.isoformat()
    settings_file.write_text(json.dumps(settings_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    app = AppController()
    assert app.settings.ramadan_day == 8
    assert app.session.current_day == 8




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
