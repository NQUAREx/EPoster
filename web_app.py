from __future__ import annotations

from flask import Flask, jsonify, request, send_from_directory

from app_controller import AppController


def create_app() -> Flask:
    app = Flask(__name__)
    controller = AppController()

    @app.get("/")
    def index():
        return send_from_directory("ui", "index.html")

    @app.get("/api/state")
    def get_state():
        ui_payload = controller.render()
        return jsonify({"state": ui_payload["view"], "view_model": ui_payload})

    @app.post("/api/command")
    def post_command():
        payload = request.get_json(silent=True) or {}
        command = payload.get("command")
        command_payload = payload.get("payload")

        if not isinstance(command, str) or not command.strip():
            return jsonify({"error": "Field 'command' is required"}), 400

        ui_payload = controller.dispatch(command.strip(), command_payload if isinstance(command_payload, dict) else None)
        return jsonify({"state": ui_payload["view"], "view_model": ui_payload})

    @app.get("/ui/<path:filename>")
    def ui_assets(filename: str):
        return send_from_directory("ui", filename)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
