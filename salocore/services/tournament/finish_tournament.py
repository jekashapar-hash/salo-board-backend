from datetime import datetime

from salocore.models import Tournament

from .base import TournamentStatusManagerBase


class TournamentFinish(TournamentStatusManagerBase):
    def _get_source_status(self) -> Tournament.Status:
        return Tournament.Status.RUNNING

    def _get_target_status(self) -> Tournament.Status:
        return Tournament.Status.FINISHED

    def _is_check(self, tournament: Tournament, time: datetime) -> bool:
        return tournament.ended_at <= time
