from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app_controller import AppController


class CommandRequest(BaseModel):
    command: str
    payload: dict | None = None


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

    @app.post("/api/command")
    def post_command(request: CommandRequest) -> dict:
        command = request.command.strip()
        if not command:
            raise HTTPException(status_code=400, detail="Поле 'command' обязательно")

        safe_payload = request.payload if isinstance(request.payload, dict) else None
        ui_payload = controller.dispatch(command, safe_payload)
        return {"state": ui_payload["view"], "view_model": ui_payload}

    app.mount("/ui", StaticFiles(directory=str(ui_dir)), name="ui")
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("web_app:app", host="0.0.0.0", port=8000, reload=False)
