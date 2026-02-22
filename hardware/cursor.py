from __future__ import annotations

import importlib


_CURSOR_HIDDEN = False


def move_cursor_to_bottom_right() -> bool:
    """Backward-compatible entrypoint: hide cursor globally via pygame."""
    global _CURSOR_HIDDEN

    if _CURSOR_HIDDEN:
        return True

    try:
        pygame = importlib.import_module("pygame")
        pygame.init()
        pygame.mouse.set_visible(False)
    except Exception:
        return False

    _CURSOR_HIDDEN = True
    return True
