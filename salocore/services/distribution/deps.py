from salocore.repositories.evaluation.deps import get_evaluation_repository
from salocore.repositories.submission.deps import get_submission_repository
from salocore.repositories.user.deps import get_user_repository

from .impl import DistributionServiceImpl
from .protocol import DistributionServiceProtocol


def get_distribution_service() -> DistributionServiceProtocol:
    return DistributionServiceImpl(
        submission_repository=get_submission_repository(),
        user_repository=get_user_repository(),
        evaluation_repository=get_evaluation_repository(),
    )
