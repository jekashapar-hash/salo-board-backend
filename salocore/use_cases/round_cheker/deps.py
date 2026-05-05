from salocore.services.distribution.deps import get_distribution_service
from salocore.services.notification.deps import get_notification_service
from salocore.services.round.deps import (
    get_round_close_evaluations,
    get_round_close_submissions,
    get_round_start,
)

from .impl import RoundCheker
from .protocol import RoundChekerProtocol


def get_round_cheker() -> RoundChekerProtocol:
    return RoundCheker(
        start_round_service=get_round_start(),
        close_submissions_service=get_round_close_submissions(),
        close_evaluations_service=get_round_close_evaluations(),
        distribution_service=get_distribution_service(),
        notification_service=get_notification_service(),
    )
