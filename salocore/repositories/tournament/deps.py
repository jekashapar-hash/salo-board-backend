from .impl import TournamentRepositoryImpl
from .protocol import TournamentRepositoryProtocol


def get_tournament_repository() -> TournamentRepositoryProtocol:
    return TournamentRepositoryImpl()
