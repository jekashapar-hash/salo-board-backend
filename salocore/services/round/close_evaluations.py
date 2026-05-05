from datetime import datetime

from salocore.models.round import Round
from salocore.repositories.evaluation.protocol import EvaluationRepositoryProtocol
from salocore.repositories.round.protocol import RoundRepositoryProtocol

from .base import RoundStatusManagerBase


class RoundCloseEvaluations(RoundStatusManagerBase):
    def __init__(
        self,
        round_repository: RoundRepositoryProtocol,
        evaluation_repository: EvaluationRepositoryProtocol,
    ) -> None:
        super().__init__(round_repository)
        self.__evaluation_repository = evaluation_repository

    def _get_source_status(self) -> Round.Status:
        return Round.Status.SUBMISSION_CLOSED

    def _get_target_status(self) -> Round.Status:
        return Round.Status.EVALUATED

    def _is_check(self, round: Round, time: datetime) -> bool:
        return self.__evaluation_repository.all_submitted_for_round(round.id)
