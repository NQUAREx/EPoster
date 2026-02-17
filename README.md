# EPoster

Офлайн state-driven платформа для электронного плаката Рамадана.

## Что реализовано сейчас

- Backend на **FastAPI** с API:
  - `GET /`
  - `GET /api/state`
  - `POST /api/wake`
  - `POST /api/command`
- Home state (`base`) как домашний экран:
  - день,
  - время до сухура,
  - время до ифтара,
  - краткое задание дня.
- Day review в режиме поочередной проверки детей:
  - порядок детей случайный для каждого дня,
  - на экране показывается только текущий ребенок,
  - команда `set_score` (0..3) переводит к следующему,
  - после последнего ребенка автоматически возврат в `base_state`.
- Есть нормализация команд из внешних источников (voice/GPIO/UI) через единый роутер команд.
- Список детей хранится отдельно в `data/children.json`.
- Локализация только русская.

## Структура данных

- `data/children.json` — список детей.
- `data/tasks.json` — 30 заданий по дням.
- `data/settings.json` — настройки системы.
- `data/session.json` — текущее состояние плаката.
- `data/prayer_times_2026.json` — время молитв.

## Команды (для ручного теста UI)

> В боевом режиме команды должен передавать голосовой модуль (или GPIO-модуль через backend).

- `open_tasks_map` (или алиас `open_map`)
- `open_task_info`
- `open_day_review` (или алиас `start_day_review`)
- `set_score` с payload: `{"score": 1..3}`
- `next` / `prev`
- `ok`
- `open_eid`
- `back`

## Запуск на Linux (включая WSL)

1. Установите Python 3.10+.
2. В корне проекта:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install fastapi uvicorn pytest httpx
```

3. Запуск API + UI:

```bash
python web_app.py
```

4. Откройте браузер:

- В Linux: `http://127.0.0.1:8000`
- В WSL через Windows браузер: `http://localhost:8000`

## Тесты

```bash
pytest -q
```
