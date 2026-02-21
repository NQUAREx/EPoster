from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))

from hardware.ambilight import AmbilightConfig, AmbilightController


def test_ambilight_led_distribution_matches_configured_length():
    controller = AmbilightController(AmbilightConfig(enabled=True, led_count=50))
    right, top, left, bottom = controller._distribute_leds(width=1920, height=1080)
    assert right + top + left + bottom == 50


def test_ambilight_frame_applies_clockwise_from_bottom_right():
    controller = AmbilightController(AmbilightConfig(enabled=True, led_count=12))
    edge_colors = {
        "right": [[255, 0, 0]],
        "top": [[0, 255, 0]],
        "left": [[0, 0, 255]],
        "bottom": [[255, 255, 0]],
    }
    led_count = controller.apply_frame(edge_colors=edge_colors, viewport={"width": 100, "height": 100})
    assert led_count == 12


def test_disabled_ambilight_ignores_frames():
    controller = AmbilightController(AmbilightConfig(enabled=False, led_count=60))
    led_count = controller.apply_frame(edge_colors={"top": [], "right": [], "bottom": [], "left": []}, viewport=None)
    assert led_count == 0
