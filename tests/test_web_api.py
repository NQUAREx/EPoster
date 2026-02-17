from pathlib import Path
import shutil
import sys

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    shutil.copytree(REPO_ROOT / "data", tmp_path / "data")
    shutil.copytree(REPO_ROOT / "ui", tmp_path / "ui")
    monkeypatch.chdir(tmp_path)

    from fastapi.testclient import TestClient
    from web_app import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_get_state(client):
    response = client.get("/api/state")
    assert response.status_code == 200
    assert response.json()["state"] == "base_state"


def test_command_transition(client):
    response = client.post("/api/command", json={"command": "open_tasks_map"})
    assert response.status_code == 200
    assert response.json()["state"] == "tasks_map_state"


def test_command_validation(client):
    response = client.post("/api/command", json={"command": "  "})
    assert response.status_code == 400
