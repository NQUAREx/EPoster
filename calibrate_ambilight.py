from __future__ import annotations

import argparse
import json
from urllib import request


def _call(method: str, url: str, payload: dict | None = None) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, method=method, data=data, headers=headers)
    with request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_color(raw: str) -> list[int]:
    value = raw.strip()
    if value.startswith("#") and len(value) == 7:
        return [int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)]
    parts = [chunk.strip() for chunk in value.split(",")]
    if len(parts) != 3:
        raise ValueError("Формат цвета: R,G,B или #RRGGBB")
    return [max(0, min(255, int(part))) for part in parts]


def main() -> None:
    parser = argparse.ArgumentParser(description="Пошаговая калибровка ambilight")
    parser.add_argument("--host", default="http://127.0.0.1:8000", help="Базовый URL API")
    args = parser.parse_args()

    base = args.host.rstrip("/")
    state = _call("POST", f"{base}/api/calibration/start")
    view_model = state.get("view_model", {})

    print("Калибровка запущена. UI переведен в calibration_state.")
    while True:
        step = view_model.get("step")
        total = view_model.get("total_steps")
        color = view_model.get("screen_color", {})
        last_observed: list[int] | None = None
        print(f"\nШаг {step}/{total}, экранный цвет: {color}")
        print("Введите цвет, проверьте ленту и нажмите 'next' для перехода к следующему шагу.")
        print("Команды: next, q")

        while True:
            raw = input("Цвет (R,G,B или #RRGGBB) / команда: ").strip()
            if raw.lower() == "q":
                _call("POST", f"{base}/api/calibration/cancel")
                print("Калибровка отменена.")
                return
            if raw.lower() == "next":
                if last_observed is None:
                    print("Сначала введите цвет для текущего шага.")
                    continue
                observed = last_observed
                print(f"Отправляется последний цвет: {observed}")
                break

            try:
                observed = _parse_color(raw)
            except ValueError as exc:
                print(f"Ошибка ввода: {exc}")
                continue
            last_observed = observed
            preview = _call("POST", f"{base}/api/calibration/preview", {"observed_rgb": observed})
            if preview.get("ok"):
                print(f"Показано на ленте: {observed}")
            else:
                print(f"Не удалось показать цвет на ленте: {preview}")

        result = _call("POST", f"{base}/api/calibration/sample", {"observed_rgb": observed})
        if result.get("finished"):
            break
        payload = result.get("state_payload", {})
        view_model = payload.get("view_model", view_model)

    finish = _call("POST", f"{base}/api/calibration/finish")
    if finish.get("ok"):
        print(f"Готово. Профиль сохранен: {finish.get('profile_file')}")
    else:
        print(f"Ошибка сохранения: {finish}")


if __name__ == "__main__":
    main()
