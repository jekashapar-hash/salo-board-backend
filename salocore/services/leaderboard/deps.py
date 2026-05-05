from salocore.repositories.leaderboard.deps import get_leaderboard_repository

from .impl import LeaderboardService
from .protocol import LeaderboardServiceProtocol


def get_leaderboard_service() -> LeaderboardServiceProtocol:
    return LeaderboardService(leaderboard_repository=get_leaderboard_repository())
