from typing import Protocol

from salocore.models.round import Round


class RoundRepositoryProtocol(Protocol):
    def get_by_status(self, status: Round.Status) -> list[Round]: ...

    def update_status(self, round_id: int, status: Round.Status) -> None: ...
