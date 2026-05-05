from salocore.services.leaderboard.deps import get_leaderboard_service

from .impl import LeaderboardUseCase
from .protocol import LeaderboardUseCaseProtocol


def get_leaderboard_use_case() -> LeaderboardUseCaseProtocol:
    return LeaderboardUseCase(leaderboard_service=get_leaderboard_service())
