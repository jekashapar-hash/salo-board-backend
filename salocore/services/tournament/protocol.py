from collections.abc import Callable
from typing import Protocol

from salocore.models.tournament import Tournament


class TournamentStatusManagerProtocol(Protocol):
    def check_status(self, on_notify: Callable[[Tournament], None] | None = None) -> None: ...
