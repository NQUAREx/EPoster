from pathlib import Path
import shutil
import sys

import pytest

pytest.importorskip("flask")

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    shutil.copytree(REPO_ROOT / "data", tmp_path / "data")
    shutil.copytree(REPO_ROOT / "ui", tmp_path / "ui")
    monkeypatch.chdir(tmp_path)

    from web_app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_get_state(client):
    response = client.get("/api/state")
    assert response.status_code == 200
    assert response.get_json()["state"] == "base"


def test_command_transition(client):
    response = client.post("/api/command", json={"command": "open_map"})
    assert response.status_code == 200
    assert response.get_json()["state"] == "task_map"


def test_command_validation(client):
    response = client.post("/api/command", json={"payload": {"x": 1}})
    assert response.status_code == 400
