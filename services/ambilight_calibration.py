from __future__ import annotations

from dataclasses import dataclass

from hardware.calibration_math import CalibrationSample, build_correction_profile
from hardware.color_profile import ColorProfile


@dataclass
class CalibrationStep:
    index: int
    total: int
    screen_rgb: tuple[int, int, int]


class AmbilightCalibration:
    _DEFAULT_SEQUENCE = [
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 255, 255),
        (128, 128, 128),
        (255, 255, 0),
        (0, 255, 255),
        (255, 0, 255),
        (255, 128, 0),
        (32, 32, 32),
    ]

    def __init__(self) -> None:
        self._active = False
        self._sequence = list(self._DEFAULT_SEQUENCE)
        self._index = 0
        self._samples: list[CalibrationSample] = []

    @property
    def active(self) -> bool:
        return self._active

    def start(self) -> CalibrationStep:
        self._active = True
        self._index = 0
        self._samples = []
        return self.current_step()

    def stop(self) -> None:
        self._active = False

    def current_step(self) -> CalibrationStep:
        idx = min(self._index, len(self._sequence) - 1)
        return CalibrationStep(index=idx + 1, total=len(self._sequence), screen_rgb=self._sequence[idx])

    def submit_observed(self, observed_rgb: tuple[int, int, int]) -> CalibrationStep | None:
        if not self._active:
            return None

        target = self._sequence[self._index]
        self._samples.append(CalibrationSample(screen_rgb=target, observed_rgb=observed_rgb))
        self._index += 1
        if self._index >= len(self._sequence):
            return None
        return self.current_step()

    def can_finish(self) -> bool:
        return len(self._samples) >= 4

    def build_profile(self) -> ColorProfile:
        return build_correction_profile(self._samples)

    def view_model(self) -> dict:
        step = self.current_step()
        color = step.screen_rgb
        return {
            "view": "calibration_state",
            "title": "Калибровка ambilight",
            "step": step.index,
            "total_steps": step.total,
            "screen_color": {"r": color[0], "g": color[1], "b": color[2]},
            "screen_color_css": f"rgb({color[0]}, {color[1]}, {color[2]})",
            "hint": "Введите наблюдаемый цвет ленты в ssh-скрипте (формат: R,G,B или #RRGGBB)",
        }
