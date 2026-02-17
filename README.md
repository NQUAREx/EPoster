# EPoster (Ramadan Poster for Raspberry Pi)

Минимальный офлайн-прототип state-driven приложения с Flask API + single-page UI.

## Что уже работает

- State machine с состояниями: `day_review`, `task_map`, `summary`, `settings`, `celebration`.
- Переключение через команды (без голосового слоя):
  - кнопки быстрых команд в UI;
  - ручной ввод `command` + JSON `payload`.
- Единый API:
  - `GET /api/state`
  - `POST /api/command`
- Хранение состояния только в JSON (`data/session.json`, `data/settings.json`, `data/tasks.json`).

## Запуск в WSL (Windows)

```bash
python -m venv .venv
source .venv/bin/activate
pip install flask pytest
python web_app.py
```

Открыть в браузере: `http://localhost:5000`

## Команды

- `open_map`, `open_summary`, `back`
- `set_score` (`{"child": "Али", "score": 2}`), `clear_score`
- `finish_day`, `next_day`, `restart`
- `open_settings`, `set_language`, `set_secret_command`, `set_gift_total_target`
- секретная команда из `settings.secret_celebration_command`

## Тесты

```bash
pytest -q
```
