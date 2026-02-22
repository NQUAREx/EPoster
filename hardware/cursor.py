from __future__ import annotations

import importlib
import importlib.util
import os


def move_cursor_to_bottom_right() -> bool:
    if not os.environ.get("DISPLAY"):
        return False

    pyautogui_spec = importlib.util.find_spec("pyautogui")
    if pyautogui_spec is None:
        return False

    try:
        pyautogui = importlib.import_module("pyautogui")
    except Exception:
        return False

    try:
        width, height = pyautogui.size()
        pyautogui.moveTo(max(0, width - 1), max(0, height - 1), duration=0)
    except Exception:
        return False
    return True
