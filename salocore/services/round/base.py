from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timezone

from salocore.models.round import Round
from salocore.repositories.round.protocol import RoundRepositoryProtocol


class RoundStatusManagerBase(ABC):
    def __init__(self, round_repository: RoundRepositoryProtocol) -> None:
        self.__round_repository = round_repository

    def check_status(self, on_notify: Callable[[Round], None] | None = None) -> None:
        rounds = self.__round_repository.get_by_status(self._get_source_status())
        now = timezone.now()
        for round in rounds:
            if self._is_check(round, now):
                self.__round_repository.update_status(round.id, self._get_target_status())
                self._on_transition(round)
                if on_notify is not None:
                    on_notify(round)

    def _on_transition(self, round: Round) -> None:  # noqa: B027
        pass

    @abstractmethod
    def _get_source_status(self) -> Round.Status: ...

    @abstractmethod
    def _get_target_status(self) -> Round.Status: ...

    @abstractmethod
    def _is_check(self, round: Round, time: datetime) -> bool: ...
