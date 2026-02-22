from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi
from threading import Event, Lock, Thread
from time import monotonic, sleep, time
from typing import Callable, Iterable, Protocol

from hardware.color_profile import ColorConverter
from hardware.lights import LightController, StripConfig


@dataclass(frozen=True)
class AmbilightConfig:
    enabled: bool = True
    gpio_pin: int = 18
    led_count: int = 120
    brightness: int = 96
    color_order: str = "GRB"


@dataclass(frozen=True)
class WakeBlinkProfile:
    period_seconds: float = 1.5
    min_blend: float = 0.2
    max_blend: float = 1.0
    base_mix: float = 0.35
    overlay_mix: float = 0.65
    color: tuple[int, int, int] = (100, 210, 255)


class AmbilightEffect(Protocol):
    def apply(self, colors: list[tuple[int, int, int]], timestamp: float) -> list[tuple[int, int, int]]:
        ...


class NoopEffect:
    def apply(self, colors: list[tuple[int, int, int]], timestamp: float) -> list[tuple[int, int, int]]:
        del timestamp
        return colors


class WakeBlinkEffect:
    _BLINK_PERIOD_SECONDS = WakeBlinkProfile.period_seconds

    def __init__(self, profile: WakeBlinkProfile | None = None, color: tuple[int, int, int] | None = None) -> None:
        if profile is None:
            profile = WakeBlinkProfile(color=color or WakeBlinkProfile().color)
        elif color is not None:
            profile = WakeBlinkProfile(
                period_seconds=profile.period_seconds,
                min_blend=profile.min_blend,
                max_blend=profile.max_blend,
                base_mix=profile.base_mix,
                overlay_mix=profile.overlay_mix,
                color=color,
            )
        self._profile = profile

    @property
    def profile(self) -> WakeBlinkProfile:
        return self._profile

    def apply(self, colors: list[tuple[int, int, int]], timestamp: float) -> list[tuple[int, int, int]]:
        phase = (timestamp % self._profile.period_seconds) / self._profile.period_seconds
        oscillation = (1.0 - cos(2.0 * pi * phase)) / 2.0
        pulse = self._profile.min_blend + ((self._profile.max_blend - self._profile.min_blend) * oscillation)
        return [
            (
                round((base[0] * self._profile.base_mix) + (self._profile.color[0] * pulse * self._profile.overlay_mix)),
                round((base[1] * self._profile.base_mix) + (self._profile.color[1] * pulse * self._profile.overlay_mix)),
                round((base[2] * self._profile.base_mix) + (self._profile.color[2] * pulse * self._profile.overlay_mix)),
            )
            for base in colors
        ]


