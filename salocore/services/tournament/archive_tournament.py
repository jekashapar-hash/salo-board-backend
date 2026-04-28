from datetime import datetime, timedelta

from salocore.models import Tournament

from .base import TournamentStatusManagerBase


class TournamentArchive(TournamentStatusManagerBase):
    def _get_source_status(self) -> Tournament.Status:
        return Tournament.Status.FINISHED

    def _get_target_status(self) -> Tournament.Status:
        return Tournament.Status.ARCHIVED

    def _is_check(self, tournament: Tournament, time: datetime) -> bool:
        return tournament.ended_at + timedelta(days=10) <= time
