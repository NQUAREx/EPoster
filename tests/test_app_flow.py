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
    monkeypatch.chdir(tmp_path)
    return AppController()


def test_initial_state_is_base(isolated_app):
    payload = isolated_app.render()
    assert payload["view"] == "base_state"
    assert "today_task" in payload


def test_day_review_scores_and_moves_to_base(isolated_app):
    app = isolated_app
    app.dispatch("open_day_review")

    for _ in app.session.children:
        payload = app.dispatch("score_3")

    assert payload["view"] == "base_state"
    assert app.session.days[1].closed is True
    assert app.session.current_day == 2


def test_map_navigation_and_open_selected_day(isolated_app):
    app = isolated_app
    app.dispatch("open_tasks_map")
    app.dispatch("next")
    app.dispatch("prev")
    payload = app.dispatch("ok")
    assert payload["view"] == "task_info_state"
