from __future__ import annotations

import asyncio

from app_controller import AppController
from command_router import CommandEvent
from services.realtime import StateBroadcaster


class AppService:
    def __init__(self, controller: AppController, broadcaster: StateBroadcaster) -> None:
        self._controller = controller
        self._broadcaster = broadcaster
        self._lock = asyncio.Lock()

    @staticmethod
    def _to_response(ui_payload: dict) -> dict:
        return {"state": ui_payload["view"], "view_model": ui_payload}

    async def get_state(self) -> dict:
        async with self._lock:
            ui_payload = await asyncio.to_thread(self._controller.render)
        return self._to_response(ui_payload)

    async def mark_wake_detected(self, source: str) -> dict:
        async with self._lock:
            await asyncio.to_thread(self._controller.mark_wake_detected)
            ui_payload = await asyncio.to_thread(self._controller.render)
            ui_payload["command_source"] = source
            response = self._to_response(ui_payload)
        await self._broadcaster.publish(response)
        return response

    async def dispatch_event(self, event: CommandEvent) -> dict:
        async with self._lock:
            ui_payload = await asyncio.to_thread(self._controller.dispatch_event, event)
            response = self._to_response(ui_payload)
        await self._broadcaster.publish(response)
        return response

    async def shutdown(self) -> None:
        return
