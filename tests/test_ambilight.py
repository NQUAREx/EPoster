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
    controller = AmbilightController(AmbilightConfig(enabled=True, led_count=164))
    edge_colors = {
        "right": [[255, 0, 0], [10, 20, 30]],
        "top": [[0, 255, 0], [0, 20, 10]],
        "left": [[0, 0, 255], [40, 50, 60]],
        "bottom": [[255, 255, 0], [12, 34, 56]],
    }
    strip = controller._build_led_strip(edge_colors=edge_colors, viewport={"width": 100, "height": 100})

    first_expected = controller._apply_ambilight_tone_mapping((10, 20, 30))
    right_tail_expected = controller._apply_ambilight_tone_mapping((255, 0, 0))
    top_head_expected = controller._apply_ambilight_tone_mapping((0, 20, 10))

    assert len(strip) == 164
    assert strip[0] == first_expected
    assert strip[29] == right_tail_expected
    assert strip[30] == top_head_expected


def test_disabled_ambilight_ignores_frames():
    controller = AmbilightController(AmbilightConfig(enabled=False, led_count=60))
    led_count = controller.apply_frame(edge_colors={"top": [], "right": [], "bottom": [], "left": []}, viewport=None)
    assert led_count == 0


def test_tone_mapping_darkens_but_preserves_color_bias():
    source = (200, 90, 40)
    mapped = AmbilightController._apply_ambilight_tone_mapping(source)
    assert mapped[0] < source[0]
    assert mapped[1] < source[1]
    assert mapped[2] < source[2]
    assert mapped[0] > mapped[1] > mapped[2]


def test_ambilight_led_distribution_prefers_30x52_layout():
    controller = AmbilightController(AmbilightConfig(enabled=True, led_count=164))
    right, top, left, bottom = controller._distribute_leds(width=1920, height=1080)
    assert (right, top, left, bottom) == (30, 52, 30, 52)
