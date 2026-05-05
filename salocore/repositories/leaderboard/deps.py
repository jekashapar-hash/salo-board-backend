from .impl import LeaderboardRepositoryImpl
from .protocol import LeaderboardRepositoryProtocol


def get_leaderboard_repository() -> LeaderboardRepositoryProtocol:
    return LeaderboardRepositoryImpl()
