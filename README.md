# EPoster

Офлайн state-driven платформа для электронного плаката Рамадана.

## Что реализовано сейчас

- Backend на **FastAPI** с API:
  - `GET /`
  - `GET /api/state`
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
  - после последнего ребенка автоматически открывается `summary`.
- Список детей хранится отдельно в `data/children.json`.
- Локализация только русская.

## Структура данных

- `data/children.json` — список детей.
- `data/tasks.json` — 30 заданий по дням.
- `data/settings.json` — настройки системы.
- `data/session.json` — текущее состояние плаката.

## Команды (для ручного теста UI)

> В боевом режиме команды должен передавать голосовой модуль.

- `start_day_review`
- `set_score` с payload: `{"score": 0..3}`
- `open_map`
- `open_summary`
- `open_settings`
- `next_day`
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

## Если Windows не открывает localhost для WSL

1. Проверьте, что сервер слушает `0.0.0.0:8000`.
2. Проверьте из WSL:

```bash
curl http://127.0.0.1:8000/api/state
```

3. Если в браузере Windows всё еще не открывается, используйте IP WSL:

```bash
hostname -I
```

и откройте `http://<WSL_IP>:8000`.

4. Проверьте, что порт 8000 не занят другим процессом.

## Запуск на Windows (без WSL, PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install fastapi uvicorn pytest httpx
python web_app.py
```

Откройте: `http://127.0.0.1:8000`

## Тесты

```bash
pytest -q
```
