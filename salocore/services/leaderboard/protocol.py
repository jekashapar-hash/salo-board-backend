from typing import Protocol


class LeaderboardServiceProtocol(Protocol):
    def get_leaderboard(self, tournament) -> list[dict]: ...

    def get_team_round_details(self, tournament, team) -> list[dict]: ...
