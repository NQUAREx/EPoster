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

## Запуск на Linux (production и dev)

1. Установите Python 3.10+.
2. В корне проекта:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install fastapi uvicorn gunicorn pytest httpx
```

### Dev-режим (локально)

```bash
python web_app.py
```

> `web_app.py` содержит прямой entrypoint (`if __name__ == "__main__"`) и запускает Uvicorn без autoreload.

или эквивалентно:

```bash
uvicorn web_app:app --host 0.0.0.0 --port 8000
```

### Production (рекомендуется для Raspberry Pi 24/7)

```bash
gunicorn -k uvicorn.workers.UvicornWorker -w 1 -b 0.0.0.0:8000 web_app:app
```

- `debug` и `reload` отключены по умолчанию.
- Для systemd используйте пример `deploy/eposter.service`.

Откройте браузер:

- Linux: `http://127.0.0.1:8000`
- WSL через Windows браузер: `http://localhost:8000`


## Голосовой модуль (wake-word + фиксированные команды)

Добавлен отдельный модуль `voice/recognizer.py`, который **не меняет логику backend** и работает как внешний процесс:

- слушает wake-слово `плакат`;
- после wake отправляет `POST /api/wake` (для синей рамки в UI);
- открывает окно 6 секунд на команду; после каждой распознанной команды окно продлевается ещё на 6 секунд;
- распознает фиксированный набор русских фраз и мапит в backend-команды;
- отправляет `POST /api/command` с `source="voice"`;
- печатает распознанный текст и mapped-команду в консоль для отладки.

Поддерживаемый фиксированный набор (RU → backend):

- `карта`, `открыть карту`, `покажи карту` → `open_tasks_map`
- `проверка`, `режим проверки`, `открыть проверку` → `open_day_review`
- `задание`, `открыть задание` → `open_task_info`
- `следующий`, `вперед` → `next`
- `предыдущий` → `prev`
- `назад` → `back`
- `ок`, `подтвердить` → `ok`
- `праздник`, `ид` → `open_eid`
- `оценка 1/2/3`, `оценка один/два/три` → `set_score` с payload `{"score": 1..3}`

### Запуск voice daemon

1. Установите offline-зависимости распознавания:

```bash
pip install vosk sounddevice
```

2. Запустите backend:

```bash
python web_app.py
```

3. В отдельном терминале запустите голосовой процесс:

```bash
python -m voice.recognizer --backend-url http://127.0.0.1:8000 --wake-word плакат --window 6 --model-path /absolute/path/to/vosk-model-small-ru-0.22
```

> Если `vosk/sounddevice` не установлены, модуль не будет распознавать аудио (завершит цикл без распознанных фраз).

## Тесты

```bash
pytest -q
```


### Ошибка `vosk model init failed` на Windows

Если видите ошибку вида `Folder ... does not contain model files`, значит Vosk смотрит не в ту папку (или модель повреждена).

Сделайте так:

1. Проверьте, что в папке модели есть файлы:
   - `am/final.mdl`
   - `conf/model.conf`
2. Передайте явный путь через `--model-path` **или** переменную окружения `VOSK_MODEL_PATH`.
3. Используйте абсолютный путь в Windows, например:

```powershell
python -m voice.recognizer --model-path "C:\vosk\vosk-model-small-ru-0.22"
```

В модуле добавлена проверка валидности директории модели до старта распознавания.
