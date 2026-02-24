from __future__ import annotations

from datetime import datetime
from typing import Callable

from models import AppSettings, PrayerTimes, Session, Task
from states import BaseScreenState, DayReviewState, EidState, TaskInfoState, TasksMapState
from states.base_state import BaseState


class StateManager:
    def __init__(
        self,
        session: Session,
        tasks: list[Task],
        settings: AppSettings,
        prayer_times: dict[str, PrayerTimes],
        now_provider: Callable[[], datetime] | None = None,
        prayer_overrides_provider: Callable[[], dict[str, str]] | None = None,
    ):
        self.session = session
        self.tasks = tasks
        self.settings = settings
        self.prayer_times = prayer_times
        self._now_provider = now_provider
        self._prayer_overrides_provider = prayer_overrides_provider
        self.state: BaseState = self._create_state("base_state")

    def refresh_data(self, tasks: list[Task], prayer_times: dict[str, PrayerTimes]) -> None:
        self.tasks = tasks
        self.prayer_times = prayer_times

        if hasattr(self.state, "tasks"):
            self.state.tasks = tasks
        if hasattr(self.state, "prayer_times"):
            self.state.prayer_times = prayer_times

    def _create_state(self, state_name: str) -> BaseState:
        if state_name == "base_state":
            return BaseScreenState(
                self.session,
                self.tasks,
                self.prayer_times,
                settings=self.settings,
                now_provider=self._now_provider,
                prayer_overrides_provider=self._prayer_overrides_provider,
            )
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
        return self.show()
