from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BaseBackground:
    id: int
    theme_class: str
    animation_profile: str


_BASE_BACKGROUNDS: dict[int, BaseBackground] = {
    1: BaseBackground(id=1, theme_class="bg-theme-1", animation_profile="lava-v1"),
}


def resolve_base_background(background_id: int) -> BaseBackground:
    return _BASE_BACKGROUNDS.get(background_id, _BASE_BACKGROUNDS[1])
