from datetime import datetime

from salocore.models.round import Round
from salocore.models.submission import Submission
from salocore.repositories.round.protocol import RoundRepositoryProtocol
from salocore.repositories.submission.protocol import SubmissionRepositoryProtocol
from salocore.repositories.team.protocol import TeamRepositoryProtocol

from .base import RoundStatusManagerBase


class RoundCloseSubmissions(RoundStatusManagerBase):
    def __init__(
        self,
        round_repository: RoundRepositoryProtocol,
        team_repository: TeamRepositoryProtocol,
        submission_repository: SubmissionRepositoryProtocol,
    ) -> None:
        super().__init__(round_repository)
        self.__team_repository = team_repository
        self.__submission_repository = submission_repository

    def _get_source_status(self) -> Round.Status:
        return Round.Status.ACTIVE

    def _get_target_status(self) -> Round.Status:
        return Round.Status.SUBMISSION_CLOSED

    def _is_check(self, round: Round, time: datetime) -> bool:
        return round.deadline <= time

    def _on_transition(self, round: Round) -> None:
        # Disqualify all teams that do not have a submission for this round
        teams_without_submission = self.__team_repository.get_teams_without_submission_for_round(round.id)
        for team in teams_without_submission:
            self.__team_repository.disqualify_team(team.id)

        # Change all submissions for this round to SUBMITTED
        submissions = self.__submission_repository.get_submissions_by_round(round.id)
        for submission in submissions:
            self.__submission_repository.change_submission_status(submission.id, Submission.Status.SUBMITTED)
