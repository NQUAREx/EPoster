from __future__ import annotations

from models import AppSettings, PrayerTimes, Session, Task
from states import CelebrationState, DayReviewState, HomeState, TaskMapState, TaskState
from states.base_state import BaseState


class StateManager:
    def __init__(self, session: Session, tasks: list[Task], settings: AppSettings, prayer_times: dict[str, PrayerTimes]):
        self.session = session
        self.tasks = tasks
        self.settings = settings
        self.prayer_times = prayer_times
        self.state: BaseState = self._build_initial_state()

    def _build_initial_state(self) -> BaseState:
        if self.session.celebration_mode:
            return CelebrationState(self.session)
        return HomeState(self.session, self.tasks, self.prayer_times)

    def _create_state(self, state_name: str) -> BaseState:
        if state_name == "base":
            return HomeState(self.session, self.tasks, self.prayer_times)
        if state_name == "day_review":
            return DayReviewState(self.session, self.tasks)
        if state_name == "task_map":
            return TaskMapState(self.session, self.tasks)
        if state_name == "task":
            return TaskState(self.session, self.tasks)
        if state_name == "eid":
            return CelebrationState(self.session)
        raise ValueError(f"Неизвестное состояние: {state_name}")

    def show(self) -> dict:
        return self.state.show()

    def handle_command(self, command: str, payload: dict | None = None) -> dict:
        if command == self.settings.secret_celebration_command:
            self.session.celebration_mode = True
            self.state = self._create_state("eid")
            return self.show()

        next_state_name = self.state.handle_command(command, payload)
        if next_state_name:
            self.state = self._create_state(next_state_name)
        return self.show()
