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


def test_day_review_moves_child_by_child_and_closes_day(isolated_app):
    app = isolated_app
    payload = app.dispatch("start_day_review")
    assert payload["view"] == "day_review"

    order = payload["review_order"]
    for _ in order:
        payload = app.dispatch("set_score", {"score": 3})

    assert payload["view"] == "summary"
    assert app.session.days[app.session.current_day].closed is True


def test_children_loaded_from_separate_file(isolated_app):
    app = isolated_app
    assert app.session.children == ["Камила", "Самир", "Амалия", "Сулейман"]


def test_settings_and_secret_command(isolated_app):
    app = isolated_app
    payload = app.dispatch("open_settings")
    assert payload["view"] == "settings"

    app.dispatch("set_secret_command", {"secret": "party"})
    payload = app.dispatch("party")
    assert payload["view"] == "celebration"
