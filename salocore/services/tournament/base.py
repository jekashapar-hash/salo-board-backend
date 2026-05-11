from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime

from django.utils import timezone

from salocore.models import Tournament
from salocore.repositories.tournament.protocol import TournamentRepositoryProtocol


class TournamentStatusManagerBase(ABC):
    def __init__(self, tournament_repository: TournamentRepositoryProtocol) -> None:
        self.__tournament_repository = tournament_repository

    def check_status(self, on_notify: Callable[[Tournament], None] | None = None) -> None:
        tournaments = self.__tournament_repository.get_by_status(self._get_source_status())
        now = timezone.now()
        for tournament in tournaments:
            if self._is_check(tournament, now):
                self.__tournament_repository.update_status(tournament.id, self._get_target_status())
                if on_notify is not None:
                    on_notify(tournament)

    @abstractmethod
    def _get_source_status(self) -> Tournament.Status: ...

    @abstractmethod
    def _get_target_status(self) -> Tournament.Status: ...

    @abstractmethod
    def _is_check(self, tournament: Tournament, time: datetime) -> bool: ...
