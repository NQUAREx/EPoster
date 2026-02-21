from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from hardware.lights import LightController, StripConfig


@dataclass(frozen=True)
class AmbilightConfig:
    enabled: bool = True
    gpio_pin: int = 18
    led_count: int = 120
    brightness: int = 96
    color_order: str = "GRB"


class AmbilightController:
    def __init__(self, config: AmbilightConfig) -> None:
        self._config = config
        self._driver = LightController(
            StripConfig(
                enabled=config.enabled,
                gpio_pin=config.gpio_pin,
                led_count=config.led_count,
                brightness=config.brightness,
                color_order=config.color_order,
            )
        )

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

        return right + top + left + bottom

    def apply_frame(self, edge_colors: dict, viewport: dict | None = None) -> int:
        if not self._config.enabled:
            print("[AMBI_LIGHT] frame skipped: ambilight disabled in config")
            return 0
        strip = self._build_led_strip(edge_colors=edge_colors, viewport=viewport)
        self._driver.show(strip)
        print(f"[AMBI_LIGHT] frame accepted: total_leds={len(strip)}")
        return len(strip)

    def shutdown(self) -> None:
        print("[AMBI_LIGHT] shutdown requested")
        self._driver.off()
