# EPoster (Ramadan Poster for Raspberry Pi)

Проект собран по материалам переписки в HTML-экспорте.

## Структура

- `main.py` — точка входа.
- `app_controller.py` — orchestration приложения.
- `state_manager.py` — переключение состояний и глобальные команды.
- `models.py` — модели `Task`, `AppSettings`, `Day`, `Session`.
- `storage.py` — загрузка/сохранение `session.json`, `settings.json`, `tasks.json`.
- `states/` — состояния (`day_review`, `task_map`, `summary`, `settings`, `celebration`).
- `ui/*.html` — отдельный экран под каждый state.
- `voice/` — lightweight модуль нормализации голосовых команд.
- `hardware/lights.py` — заглушка подсветки (print принятых команд).

## Логика оценок

- Диапазон оценок: **0..3**.
- У каждого ребёнка на день стартовое значение — **`None`** (не выставлено).
- День нельзя закрыть (`finish_day`), пока всем детям не выставлена оценка.

## Команды

- `open_map`, `open_summary`, `back`
- `set_score` (`{"child": "Али", "score": 2}`), `clear_score`
- `finish_day`, `next_day`, `restart`
- `open_settings`, `set_language`, `set_secret_command`, `set_gift_total_target`
- секретная команда из `settings.secret_celebration_command` для перехода в celebration из любого state

## Быстрый старт

```bash
python main.py
pytest -q
```
