from collections.abc import Callable
from typing import Protocol

from salocore.models.round import Round


class RoundStatusManagerProtocol(Protocol):
    def check_status(self, on_notify: Callable[[Round], None] | None = None) -> None: ...
