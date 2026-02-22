from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))

from hardware.calibration_math import CalibrationSample, build_correction_profile
from hardware.color_profile import ColorConverter, ColorProfile


def test_identity_profile_keeps_color():
    converter = ColorConverter(ColorProfile.identity())
    assert converter.convert((120, 45, 200)) == (120, 45, 200)


def test_calibration_builds_inverse_transform_for_simple_bias():
    samples = []
    for src in [(255, 0, 0), (0, 255, 0), (0, 0, 255), (140, 100, 20), (255, 255, 255)]:
        observed = (
            min(255, src[0] + 10),
            min(255, src[1] + 20),
            min(255, src[2] + 30),
        )
        samples.append(CalibrationSample(screen_rgb=src, observed_rgb=observed))

    profile = build_correction_profile(samples)
    converter = ColorConverter(profile)
    corrected = converter.convert((120, 150, 180))

    assert corrected[0] <= 120
    assert corrected[1] <= 150
    assert corrected[2] <= 180
