from __future__ import annotations

from dataclasses import dataclass

from hardware.color_profile import ColorProfile


@dataclass(frozen=True)
class CalibrationSample:
    screen_rgb: tuple[int, int, int]
    observed_rgb: tuple[int, int, int]


def _safe_rgb(raw: list[int] | tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(channel))) for channel in raw[:3])  # type: ignore[return-value]


def _solve_linear_3x3(a: list[list[float]], b: list[float]) -> list[float]:
    matrix = [row[:] for row in a]
    rhs = b[:]

    for pivot in range(3):
        max_row = max(range(pivot, 3), key=lambda row: abs(matrix[row][pivot]))
        if abs(matrix[max_row][pivot]) < 1e-9:
            return [0.0, 0.0, 0.0]
        if max_row != pivot:
            matrix[pivot], matrix[max_row] = matrix[max_row], matrix[pivot]
            rhs[pivot], rhs[max_row] = rhs[max_row], rhs[pivot]

        pivot_value = matrix[pivot][pivot]
        for col in range(pivot, 3):
            matrix[pivot][col] /= pivot_value
        rhs[pivot] /= pivot_value

        for row in range(3):
            if row == pivot:
                continue
            factor = matrix[row][pivot]
            for col in range(pivot, 3):
                matrix[row][col] -= factor * matrix[pivot][col]
            rhs[row] -= factor * rhs[pivot]

    return rhs


def _solve_least_squares(inputs: list[tuple[int, int, int]], outputs: list[int]) -> list[float]:
    # outputs ~= a*r + b*g + c*b + d
    design = [[float(r), float(g), float(b), 1.0] for r, g, b in inputs]

    # normal equations (4x4) with tiny regularization
    normal = [[0.0 for _ in range(4)] for _ in range(4)]
    target = [0.0 for _ in range(4)]
    for row, out in zip(design, outputs):
        for i in range(4):
            target[i] += row[i] * float(out)
            for j in range(4):
                normal[i][j] += row[i] * row[j]

    for i in range(4):
        normal[i][i] += 1e-6

    # gaussian elimination for 4x4
    for pivot in range(4):
        max_row = max(range(pivot, 4), key=lambda row: abs(normal[row][pivot]))
        if abs(normal[max_row][pivot]) < 1e-9:
            return [1.0, 0.0, 0.0, 0.0] if len(outputs) else [0.0, 0.0, 0.0, 0.0]
        if max_row != pivot:
            normal[pivot], normal[max_row] = normal[max_row], normal[pivot]
            target[pivot], target[max_row] = target[max_row], target[pivot]

        pv = normal[pivot][pivot]
        for col in range(pivot, 4):
            normal[pivot][col] /= pv
        target[pivot] /= pv

        for row in range(4):
            if row == pivot:
                continue
            factor = normal[row][pivot]
            for col in range(pivot, 4):
                normal[row][col] -= factor * normal[pivot][col]
            target[row] -= factor * target[pivot]

    return target


def build_correction_profile(samples: list[CalibrationSample]) -> ColorProfile:
    if len(samples) < 4:
        return ColorProfile.identity()

    screen = [_safe_rgb(list(sample.screen_rgb)) for sample in samples]
    observed = [_safe_rgb(list(sample.observed_rgb)) for sample in samples]

    row_r = _solve_least_squares(screen, [sample[0] for sample in observed])
    row_g = _solve_least_squares(screen, [sample[1] for sample in observed])
    row_b = _solve_least_squares(screen, [sample[2] for sample in observed])

    measured_matrix = [
        [row_r[0], row_r[1], row_r[2]],
        [row_g[0], row_g[1], row_g[2]],
        [row_b[0], row_b[1], row_b[2]],
    ]
    measured_offset = [row_r[3], row_g[3], row_b[3]]

    inv_rows = []
    for basis in ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]):
        inv_rows.append(_solve_linear_3x3(measured_matrix, list(basis)))

    inv_matrix = (
        (inv_rows[0][0], inv_rows[0][1], inv_rows[0][2]),
        (inv_rows[1][0], inv_rows[1][1], inv_rows[1][2]),
        (inv_rows[2][0], inv_rows[2][1], inv_rows[2][2]),
    )

    offset = []
    for row in inv_matrix:
        value = -((row[0] * measured_offset[0]) + (row[1] * measured_offset[1]) + (row[2] * measured_offset[2]))
        offset.append(value)

    return ColorProfile(matrix=inv_matrix, offset=(offset[0], offset[1], offset[2]))
