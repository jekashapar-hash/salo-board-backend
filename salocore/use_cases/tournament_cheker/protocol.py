from typing import Protocol


class TournamentChekerProtocol(Protocol):
    def check(self) -> None: ...
