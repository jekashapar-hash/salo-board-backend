from salocore.repositories.evaluation.deps import get_evaluation_repository
from salocore.repositories.round.deps import get_round_repository
from salocore.repositories.submission.deps import get_submission_repository
from salocore.repositories.team.deps import get_team_repository
from salocore.services.round.protocol import RoundStatusManagerProtocol

from .close_evaluations import RoundCloseEvaluations
from .close_submissions import RoundCloseSubmissions
from .start_round import RoundStart


def get_round_start() -> RoundStatusManagerProtocol:
    return RoundStart(round_repository=get_round_repository())


def get_round_close_submissions() -> RoundStatusManagerProtocol:
    return RoundCloseSubmissions(
        round_repository=get_round_repository(),
        team_repository=get_team_repository(),
        submission_repository=get_submission_repository(),
    )


def get_round_close_evaluations() -> RoundStatusManagerProtocol:
    return RoundCloseEvaluations(
        round_repository=get_round_repository(),
        evaluation_repository=get_evaluation_repository(),
    )
