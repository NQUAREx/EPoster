from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Iterable


@dataclass(frozen=True)
class AmbilightConfig:
    enabled: bool = True
    gpio_pin: int = 18
    led_count: int = 120
    brightness: int = 96
    color_order: str = "GRB"


class _Ws2812Driver:
    def __init__(self, config: AmbilightConfig) -> None:
        self._config = config
        self._pixels = None
        self._lock = Lock()
        self._active = False
        self._setup_driver()

    def _setup_driver(self) -> None:
        if not self._config.enabled:
            return
        try:
            from rpi_ws281x import PixelStrip, ws  # type: ignore

            pixel_order = {
                "RGB": ws.WS2811_STRIP_RGB,
                "RBG": ws.WS2811_STRIP_RBG,
                "GRB": ws.WS2811_STRIP_GRB,
                "GBR": ws.WS2811_STRIP_GBR,
                "BRG": ws.WS2811_STRIP_BRG,
                "BGR": ws.WS2811_STRIP_BGR,
            }.get(self._config.color_order, ws.WS2811_STRIP_GRB)

            self._pixels = PixelStrip(
                self._config.led_count,
                self._config.gpio_pin,
                800_000,
                10,
                False,
                self._config.brightness,
                0,
                pixel_order,
            )
            self._pixels.begin()
            self._active = True
        except Exception:
            self._pixels = None
            self._active = False

    @staticmethod
    def _to_color_int(rgb: tuple[int, int, int]) -> int:
        return (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]

    def show(self, colors: list[tuple[int, int, int]]) -> None:
        if not self._active or self._pixels is None:
            return
        with self._lock:
            for index, rgb in enumerate(colors[: self._config.led_count]):
                self._pixels.setPixelColor(index, self._to_color_int(rgb))
            self._pixels.show()

    def off(self) -> None:
        if not self._active or self._pixels is None:
            return
        with self._lock:
            for index in range(self._config.led_count):
                self._pixels.setPixelColor(index, 0)
            self._pixels.show()


class AmbilightController:
    def __init__(self, config: AmbilightConfig) -> None:
        self._config = config
        self._driver = _Ws2812Driver(config)

    @staticmethod
    def _safe_rgb(value: Iterable[int]) -> tuple[int, int, int]:
        rgb = list(value)
        if len(rgb) != 3:
            return (0, 0, 0)
        return (
            max(0, min(255, int(rgb[0]))),
            max(0, min(255, int(rgb[1]))),
            max(0, min(255, int(rgb[2]))),
        )

    def _distribute_leds(self, width: int, height: int) -> tuple[int, int, int, int]:
        width = max(1, int(width or 1))
        height = max(1, int(height or 1))
        perimeter = (2 * width) + (2 * height)
        led_count = max(12, self._config.led_count)

        right = max(1, round(led_count * (height / perimeter)))
        top = max(1, round(led_count * (width / perimeter)))
        left = max(1, round(led_count * (height / perimeter)))
        bottom = max(1, led_count - (right + top + left))
        return right, top, left, bottom

    @staticmethod
    def _nearest_palette(palette: list[tuple[int, int, int]], count: int) -> list[tuple[int, int, int]]:
        if count <= 0:
            return []
        if not palette:
            return [(0, 0, 0)] * count
        if len(palette) == count:
            return palette
        if len(palette) == 1:
            return palette * count

        last = len(palette) - 1
        mapped: list[tuple[int, int, int]] = []
        for index in range(count):
            source_index = round((index / max(1, count - 1)) * last)
            mapped.append(palette[source_index])
        return mapped

    def _build_led_strip(self, edge_colors: dict, viewport: dict | None) -> list[tuple[int, int, int]]:
        width = int((viewport or {}).get("width", 1920) or 1920)
        height = int((viewport or {}).get("height", 1080) or 1080)
        right_count, top_count, left_count, bottom_count = self._distribute_leds(width, height)

        right = self._nearest_palette([self._safe_rgb(v) for v in edge_colors.get("right", [])], right_count)
        top = self._nearest_palette([self._safe_rgb(v) for v in edge_colors.get("top", [])], top_count)
        left = self._nearest_palette([self._safe_rgb(v) for v in edge_colors.get("left", [])], left_count)
        bottom = self._nearest_palette([self._safe_rgb(v) for v in edge_colors.get("bottom", [])], bottom_count)

        # Start in lower-right corner and move clockwise.
        return right + top + left + bottom

    def apply_frame(self, edge_colors: dict, viewport: dict | None = None) -> int:
        if not self._config.enabled:
            return 0
        strip = self._build_led_strip(edge_colors=edge_colors, viewport=viewport)
        self._driver.show(strip)
        return len(strip)

    def shutdown(self) -> None:
        self._driver.off()
