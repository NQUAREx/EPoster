#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


class RuntimeTestClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get(self, path: str) -> dict:
        req = urllib.request.Request(f"{self.base_url}{path}", method="GET")
        return self._send(req)

    def post(self, path: str, payload: dict | None = None) -> dict:
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=headers, method="POST")
        return self._send(req)

    @staticmethod
    def _send(req: urllib.request.Request) -> dict:
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def print_help() -> None:
    print(
        """
Команды:
  help                     - показать помощь
  status                   - статус runtime режима
  start                    - включить runtime режим (основной backend на паузе)
  stop                     - выключить runtime режим (возврат управления backend)
  set-times HH:MM HH:MM    - задать суxур и ифтар (например: set-times 04:20 18:45)
  clear-times              - убрать override времени
  cycle-start              - ускорить время (1 час = 1 сек)
  cycle-stop               - остановить ускорение времени
  set-blob-bg VALUE        - override цвета фона blob (rgb(...) или #RRGGBB)
  set-blob1 VALUE          - override blob1
  set-blob2 VALUE          - override blob2
  set-blob3 VALUE          - override blob3
  clear-blob               - убрать все blob override
  pick                     - меню выбора пункта
  exit                     - выход
""".strip()
    )


def print_status(payload: dict) -> None:
    vm = payload.get("view_model", payload)
    print("active:", vm.get("active"))
    print("virtual_now:", vm.get("virtual_now"))
    print("time_multiplier:", vm.get("time_multiplier"))
    print("overrides:", vm.get("overrides"))


def selection_menu(client: RuntimeTestClient) -> None:
    while True:
        print("\nВыберите действие:")
        print(" 1) status")
        print(" 2) start")
        print(" 3) stop")
        print(" 4) set-times")
        print(" 5) clear-times")
        print(" 6) cycle-start")
        print(" 7) cycle-stop")
        print(" 8) set-blob-bg")
        print(" 9) set-blob1")
        print("10) set-blob2")
        print("11) set-blob3")
        print("12) clear-blob")
        print(" 0) back")
        choice = input("> ").strip()
        if choice == "0":
            return
        if choice == "1":
            print_status(client.get("/api/runtime-test/status"))
        elif choice == "2":
            print_status(client.post("/api/runtime-test/start"))
        elif choice == "3":
            print_status(client.post("/api/runtime-test/stop"))
        elif choice == "4":
            suhoor = input("suhoor HH:MM> ").strip()
            iftar = input("iftar HH:MM> ").strip()
            print_status(client.post("/api/runtime-test/prayer-override", {"suhoor": suhoor, "iftar": iftar}))
        elif choice == "5":
            print_status(client.post("/api/runtime-test/prayer-override/clear"))
        elif choice == "6":
            print_status(client.post("/api/runtime-test/time-cycle/start", {"hours_per_second": 1.0}))
        elif choice == "7":
            print_status(client.post("/api/runtime-test/time-cycle/stop"))
        elif choice == "8":
            value = input("blob bg color> ").strip()
            print_status(client.post("/api/runtime-test/blob-override", {"bg": value}))
        elif choice == "9":
            value = input("blob1 color> ").strip()
            print_status(client.post("/api/runtime-test/blob-override", {"blob1": value}))
        elif choice == "10":
            value = input("blob2 color> ").strip()
            print_status(client.post("/api/runtime-test/blob-override", {"blob2": value}))
        elif choice == "11":
            value = input("blob3 color> ").strip()
            print_status(client.post("/api/runtime-test/blob-override", {"blob3": value}))
        elif choice == "12":
            print_status(client.post("/api/runtime-test/blob-override/clear"))
        else:
            print("Неизвестный пункт")


def main() -> int:
    parser = argparse.ArgumentParser(description="SSH runtime test console")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL API")
    args = parser.parse_args()

    client = RuntimeTestClient(args.url)
    print("Runtime SSH console. Введите help для списка команд.")

    while True:
        try:
            raw = input("runtime> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nexit")
            return 0

        if not raw:
            continue
        if raw == "help":
            print_help()
            continue
        if raw == "exit":
            return 0
        try:
            if raw == "status":
                print_status(client.get("/api/runtime-test/status"))
            elif raw == "start":
                print_status(client.post("/api/runtime-test/start"))
            elif raw == "stop":
                print_status(client.post("/api/runtime-test/stop"))
            elif raw.startswith("set-times "):
                _, suhoor, iftar = raw.split(maxsplit=2)
                print_status(client.post("/api/runtime-test/prayer-override", {"suhoor": suhoor, "iftar": iftar}))
            elif raw == "clear-times":
                print_status(client.post("/api/runtime-test/prayer-override/clear"))
            elif raw == "cycle-start":
                print_status(client.post("/api/runtime-test/time-cycle/start", {"hours_per_second": 1.0}))
            elif raw == "cycle-stop":
                print_status(client.post("/api/runtime-test/time-cycle/stop"))
            elif raw.startswith("set-blob-bg "):
                _, value = raw.split(maxsplit=1)
                print_status(client.post("/api/runtime-test/blob-override", {"bg": value}))
            elif raw.startswith("set-blob1 "):
                _, value = raw.split(maxsplit=1)
                print_status(client.post("/api/runtime-test/blob-override", {"blob1": value}))
            elif raw.startswith("set-blob2 "):
                _, value = raw.split(maxsplit=1)
                print_status(client.post("/api/runtime-test/blob-override", {"blob2": value}))
            elif raw.startswith("set-blob3 "):
                _, value = raw.split(maxsplit=1)
                print_status(client.post("/api/runtime-test/blob-override", {"blob3": value}))
            elif raw == "clear-blob":
                print_status(client.post("/api/runtime-test/blob-override/clear"))
            elif raw == "pick":
                selection_menu(client)
            else:
                print("Неизвестная команда. help")
        except Exception as exc:
            print(f"Ошибка: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
