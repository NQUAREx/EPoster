from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class StripConfig:
    enabled: bool = True
    gpio_pin: int = 18
    led_count: int = 120
    brightness: int = 96
    color_order: str = "GRB"


class LightController:
    """WS2812/NeoPixel controller based on board + neopixel libraries."""

    _ORDER_MAP = {
        "RGB": "RGB",
        "RBG": "RBG",
        "GRB": "GRB",
        "GBR": "GBR",
        "BRG": "BRG",
        "BGR": "BGR",
    }

    def __init__(self, config: StripConfig) -> None:
        self._config = config
        self._lock = Lock()
        self._pixels = None
        self._active = False
        self._setup_driver()

    @staticmethod
    def _resolve_pin(board_module, gpio_pin: int):
        if gpio_pin == 18 and hasattr(board_module, "D18"):
            return board_module.D18
        pin_name = f"D{gpio_pin}"
        return getattr(board_module, pin_name, None)

    @staticmethod
    def _brightness_to_float(value: int) -> float:
        safe_value = min(255, max(0, int(value)))
        return safe_value / 255.0

    def _setup_driver(self) -> None:
        if not self._config.enabled:
            return

        try:
            import board  # type: ignore
            import neopixel  # type: ignore

            pin = self._resolve_pin(board, self._config.gpio_pin)
            if pin is None:
                return

            order_name = self._ORDER_MAP.get(self._config.color_order, "GRB")
            pixel_order = getattr(neopixel, order_name, neopixel.GRB)

            self._pixels = neopixel.NeoPixel(
                pin,
                self._config.led_count,
                brightness=self._brightness_to_float(self._config.brightness),
                auto_write=False,
                pixel_order=pixel_order,
            )
            self._active = True
        except Exception:
            self._pixels = None
            self._active = False

    def show(self, colors: list[tuple[int, int, int]]) -> None:
        if not self._active or self._pixels is None:
            return

        with self._lock:
            limit = min(self._config.led_count, len(colors))
            for index in range(limit):
                self._pixels[index] = colors[index]

            for index in range(limit, self._config.led_count):
                self._pixels[index] = (0, 0, 0)

            self._pixels.show()


    def set_brightness(self, brightness: int) -> None:
        safe = min(255, max(0, int(brightness)))
        if not self._active or self._pixels is None:
            return

        with self._lock:
            self._pixels.brightness = self._brightness_to_float(safe)
            self._pixels.show()

    def off(self) -> None:
        if not self._active or self._pixels is None:
            return

        with self._lock:
            self._pixels.fill((0, 0, 0))
            self._pixels.show()
