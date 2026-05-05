from datetime import datetime

from salocore.models.round import Round

from .base import RoundStatusManagerBase


class RoundStart(RoundStatusManagerBase):
    def _get_source_status(self) -> Round.Status:
        return Round.Status.DRAFT

    def _get_target_status(self) -> Round.Status:
        return Round.Status.ACTIVE

    def _is_check(self, round: Round, time: datetime) -> bool:
        return round.start_at <= time
