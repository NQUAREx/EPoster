from datetime import date
from pathlib import Path
import json
import shutil
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))

from app_controller import AppController
from command_router import CommandEvent


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


def test_map_view_contains_task_text_from_tasks_json(tmp_path, monkeypatch):
    source_data = REPO_ROOT / "data"
    shutil.copytree(source_data, tmp_path / "data")
    monkeypatch.setenv("EPOSTER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)

    tasks_file = tmp_path / "data" / "tasks.json"
    tasks_payload = json.loads(tasks_file.read_text(encoding="utf-8"))
    custom_text = "ТЕСТ: текст задания в карте"
    tasks_payload[1]["text"] = custom_text
    tasks_file.write_text(json.dumps(tasks_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    app = AppController()
    app.dispatch("open_tasks_map")

    circles = app.render()["circles"]
    day_two = next(item for item in circles if item["day"] == 2)
    assert day_two["task_text"] == custom_text


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


def test_children_list_loaded_from_json(isolated_app):
    app = isolated_app
    expected_children = json.loads((Path("data") / "children.json").read_text(encoding="utf-8"))
    assert app.session.children == expected_children
    app.dispatch("open_day_review")
    view = app.render()
    assert view["view"] == "day_review_state"
    assert view["child"] in app.session.children


def test_render_does_not_write_session_without_changes(isolated_app, monkeypatch):
    save_calls = 0

    def fake_save_session(_):
        nonlocal save_calls
        save_calls += 1

    monkeypatch.setattr("app_controller.save_session", fake_save_session)

    isolated_app.render()
    isolated_app.render()

    assert save_calls == 0


def test_render_does_not_reload_tasks_when_file_unchanged(isolated_app, monkeypatch):
    load_calls = 0

    def fake_load_tasks():
        nonlocal load_calls
        load_calls += 1
        return isolated_app.tasks

    monkeypatch.setattr("app_controller.load_tasks", fake_load_tasks)

    isolated_app.render()
    isolated_app.render()
    isolated_app.render()

    assert load_calls == 0


def test_existing_children_file_is_not_overwritten(tmp_path, monkeypatch):
    source_data = REPO_ROOT / "data"
    shutil.copytree(source_data, tmp_path / "data")
    monkeypatch.setenv("EPOSTER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)

    children_file = tmp_path / "data" / "children.json"
    expected_children = ["Алия", "Ильяс"]
    children_file.write_text(json.dumps(expected_children, ensure_ascii=False, indent=2), encoding="utf-8")

    app = AppController()

    assert app.session.children == expected_children
    assert json.loads(children_file.read_text(encoding="utf-8")) == expected_children


def test_day_scores_are_restored_from_session_file(tmp_path, monkeypatch):
    source_data = REPO_ROOT / "data"
    shutil.copytree(source_data, tmp_path / "data")
    monkeypatch.setenv("EPOSTER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)

    session_file = tmp_path / "data" / "session.json"
    session_payload = json.loads(session_file.read_text(encoding="utf-8"))
    session_payload["days"]["2"]["scores"] = {"Камила": 3, "Самир": 2}
    session_file.write_text(json.dumps(session_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    app = AppController()

    assert app.session.days[2].scores["Камила"] == 3
    assert app.session.days[2].scores["Самир"] == 2


def test_wake_detection_triggers_ambilight_effect(isolated_app, monkeypatch):
    calls = []

    def fake_trigger(duration_seconds: float = 6.0):
        calls.append(duration_seconds)

    monkeypatch.setattr(isolated_app._ambilight, "trigger_wake_effect", fake_trigger)
    isolated_app.mark_wake_detected()

    assert calls == [6.0]


def test_voice_command_can_switch_ambilight_effect(isolated_app):
    payload = isolated_app.dispatch_event(
        CommandEvent(command="эмбилайт без эффекта", source="voice", wake_word_detected=True)
    )

    assert payload["wake_active"] is True
    assert isolated_app.ambilight_config()["effect"] == "none"
