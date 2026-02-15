from __future__ import annotations

from app_controller import AppController


if __name__ == "__main__":
    app = AppController()
    print("Initial view:", app.render())
