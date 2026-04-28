from salocore.services.notification.protocol import NotificationServiceProtocol
from salocore.services.tournament.protocol import TournamentStatusManagerProtocol


class TournamentCheker:
    def __init__(
        self,
        start_registration_service: TournamentStatusManagerProtocol,
        close_registration_service: TournamentStatusManagerProtocol,
        finish_tournament_service: TournamentStatusManagerProtocol,
        archive_tournament_service: TournamentStatusManagerProtocol,
        notification_service: NotificationServiceProtocol,
    ) -> None:
        self._start_registration_service = start_registration_service
        self._close_registration_service = close_registration_service
        self._finish_tournament_service = finish_tournament_service
        self._archive_tournament_service = archive_tournament_service
        self._notification_service = notification_service

    def check(self) -> None:
        self._start_registration_service.check_status(on_notify=self._notification_service.reg_start)
        self._close_registration_service.check_status(on_notify=self._notification_service.reg_end)
        self._finish_tournament_service.check_status(on_notify=self._notification_service.finish_tournament)
        self._archive_tournament_service.check_status()
