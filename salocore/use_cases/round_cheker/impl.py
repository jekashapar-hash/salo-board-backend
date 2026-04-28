from salocore.services.distribution.protocol import DistributionServiceProtocol
from salocore.services.notification.protocol import NotificationServiceProtocol
from salocore.services.round.protocol import RoundStatusManagerProtocol

from .protocol import RoundChekerProtocol


class RoundCheker(RoundChekerProtocol):
    def __init__(
        self,
        start_round_service: RoundStatusManagerProtocol,
        close_submissions_service: RoundStatusManagerProtocol,
        close_evaluations_service: RoundStatusManagerProtocol,
        distribution_service: DistributionServiceProtocol,
        notification_service: NotificationServiceProtocol,
    ) -> None:
        self._start_round_service = start_round_service
        self._close_submissions_service = close_submissions_service
        self._close_evaluations_service = close_evaluations_service
        self._distribution_service = distribution_service
        self._notification_service = notification_service

    def check(self) -> None:
        self._start_round_service.check_status(
            on_notify=self._notification_service.start_round
        )
        self._close_submissions_service.check_status(
            on_notify=self._distribution_service.distribute
        )
        self._close_evaluations_service.check_status(
            on_notify=self._notification_service.finish_evaluation
        )
