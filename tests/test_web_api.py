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
    monkeypatch.setenv("EPOSTER_DATA_DIR", str(tmp_path / "data"))
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


def test_command_alias_transition(client):
    response = client.post("/api/command", json={"command": "open_map"})
    assert response.status_code == 200
    assert response.json()["state"] == "tasks_map_state"


def test_wake_endpoint(client):
    response = client.post("/api/wake", json={"source": "voice"})
    assert response.status_code == 200
    assert response.json()["view_model"]["wake_active"] is True


def test_command_validation(client):
    response = client.post("/api/command", json={"command": "  "})
    assert response.status_code == 400


def test_wake_state_persists_for_polling(client):
    wake_response = client.post("/api/wake", json={"source": "voice"})
    assert wake_response.status_code == 200

    state_response = client.get("/api/state")
    assert state_response.status_code == 200
    assert state_response.json()["view_model"]["wake_active"] is True


def test_websocket_pushes_state_updates(client):
    with client.websocket_connect("/ws/state") as ws:
        initial_payload = ws.receive_json()
        assert initial_payload["state"] == "base_state"

        command_response = client.post("/api/command", json={"command": "open_tasks_map"})
        assert command_response.status_code == 200

        pushed_payload = ws.receive_json()
        assert pushed_payload["state"] == "tasks_map_state"
        assert len(pushed_payload["view_model"]["circles"]) == 30
