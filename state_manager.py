from __future__ import annotations

from models import Session
from states import CelebrationState, DayReviewState, SummaryState, TaskMapState
from states.base_state import BaseState


class StateManager:
    def __init__(self, session: Session):
        self.session = session
        self.state: BaseState = self._build_initial_state()

    def _build_initial_state(self) -> BaseState:
        if self.session.celebration_mode:
            return CelebrationState()
        return DayReviewState(self.session.current_day)

    def _create_state(self, state_name: str) -> BaseState:
        if state_name == "day_review":
            return DayReviewState(self.session.current_day)
        if state_name == "task_map":
            return TaskMapState(self.session.current_day)
        if state_name == "summary":
            return SummaryState(self.session.current_day)
        if state_name == "celebration":
            return CelebrationState()
        raise ValueError(f"Неизвестное состояние: {state_name}")

    def show(self) -> dict:
        return self.state.show()

    def handle_command(self, command: str, payload: dict | None = None) -> dict:
        next_state_name = self.state.handle_command(command, payload)
        if next_state_name:
            self.state = self._create_state(next_state_name)
        return self.show()
