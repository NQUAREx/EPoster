from pathlib import Path
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
    assert app.session.current_day == min(30, start_day + 1)


def test_map_navigation_and_open_selected_day(isolated_app):
    app = isolated_app
    app.dispatch("open_tasks_map")
    app.dispatch("next")
    app.dispatch("prev")
    payload = app.dispatch("ok")
    assert payload["view"] == "task_info_state"


def test_session_current_day_persists_between_restarts(tmp_path, monkeypatch):
    source_data = REPO_ROOT / "data"
    shutil.copytree(source_data, tmp_path / "data")
    monkeypatch.setenv("EPOSTER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)

    session_file = tmp_path / "data" / "session.json"
    payload = __import__("json").loads(session_file.read_text(encoding="utf-8"))
    payload["current_day"] = 10
    payload["selected_day"] = 10
    session_file.write_text(__import__("json").dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    app = AppController()
    assert app.session.current_day == 10


def test_children_list_is_strict_and_has_no_extra_names(isolated_app):
    app = isolated_app
    assert app.session.children == ["Камила", "Самир", "Амалия", "Сулейман", "Айя"]
    app.dispatch("open_day_review")
    view = app.render()
    assert view["view"] == "day_review_state"
    assert view["child"] in app.session.children
