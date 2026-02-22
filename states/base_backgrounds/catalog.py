from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BaseBackground:
    id: int
    theme_class: str
    animation_profile: str


_BASE_BACKGROUNDS: dict[int, BaseBackground] = {
    1: BaseBackground(id=1, theme_class="bg-theme-1", animation_profile="lava-v1"),
    2: BaseBackground(id=2, theme_class="bg-theme-2", animation_profile="lava-v2"),
    3: BaseBackground(id=3, theme_class="bg-theme-3", animation_profile="lava-v3"),
}


def resolve_base_background(background_id: int) -> BaseBackground:
    return _BASE_BACKGROUNDS.get(background_id, _BASE_BACKGROUNDS[1])
