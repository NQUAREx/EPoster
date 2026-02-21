from __future__ import annotations

from dataclasses import dataclass
from threading import Event, Lock, Thread
from time import monotonic, sleep
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
        self._frame_lock = Lock()
        self._target_strip: list[tuple[int, int, int]] = [(0, 0, 0)] * self._config.led_count
        self._current_strip: list[tuple[float, float, float]] = [
            (0.0, 0.0, 0.0) for _ in range(self._config.led_count)
        ]
        self._shutdown_event = Event()
        self._render_event = Event()
        self._render_thread: Thread | None = None
        if self._config.enabled:
            self._render_thread = Thread(target=self._render_loop, name="ambilight-render", daemon=True)
            self._render_thread.start()

    _GAMMA = 2.35
    _FRAME_RATE = 30.0
    _SMOOTHING_HALF_LIFE = 0.18
    _MIN_LED_BRIGHTNESS = 6
    _DARKEN_FACTOR = 0.78
    _SATURATION_BOOST = 1.12

    @classmethod
    def _to_linear(cls, value: int) -> float:
        return pow(max(0.0, min(1.0, value / 255.0)), cls._GAMMA)

    @classmethod
    def _to_gamma(cls, value: float) -> int:
        clamped = max(0.0, min(1.0, value))
        return round(pow(clamped, 1.0 / cls._GAMMA) * 255.0)

    @classmethod
    def _apply_ambilight_tone_mapping(cls, rgb: tuple[int, int, int]) -> tuple[int, int, int]:
        # Рабочий пайплайн для LED: легкое затемнение, буст насыщенности,
        # минимальный порог свечения и гамма-коррекция.
        r_lin = cls._to_linear(rgb[0])
        g_lin = cls._to_linear(rgb[1])
        b_lin = cls._to_linear(rgb[2])

        luminance = (0.2126 * r_lin) + (0.7152 * g_lin) + (0.0722 * b_lin)
        r_lin = luminance + ((r_lin - luminance) * cls._SATURATION_BOOST)
        g_lin = luminance + ((g_lin - luminance) * cls._SATURATION_BOOST)
        b_lin = luminance + ((b_lin - luminance) * cls._SATURATION_BOOST)

        r_out = cls._to_gamma(r_lin * cls._DARKEN_FACTOR)
        g_out = cls._to_gamma(g_lin * cls._DARKEN_FACTOR)
        b_out = cls._to_gamma(b_lin * cls._DARKEN_FACTOR)

        if (r_out + g_out + b_out) > 0:
            r_out = max(cls._MIN_LED_BRIGHTNESS, r_out)
            g_out = max(cls._MIN_LED_BRIGHTNESS, g_out)
            b_out = max(cls._MIN_LED_BRIGHTNESS, b_out)

        return (
            max(0, min(255, r_out)),
            max(0, min(255, g_out)),
            max(0, min(255, b_out)),
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

        raw_strip = right + top + left + bottom
        return [self._apply_ambilight_tone_mapping(color) for color in raw_strip]

    def _render_loop(self) -> None:
        target_dt = 1.0 / self._FRAME_RATE
        last_tick = monotonic()

        while not self._shutdown_event.is_set():
            self._render_event.wait(timeout=target_dt)
            self._render_event.clear()

            now = monotonic()
            dt = max(1e-3, now - last_tick)
            last_tick = now
            alpha = 1.0 - pow(0.5, dt / self._SMOOTHING_HALF_LIFE)

            with self._frame_lock:
                target = list(self._target_strip)

            if len(target) != len(self._current_strip):
                self._current_strip = [(0.0, 0.0, 0.0) for _ in range(len(target))]

            rendered: list[tuple[int, int, int]] = []
            for index, target_rgb in enumerate(target):
                current_rgb = self._current_strip[index]
                next_rgb = (
                    current_rgb[0] + ((target_rgb[0] - current_rgb[0]) * alpha),
                    current_rgb[1] + ((target_rgb[1] - current_rgb[1]) * alpha),
                    current_rgb[2] + ((target_rgb[2] - current_rgb[2]) * alpha),
                )
                self._current_strip[index] = next_rgb
                rendered.append((round(next_rgb[0]), round(next_rgb[1]), round(next_rgb[2])))

            self._driver.show(rendered)
            if dt < target_dt:
                sleep(target_dt - dt)

    def apply_frame(self, edge_colors: dict, viewport: dict | None = None) -> int:
        if not self._config.enabled:
            return 0
        strip = self._build_led_strip(edge_colors=edge_colors, viewport=viewport)
        with self._frame_lock:
            self._target_strip = strip
        self._render_event.set()
        return len(strip)

    def shutdown(self) -> None:
        self._shutdown_event.set()
        self._render_event.set()
        if self._render_thread and self._render_thread.is_alive():
            self._render_thread.join(timeout=0.4)
        self._driver.off()
