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


def test_full_day_flow_and_celebration_command(isolated_app):
    app = isolated_app

    assert app.render()["view"] in {"day_review", "celebration"}

    app.dispatch("open_map")
    payload = app.dispatch("set_score", {"child": app.session.children[0], "score": 3})
    assert payload["view"] == "task_map"

    payload = app.dispatch("finish_day")
    assert payload["view"] == "summary"
    assert app.session.days[app.session.current_day].closed is True

    payload = app.dispatch(app.settings.secret_celebration_command)
    assert payload["view"] == "celebration"


def test_settings_update(isolated_app):
    app = isolated_app
    payload = app.dispatch("open_settings")
    assert payload["view"] == "settings"

    app.dispatch("set_language", {"language": "en"})
    payload = app.dispatch("set_secret_command", {"secret": "party"})
    assert payload["language"] == "en"
    assert payload["secret_celebration_command"] == "party"
