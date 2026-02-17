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


def test_finish_day_blocked_until_all_children_scored(isolated_app):
    app = isolated_app
    app.dispatch("open_map")

    payload = app.dispatch("finish_day")
    assert payload["view"] == "task_map"
    assert payload["can_close_day"] is False

    for child in app.session.children:
        payload = app.dispatch("set_score", {"child": child, "score": 3})
    assert payload["can_close_day"] is True

    payload = app.dispatch("finish_day")
    assert payload["view"] == "summary"
    assert app.session.days[app.session.current_day].closed is True


def test_score_range_0_to_3(isolated_app):
    app = isolated_app
    app.dispatch("open_map")

    payload = app.dispatch("set_score", {"child": app.session.children[0], "score": 5})
    assert payload["scores"][app.session.children[0]] is None

    payload = app.dispatch("set_score", {"child": app.session.children[0], "score": 2})
    assert payload["scores"][app.session.children[0]] == 2


def test_settings_and_secret_command(isolated_app):
    app = isolated_app
    payload = app.dispatch("open_settings")
    assert payload["view"] == "settings"

    app.dispatch("set_secret_command", {"secret": "party"})
    payload = app.dispatch("party")
    assert payload["view"] == "celebration"
