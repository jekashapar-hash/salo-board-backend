from salocore.services.leaderboard.protocol import LeaderboardServiceProtocol


class LeaderboardUseCase:
    def __init__(self, leaderboard_service: LeaderboardServiceProtocol) -> None:
        self._service = leaderboard_service

    def get_leaderboard(self, tournament) -> list[dict]:
        return self._service.get_leaderboard(tournament)

    def get_team_round_details(self, tournament, team) -> list[dict]:
        return self._service.get_team_round_details(tournament, team)
