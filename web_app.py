from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.routes import build_router
from app_controller import AppController
from services.app_service import AppService
from services.realtime import StateBroadcaster


@asynccontextmanager
async def lifespan(app: FastAPI):
    controller = AppController()
    broadcaster = StateBroadcaster()
    app.state.app_service = AppService(controller, broadcaster)
    app.state.broadcaster = broadcaster
    try:
        yield
    finally:
        await app.state.app_service.shutdown()


def create_app() -> FastAPI:
    ui_dir = Path(__file__).resolve().parent / "ui"
    app = FastAPI(title="EPoster API", debug=False, lifespan=lifespan)
    app.include_router(build_router(ui_dir))
    app.mount("/ui", StaticFiles(directory=str(ui_dir)), name="ui")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
