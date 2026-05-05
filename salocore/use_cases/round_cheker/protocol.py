from typing import Protocol


class RoundChekerProtocol(Protocol):
    def check(self) -> None: ...
