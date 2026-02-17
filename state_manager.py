from __future__ import annotations

from models import AppSettings, PrayerTimes, Session, Task
from states import BaseScreenState, DayReviewState, EidState, TaskInfoState, TasksMapState
from states.base_state import BaseState


class StateManager:
    def __init__(self, session: Session, tasks: list[Task], settings: AppSettings, prayer_times: dict[str, PrayerTimes]):
        self.session = session
        self.tasks = tasks
        self.settings = settings
        self.prayer_times = prayer_times
        self.state: BaseState = self._create_state("base_state")

    def refresh_data(self, tasks: list[Task], prayer_times: dict[str, PrayerTimes]) -> None:
        self.tasks = tasks
        self.prayer_times = prayer_times
        self.state = self._create_state(self.state.name)

    def _create_state(self, state_name: str) -> BaseState:
        if state_name == "base_state":
            return BaseScreenState(self.session, self.tasks, self.prayer_times)
        if state_name == "task_info_state":
            return TaskInfoState(self.session, self.tasks)
        if state_name == "tasks_map_state":
            return TasksMapState(self.session, self.tasks)
        if state_name == "day_review_state":
            return DayReviewState(self.session, self.tasks)
        if state_name == "eid_state":
            return EidState(self.session)
        raise ValueError(f"Неизвестное состояние: {state_name}")

    def show(self) -> dict:
        return self.state.show()

    def handle_command(self, command: str, payload: dict | None = None) -> dict:
        if command == self.settings.secret_celebration_command:
            self.state = self._create_state("eid_state")
            return self.show()

        next_state_name = self.state.handle_command(command, payload)
        if next_state_name:
            self.state = self._create_state(next_state_name)
        ui_payload = self.show()

        if self.state.name == "tasks_map_state" and command in {"ok", "open_selected_day"} and self.session.selected_day > self.session.current_day + 2:
            ui_payload["warning"] = "Задание открыть нельзя!"

        return ui_payload
