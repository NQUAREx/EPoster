# EPoster (Ramadan Poster for Raspberry Pi)

Проект собран по материалам переписки в HTML-экспорте.

## Структура

- `main.py` — точка входа.
- `app_controller.py` — orchestration приложения.
- `state_manager.py` — переключение состояний.
- `models.py` — `Day` и `Session` dataclass-модели.
- `storage.py` — загрузка/сохранение `session.json` и инициализация из `tasks.json`.
- `time_model.py` — получение времени намазов из файла.
- `states/` — модульные состояния плаката.
- `data/` — `tasks.json`, `settings.json`, `session.json`, `prayer_times_2026.json`.
- `voice/`, `hardware/`, `ui/` — подготовленные папки под интеграции.

## Быстрый старт

```bash
python main.py
```
