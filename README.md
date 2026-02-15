# EPoster (Ramadan Poster for Raspberry Pi)

Проект собран по материалам переписки в HTML-экспорте.

## Структура

- `main.py` — точка входа.
- `app_controller.py` — orchestration приложения.
- `state_manager.py` — переключение состояний и глобальные команды.
- `models.py` — модели `Task`, `AppSettings`, `Day`, `Session`.
- `storage.py` — загрузка/сохранение `session.json`, `settings.json`, `tasks.json`.
- `time_model.py` — получение времени намазов из файла.
- `states/` — модульные состояния плаката (`day_review`, `task_map`, `summary`, `settings`, `celebration`).
- `data/` — `tasks.json`, `settings.json`, `session.json`, `prayer_times_2026.json`.
- `voice/`, `hardware/`, `ui/` — интеграционные модули для Raspberry Pi.
- `tests/` — базовые автотесты сценариев приложения.

## Поддерживаемые команды

- `open_map`, `open_summary`
- `set_score` с payload `{"child": "Али", "score": 3}`
- `finish_day`, `next_day`
- `open_settings`, `set_language`, `set_secret_command`, `back`
- секретная команда из `settings.secret_celebration_command` для перехода в celebration
- `restart` (в celebration)

## Быстрый старт

```bash
python main.py
pytest -q
```
