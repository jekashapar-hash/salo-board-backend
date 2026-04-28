import itertools

from salocore.models.round import Round
from salocore.repositories.evaluation.protocol import EvaluationRepositoryProtocol
from salocore.repositories.submission.protocol import SubmissionRepositoryProtocol
from salocore.repositories.user.protocol import UserRepositoryProtocol

from .protocol import DistributionServiceProtocol


class DistributionServiceImpl(DistributionServiceProtocol):
    def __init__(
        self,
        submission_repository: SubmissionRepositoryProtocol,
        user_repository: UserRepositoryProtocol,
        evaluation_repository: EvaluationRepositoryProtocol,
    ) -> None:
        self.__submission_repository = submission_repository
        self.__user_repository = user_repository
        self.__evaluation_repository = evaluation_repository

    def distribute(self, round: Round) -> None:
        submissions = self.__submission_repository.get_submissions_by_round(round.id)
        if not submissions:
            return

        jury_ids = self.__user_repository.get_juries_ids(round.tournament_id)
        if not jury_ids:
            return

        juries_per_submission = min(len(jury_ids), 3)
        jury_cycle = itertools.cycle(jury_ids)

        submission_jury_pairs: list[tuple[int, int]] = []
        for submission in submissions:
            assigned_juries = [next(jury_cycle) for _ in range(juries_per_submission)]
            for jury_id in assigned_juries:
                submission_jury_pairs.append((submission.id, jury_id))

        if submission_jury_pairs:
            self.__evaluation_repository.create_evaluations(submission_jury_pairs)
