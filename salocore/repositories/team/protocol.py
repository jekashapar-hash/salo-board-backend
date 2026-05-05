from typing import Protocol

from salocore.models import Team


class TeamRepositoryProtocol(Protocol):
    def disqualify_team(self, team_id: int) -> None: ...

    def get_teams_without_submission_for_round(self, round_id: int) -> list[Team]: ...
