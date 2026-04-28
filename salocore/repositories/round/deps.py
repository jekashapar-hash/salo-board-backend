from .impl import RoundRepositoryImpl
from .protocol import RoundRepositoryProtocol


def get_round_repository() -> RoundRepositoryProtocol:
    return RoundRepositoryImpl()
