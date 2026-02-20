from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from api.schemas import CommandRequest, WakeRequest
from command_router import CommandEvent


def build_router(ui_dir: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/")
    async def index() -> FileResponse:
        return FileResponse(ui_dir / "index.html")

    @router.get("/api/state")
    async def get_state(request: Request) -> dict:
        return await request.app.state.app_service.get_state()

    @router.post("/api/wake")
    async def post_wake(payload: WakeRequest, request: Request) -> dict:
        return await request.app.state.app_service.mark_wake_detected(payload.source)

    @router.post("/api/command")
    async def post_command(payload: CommandRequest, request: Request) -> dict:
        command = payload.command.strip()
        if not command:
            raise HTTPException(status_code=400, detail="Поле 'command' обязательно")

        safe_payload = payload.payload if isinstance(payload.payload, dict) else None
        event = CommandEvent(
            command=command,
            payload=safe_payload,
            source=payload.source,
            wake_word_detected=payload.wake_word_detected,
        )
        return await request.app.state.app_service.dispatch_event(event)

    @router.websocket("/ws/state")
    async def state_ws(websocket: WebSocket) -> None:
        await websocket.accept()
        service = websocket.app.state.app_service
        broadcaster = websocket.app.state.broadcaster
        await websocket.send_json(await service.get_state())
        try:
            async with broadcaster.subscribe() as queue:
                while True:
                    payload = await queue.get()
                    await websocket.send_json(payload)
        except WebSocketDisconnect:
            return

    return router
