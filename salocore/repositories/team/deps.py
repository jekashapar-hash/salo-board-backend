from .impl import TeamRepositoryImpl
from .protocol import TeamRepositoryProtocol


def get_team_repository() -> TeamRepositoryProtocol:
    return TeamRepositoryImpl()
