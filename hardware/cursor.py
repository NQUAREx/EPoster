from __future__ import annotations

import os
import subprocess


_UNCLUTTER_PROCESS: subprocess.Popen | None = None


def move_cursor_to_bottom_right() -> bool:
    """Backward-compatible entrypoint: now hides cursor via unclutter on X11."""
    global _UNCLUTTER_PROCESS

    if _UNCLUTTER_PROCESS is not None and _UNCLUTTER_PROCESS.poll() is None:
        return True

    if not os.environ.get("DISPLAY"):
        return False

    try:
        _UNCLUTTER_PROCESS = subprocess.Popen(
            ["unclutter", "-idle", "0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        return False

    return _UNCLUTTER_PROCESS.poll() is None
