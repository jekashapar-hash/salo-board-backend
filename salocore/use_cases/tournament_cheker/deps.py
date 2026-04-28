from salocore.services.notification.deps import get_notification_service
from salocore.services.tournament.deps import (
    get_tournament_archive,
    get_tournament_close_registration,
    get_tournament_finish,
    get_tournament_start_registration,
)

from .impl import TournamentCheker
from .protocol import TournamentChekerProtocol


def get_tournament_cheker() -> TournamentChekerProtocol:
    return TournamentCheker(
        start_registration_service=get_tournament_start_registration(),
        close_registration_service=get_tournament_close_registration(),
        finish_tournament_service=get_tournament_finish(),
        archive_tournament_service=get_tournament_archive(),
        notification_service=get_notification_service(),
    )
