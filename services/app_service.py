from __future__ import annotations

import asyncio
from uuid import uuid4

from app_controller import AppController
from command_router import CommandEvent
from services.realtime import StateBroadcaster


class AppService:
    def __init__(self, controller: AppController, broadcaster: StateBroadcaster) -> None:
        self._controller = controller
        self._broadcaster = broadcaster
        self._lock = asyncio.Lock()
        self._app_instance_id = uuid4().hex

    @staticmethod
    def _to_response(ui_payload: dict) -> dict:
        return {"state": ui_payload["view"], "view_model": ui_payload}

    def _with_meta(self, response: dict) -> dict:
        payload = dict(response)
        payload["app_instance_id"] = self._app_instance_id
        return payload

    async def get_state(self) -> dict:
        async with self._lock:
            ui_payload = await asyncio.to_thread(self._controller.render)
        return self._with_meta(self._to_response(ui_payload))

    async def mark_wake_detected(self, source: str) -> dict:
        async with self._lock:
            await asyncio.to_thread(self._controller.mark_wake_detected)
            ui_payload = await asyncio.to_thread(self._controller.render)
            ui_payload["command_source"] = source
            response = self._with_meta(self._to_response(ui_payload))
        await self._broadcaster.publish(response)
        return response

    async def dispatch_event(self, event: CommandEvent) -> dict:
        async with self._lock:
            ui_payload = await asyncio.to_thread(self._controller.dispatch_event, event)
            response = self._with_meta(self._to_response(ui_payload))
        await self._broadcaster.publish(response)
        return response


    async def get_ambilight_config(self) -> dict:
        async with self._lock:
            return await asyncio.to_thread(self._controller.ambilight_config)

    async def apply_ambilight_frame(self, edge_colors: dict, viewport: dict | None = None) -> int:
        async with self._lock:
            return await asyncio.to_thread(self._controller.apply_ambilight_frame, edge_colors, viewport)



    async def calibration_start(self) -> dict:
        async with self._lock:
            response = await asyncio.to_thread(self._controller.calibration_start)
            payload = self._with_meta(self._to_response(response))
        await self._broadcaster.publish(payload)
        return payload

    async def calibration_status(self) -> dict:
        async with self._lock:
            return await asyncio.to_thread(self._controller.calibration_status)

    async def calibration_submit(self, observed_rgb: tuple[int, int, int]) -> dict:
        async with self._lock:
            result = await asyncio.to_thread(self._controller.calibration_submit, observed_rgb)
            status = await asyncio.to_thread(self._controller.calibration_status)
            if status.get("active"):
                payload = self._with_meta(self._to_response(status["view_model"]))
            else:
                payload = self._with_meta(self._to_response(await asyncio.to_thread(self._controller.render)))
        await self._broadcaster.publish(payload)
        result["state_payload"] = payload
        return result

    async def calibration_preview(self, observed_rgb: tuple[int, int, int]) -> dict:
        async with self._lock:
            return await asyncio.to_thread(self._controller.calibration_preview, observed_rgb)

    async def calibration_finish(self) -> dict:
        async with self._lock:
            result = await asyncio.to_thread(self._controller.calibration_finish)
            payload = self._with_meta(self._to_response(await asyncio.to_thread(self._controller.render)))
        await self._broadcaster.publish(payload)
        result["state_payload"] = payload
        return result

    async def calibration_cancel(self) -> dict:
        async with self._lock:
            result = await asyncio.to_thread(self._controller.calibration_cancel)
            payload = self._with_meta(self._to_response(await asyncio.to_thread(self._controller.render)))
        await self._broadcaster.publish(payload)
        result["state_payload"] = payload
        return result


    async def runtime_status(self) -> dict:
        async with self._lock:
            status = await asyncio.to_thread(self._controller.runtime_status)
            payload = self._with_meta({"state": "runtime_test", "view_model": status})
        return payload

    async def runtime_start(self) -> dict:
        async with self._lock:
            status = await asyncio.to_thread(self._controller.runtime_start)
            response = self._with_meta({"state": "runtime_test", "view_model": status})
        await self._broadcaster.publish(await self.get_state())
        return response

    async def runtime_stop(self) -> dict:
        async with self._lock:
            status = await asyncio.to_thread(self._controller.runtime_stop)
            response = self._with_meta({"state": "runtime_test", "view_model": status})
        await self._broadcaster.publish(await self.get_state())
        return response

    async def runtime_set_prayer_overrides(self, suhoor: str, iftar: str) -> dict:
        async with self._lock:
            status = await asyncio.to_thread(self._controller.runtime_set_prayer_overrides, suhoor, iftar)
            response = self._with_meta({"state": "runtime_test", "view_model": status})
        await self._broadcaster.publish(await self.get_state())
        return response

    async def runtime_clear_prayer_overrides(self) -> dict:
        async with self._lock:
            status = await asyncio.to_thread(self._controller.runtime_clear_prayer_overrides)
            response = self._with_meta({"state": "runtime_test", "view_model": status})
        await self._broadcaster.publish(await self.get_state())
        return response

    async def runtime_set_blob_overrides(
        self,
        *,
        bg: str | None = None,
        blob1: str | None = None,
        blob2: str | None = None,
        blob3: str | None = None,
    ) -> dict:
        async with self._lock:
            status = await asyncio.to_thread(
                self._controller.runtime_set_blob_overrides,
                bg=bg,
                blob1=blob1,
                blob2=blob2,
                blob3=blob3,
            )
            response = self._with_meta({"state": "runtime_test", "view_model": status})
        await self._broadcaster.publish(await self.get_state())
        return response

    async def runtime_clear_blob_overrides(self) -> dict:
        async with self._lock:
            status = await asyncio.to_thread(self._controller.runtime_clear_blob_overrides)
            response = self._with_meta({"state": "runtime_test", "view_model": status})
        await self._broadcaster.publish(await self.get_state())
        return response

    async def runtime_start_time_cycle(self, hours_per_second: float) -> dict:
        async with self._lock:
            status = await asyncio.to_thread(self._controller.runtime_start_time_cycle, hours_per_second)
            response = self._with_meta({"state": "runtime_test", "view_model": status})
        await self._broadcaster.publish(await self.get_state())
        return response

    async def runtime_stop_time_cycle(self) -> dict:
        async with self._lock:
            status = await asyncio.to_thread(self._controller.runtime_stop_time_cycle)
            response = self._with_meta({"state": "runtime_test", "view_model": status})
        await self._broadcaster.publish(await self.get_state())
        return response

    async def shutdown(self) -> None:
        await asyncio.to_thread(self._controller.shutdown)
