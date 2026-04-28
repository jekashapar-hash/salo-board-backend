from typing import Protocol

from salocore.models import Tournament


class TournamentRepositoryProtocol(Protocol):
    def get_by_status(self, status: Tournament.Status) -> list[Tournament]: ...

    def update_status(self, tournament_id: int, status: str) -> None: ...
