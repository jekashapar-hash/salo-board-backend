from datetime import datetime

from salocore.models import Tournament

from .base import TournamentStatusManagerBase


class TournamentStartRegistration(TournamentStatusManagerBase):
    def _get_source_status(self) -> Tournament.Status:
        return Tournament.Status.DRAFT

    def _get_target_status(self) -> Tournament.Status:
        return Tournament.Status.REGISTRATION

    def _is_check(self, tournament: Tournament, time: datetime) -> bool:
        return tournament.reg_open_at <= time
