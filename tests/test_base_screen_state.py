import pytest
from states.base_screen_state import BaseScreenState


def test_palette_progress_remap_split_points():
    assert BaseScreenState._remap_palette_progress(0.0) == 0.0
    assert BaseScreenState._remap_palette_progress(0.8) == 0.2
    assert BaseScreenState._remap_palette_progress(1.0) == 1.0


def test_palette_progress_remap_slow_then_fast():
    early = BaseScreenState._remap_palette_progress(0.4)
    late = BaseScreenState._remap_palette_progress(0.9)

    # Первая половина реального времени меняет фон совсем немного
    assert early == 0.1
    # Последние 10% реального времени дают большой скачок
    assert late == pytest.approx(0.6)
