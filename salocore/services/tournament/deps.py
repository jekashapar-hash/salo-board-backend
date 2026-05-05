from salocore.repositories.tournament.deps import get_tournament_repository
from salocore.services.tournament.protocol import TournamentStatusManagerProtocol

from .archive_tournament import TournamentArchive
from .close_registration import TournamentCloseRegistration
from .finish_tournament import TournamentFinish
from .start_registration import TournamentStartRegistration


def get_tournament_start_registration() -> TournamentStatusManagerProtocol:
    return TournamentStartRegistration(tournament_repository=get_tournament_repository())


def get_tournament_close_registration() -> TournamentStatusManagerProtocol:
    return TournamentCloseRegistration(tournament_repository=get_tournament_repository())


def get_tournament_finish() -> TournamentStatusManagerProtocol:
    return TournamentFinish(tournament_repository=get_tournament_repository())


def get_tournament_archive() -> TournamentStatusManagerProtocol:
    return TournamentArchive(tournament_repository=get_tournament_repository())