class AmbilightController:
    _BASE_VERTICAL_LEDS = 30
    _BASE_HORIZONTAL_LEDS = 52

    _GAMMA = 2.35
    _FRAME_RATE = 30.0
    _SMOOTHING_HALF_LIFE = 0.18
    _DARKEN_FACTOR = 0.78
    _SATURATION_BOOST = 1.12
    _WAKE_EFFECT_DURATION_SECONDS = 6.0

    def __init__(self, config: AmbilightConfig, converter: ColorConverter | None = None) -> None:
        self._config = config
        self._converter = converter or ColorConverter()
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
        self._effect_lock = Lock()
        self._wake_effect_until = 0.0
        self._wake_effect_started_at = 0.0
        self._wake_effect_started_at_epoch_ms = 0
        self._wake_effect_until_epoch_ms = 0
        self._wake_profile = WakeBlinkProfile()
        self._effect_factories: dict[str, Callable[[], AmbilightEffect]] = {
            "none": NoopEffect,
            "wake_blink": lambda: WakeBlinkEffect(self._wake_profile),
        }
        self._effect_titles: dict[str, str] = {
            "none": "Без эффекта",
            "wake_blink": "Мигание при wake",
        }
        self._effect_name = "wake_blink"
        self._effect: AmbilightEffect = self._effect_factories[self._effect_name]()
        self._render_thread: Thread | None = None
        if self._config.enabled:
            self._render_thread = Thread(target=self._render_loop, name="ambilight-render", daemon=True)
            self._render_thread.start()

    @classmethod
    def _to_linear(cls, value: int) -> float:
        return pow(max(0.0, min(1.0, value / 255.0)), cls._GAMMA)

    @classmethod
    def _to_gamma(cls, value: float) -> int:
        clamped = max(0.0, min(1.0, value))
        return round(pow(clamped, 1.0 / cls._GAMMA) * 255.0)

    @classmethod
    def _apply_ambilight_tone_mapping(cls, rgb: tuple[int, int, int]) -> tuple[int, int, int]:
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
        del width, height
        led_count = max(12, self._config.led_count)
        base_layout = [
            self._BASE_VERTICAL_LEDS,
            self._BASE_HORIZONTAL_LEDS,
            self._BASE_VERTICAL_LEDS,
            self._BASE_HORIZONTAL_LEDS,
        ]
        base_total = sum(base_layout)
        scale = led_count / base_total

        scaled = [max(1, int(value * scale)) for value in base_layout]
        missing = led_count - sum(scaled)
        if missing != 0:
            priorities = sorted(
                range(len(base_layout)),
                key=lambda idx: (base_layout[idx] * scale) - int(base_layout[idx] * scale),
                reverse=missing > 0,
            )
            step = 1 if missing > 0 else -1
            idx = 0
            while missing != 0:
                edge_index = priorities[idx % len(priorities)]
                if scaled[edge_index] + step >= 1:
                    scaled[edge_index] += step
                    missing -= step
                idx += 1

        right, top, left, bottom = scaled
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

        raw_strip = list(reversed(right)) + list(reversed(top)) + left + bottom
        tone_mapped = [self._apply_ambilight_tone_mapping(color) for color in raw_strip]
        return [self._converter.convert(color) for color in tone_mapped]

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

            with self._effect_lock:
                wake_overlay_active = now < self._wake_effect_until
                effect = self._effect
            if wake_overlay_active:
                rendered = effect.apply(rendered, max(0.0, now - self._wake_effect_started_at))

            self._driver.show(rendered)
            if dt < target_dt:
                sleep(target_dt - dt)


    def show_calibration_color(self, rgb: tuple[int, int, int]) -> int:
        if not self._config.enabled:
            return 0

        direct_rgb = self._safe_rgb(rgb)
        strip = [direct_rgb for _ in range(self._config.led_count)]
        with self._frame_lock:
            self._target_strip = strip
            self._current_strip = [(float(direct_rgb[0]), float(direct_rgb[1]), float(direct_rgb[2])) for _ in range(self._config.led_count)]

        with self._effect_lock:
            self._wake_effect_until = 0.0
            self._wake_effect_until_epoch_ms = 0

        self._driver.show(strip)
        self._render_event.set()
        return len(strip)

    def apply_frame(self, edge_colors: dict, viewport: dict | None = None) -> int:
        if not self._config.enabled:
            return 0
        strip = self._build_led_strip(edge_colors=edge_colors, viewport=viewport)
        with self._frame_lock:
            self._target_strip = strip
        self._render_event.set()
        return len(strip)

    def trigger_wake_effect(self, duration_seconds: float = _WAKE_EFFECT_DURATION_SECONDS) -> None:
        now = monotonic()
        now_epoch_ms = round(time() * 1000)
        safe_duration = max(0.1, duration_seconds)
        with self._effect_lock:
            if now >= self._wake_effect_until:
                self._wake_effect_started_at = now
                self._wake_effect_started_at_epoch_ms = now_epoch_ms
            self._wake_effect_until = max(self._wake_effect_until, now + safe_duration)
            self._wake_effect_until_epoch_ms = max(self._wake_effect_until_epoch_ms, now_epoch_ms + round(safe_duration * 1000))
        self._render_event.set()

    def wake_blink_state(self) -> dict:
        with self._effect_lock:
            return {
                "started_at_epoch_ms": self._wake_effect_started_at_epoch_ms,
                "active_until_epoch_ms": self._wake_effect_until_epoch_ms,
                "profile": {
                    "period_seconds": self._wake_profile.period_seconds,
                    "min_blend": self._wake_profile.min_blend,
                    "max_blend": self._wake_profile.max_blend,
                    "base_mix": self._wake_profile.base_mix,
                    "overlay_mix": self._wake_profile.overlay_mix,
                    "color": list(self._wake_profile.color),
                },
            }

    def set_effect_mode(self, name: str) -> bool:
        normalized = str(name or "").strip().lower()
        factory = self._effect_factories.get(normalized)
        if factory is None:
            return False
        with self._effect_lock:
            self._effect_name = normalized
            self._effect = factory()
        self._render_event.set()
        return True

    def effect_status(self) -> dict:
        with self._effect_lock:
            current = self._effect_name
        available = [
            {"name": name, "title": self._effect_titles.get(name, name)}
            for name in sorted(self._effect_factories.keys())
        ]
        return {"current": current, "available": available}

    def shutdown(self) -> None:
        self._shutdown_event.set()
        self._render_event.set()
        if self._render_thread and self._render_thread.is_alive():
            self._render_thread.join(timeout=0.4)
        self._driver.off()
