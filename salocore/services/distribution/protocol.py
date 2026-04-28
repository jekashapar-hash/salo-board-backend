from typing import Protocol

from salocore.models.round import Round


class DistributionServiceProtocol(Protocol):
    def distribute(self, round: Round) -> None: ...
