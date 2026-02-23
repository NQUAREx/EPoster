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
    payload = response.json()
    assert payload["state"] == "base_state"
    assert isinstance(payload.get("app_instance_id"), str) and payload["app_instance_id"]
    assert "background" not in payload["view_model"]


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
        assert isinstance(initial_payload.get("app_instance_id"), str) and initial_payload["app_instance_id"]

        command_response = client.post("/api/command", json={"command": "open_tasks_map"})
        assert command_response.status_code == 200

        pushed_payload = ws.receive_json()
        assert pushed_payload["state"] == "tasks_map_state"
        assert len(pushed_payload["view_model"]["circles"]) == 30




def test_ambilight_config_endpoint(client):
    response = client.get("/api/ambilight/config")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload.get("led_count"), int)
    assert isinstance(payload.get("enabled"), bool)
    assert payload.get("effect") in {"wake_blink", "none"}
    assert isinstance(payload.get("effects"), list)

def test_ambilight_frame_endpoint(client):
    response = client.post(
        "/api/ambilight/frame",
        json={
            "top": [[12, 34, 56]],
            "right": [[1, 2, 3]],
            "bottom": [[9, 9, 9]],
            "left": [[5, 6, 7]],
            "viewport": {"width": 1280, "height": 720},
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["led_count"] > 0


def test_voice_command_switches_ambilight_effect(client):
    response = client.post(
        "/api/command",
        json={"command": "эмбилайт без эффекта", "source": "voice", "wake_word_detected": True},
    )
    assert response.status_code == 200
    assert response.json()["view_model"]["wake_active"] is True

    config = client.get("/api/ambilight/config")
    assert config.status_code == 200
    assert config.json()["effect"] == "none"


def test_calibration_preview_endpoint(client):
    start = client.post("/api/calibration/start")
    assert start.status_code == 200

    preview = client.post("/api/calibration/preview", json={"observed_rgb": [10, 20, 30]})
    assert preview.status_code == 200
    assert preview.json()["ok"] is True


def test_calibration_preview_requires_active_session(client):
    preview = client.post("/api/calibration/preview", json={"observed_rgb": [10, 20, 30]})
    assert preview.status_code == 200
    assert preview.json()["ok"] is False

def test_runtime_console_lock_and_restore(client):
    start = client.post('/api/runtime-test/start')
    assert start.status_code == 200
    assert start.json()['view_model']['active'] is True

    blocked = client.post('/api/command', json={'command': 'open_tasks_map'})
    assert blocked.status_code == 200
    assert blocked.json()['view_model']['command_source'] == 'runtime_lock'

    stop = client.post('/api/runtime-test/stop')
    assert stop.status_code == 200
    assert stop.json()['view_model']['active'] is False

    normal = client.post('/api/command', json={'command': 'open_tasks_map'})
    assert normal.status_code == 200
    assert normal.json()['state'] == 'tasks_map_state'


def test_runtime_prayer_override_endpoint(client):
    client.post('/api/runtime-test/start')

    override = client.post('/api/runtime-test/prayer-override', json={'suhoor': '06:10', 'iftar': '20:20'})
    assert override.status_code == 200
    assert override.json()['view_model']['overrides']['suhoor'] == '06:10'

    state = client.get('/api/state')
    assert state.status_code == 200
    assert state.json()['view_model']['next_prayer']['suhoor'] == '06:10'

    clear = client.post('/api/runtime-test/prayer-override/clear')
    assert clear.status_code == 200
    assert clear.json()['view_model']['overrides']['suhoor'] is None


def test_runtime_time_cycle_exposes_multiplier_in_state(client):
    client.post('/api/runtime-test/start')

    accelerated = client.post('/api/runtime-test/time-cycle/start', json={'hours_per_second': 1.0})
    assert accelerated.status_code == 200
    assert accelerated.json()['view_model']['time_multiplier'] == 3600.0

    state = client.get('/api/state')
    assert state.status_code == 200
    assert state.json()['view_model']['runtime_time_multiplier'] == 3600.0


def test_runtime_blob_override_endpoint(client):
    client.post('/api/runtime-test/start')

    override = client.post('/api/runtime-test/blob-override', json={'blob1': 'rgb(1, 2, 3)', 'blob2': '#112233'})
    assert override.status_code == 200
    assert override.json()['view_model']['overrides']['blob1'] == 'rgb(1, 2, 3)'
    assert override.json()['view_model']['overrides']['blob2'] == '#112233'

    state = client.get('/api/state')
    assert state.status_code == 200
    palette = state.json()['view_model']['next_prayer']['palette']
    assert palette['blob1'] == 'rgb(1, 2, 3)'
    assert palette['blob2'] == '#112233'

    clear = client.post('/api/runtime-test/blob-override/clear')
    assert clear.status_code == 200
    assert clear.json()['view_model']['overrides']['blob1'] is None
    assert clear.json()['view_model']['overrides']['blob2'] is None
