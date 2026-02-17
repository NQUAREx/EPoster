from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app_controller import AppController
from command_router import CommandEvent


class CommandRequest(BaseModel):
    command: str
    payload: dict | None = None
    source: str = "manual"
    wake_word_detected: bool = False


class WakeRequest(BaseModel):
    source: str = "voice"


def create_app() -> FastAPI:
    app = FastAPI(title="EPoster API")
    controller = AppController()
    ui_dir = Path(__file__).resolve().parent / "ui"

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(ui_dir / "index.html")

    @app.get("/api/state")
    def get_state() -> dict:
        ui_payload = controller.render()
        return {"state": ui_payload["view"], "view_model": ui_payload}

    @app.post("/api/wake")
    def post_wake(request: WakeRequest) -> dict:
        ui_payload = controller.render()
        ui_payload["wake_active"] = True
        ui_payload["command_source"] = request.source
        return {"state": ui_payload["view"], "view_model": ui_payload}

    @app.post("/api/command")
    def post_command(request: CommandRequest) -> dict:
        command = request.command.strip()
        if not command:
            raise HTTPException(status_code=400, detail="Поле 'command' обязательно")

        safe_payload = request.payload if isinstance(request.payload, dict) else None
        event = CommandEvent(
            command=command,
            payload=safe_payload,
            source=request.source,
            wake_word_detected=request.wake_word_detected,
        )
        ui_payload = controller.dispatch_event(event)
        return {"state": ui_payload["view"], "view_model": ui_payload}

    app.mount("/ui", StaticFiles(directory=str(ui_dir)), name="ui")
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("web_app:app", host="0.0.0.0", port=8000, reload=False)
