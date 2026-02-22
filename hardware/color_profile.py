from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ColorProfile:
    matrix: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]
    offset: tuple[float, float, float]

    @staticmethod
    def identity() -> "ColorProfile":
        return ColorProfile(
            matrix=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            offset=(0.0, 0.0, 0.0),
        )

    @staticmethod
    def from_dict(data: dict | None) -> "ColorProfile":
        if not isinstance(data, dict):
            return ColorProfile.identity()
        matrix = data.get("matrix")
        offset = data.get("offset")
        try:
            parsed_matrix = tuple(
                tuple(float(value) for value in row[:3])  # type: ignore[arg-type]
                for row in matrix[:3]  # type: ignore[index]
            )
            if len(parsed_matrix) != 3 or any(len(row) != 3 for row in parsed_matrix):
                raise ValueError
        except (TypeError, ValueError):
            parsed_matrix = ColorProfile.identity().matrix

        try:
            parsed_offset = tuple(float(value) for value in offset[:3])  # type: ignore[index]
            if len(parsed_offset) != 3:
                raise ValueError
        except (TypeError, ValueError):
            parsed_offset = (0.0, 0.0, 0.0)

        return ColorProfile(matrix=parsed_matrix, offset=parsed_offset)

    def to_dict(self) -> dict:
        return {"matrix": [list(row) for row in self.matrix], "offset": list(self.offset)}


class ColorConverter:
    def __init__(self, profile: ColorProfile | None = None) -> None:
        self._profile = profile or ColorProfile.identity()

    def convert(self, rgb: Iterable[int]) -> tuple[int, int, int]:
        src = [max(0, min(255, int(channel))) for channel in rgb]
        if len(src) != 3:
            return (0, 0, 0)

        out = []
        for row_index in range(3):
            row = self._profile.matrix[row_index]
            value = (
                (row[0] * src[0])
                + (row[1] * src[1])
                + (row[2] * src[2])
                + self._profile.offset[row_index]
            )
            out.append(max(0, min(255, round(value))))
        return out[0], out[1], out[2]
