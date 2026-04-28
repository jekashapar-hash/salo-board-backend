"""
Celery-задачи периодической проверки состояния раундов и турниров.

Запускаются автоматически по расписанию Celery Beat (интервал задаётся
переменной CHECKER_INTERVAL_MINUTES в .env, по умолчанию — 15 минут).
"""

from celery import shared_task

from salocore.services.distribution.deps import get_distribution_service
from salocore.services.notification.deps import get_notification_service
from salocore.services.round.deps import (
    get_round_close_evaluations,
    get_round_close_submissions,
    get_round_start,
)
from salocore.services.tournament.deps import (
    get_tournament_archive,
    get_tournament_close_registration,
    get_tournament_finish,
    get_tournament_start_registration,
)
from salocore.use_cases.round_cheker.impl import RoundCheker
from salocore.use_cases.tournament_cheker.impl import TournamentCheker


@shared_task(name="salocore.tasks.run_round_checker", bind=True, max_retries=3)
def run_round_checker(self) -> None:  # type: ignore[override]
    """
    Периодическая проверка статусов раундов:
      - открытие раунда (START)
      - закрытие приёма работ (CLOSE_SUBMISSIONS)
      - закрытие оценивания (CLOSE_EVALUATIONS)
    """
    try:
        checker = RoundCheker(
            start_round_service=get_round_start(),
            close_submissions_service=get_round_close_submissions(),
            close_evaluations_service=get_round_close_evaluations(),
            distribution_service=get_distribution_service(),
            notification_service=get_notification_service(),
        )
        checker.check()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60) from exc


@shared_task(name="salocore.tasks.run_tournament_checker", bind=True, max_retries=3)
def run_tournament_checker(self) -> None:  # type: ignore[override]
    """
    Периодическая проверка статусов турниров:
      - начало регистрации (START_REGISTRATION)
      - закрытие регистрации (CLOSE_REGISTRATION)
      - завершение турнира (FINISH)
      - архивация турнира (ARCHIVE)
    """
    try:
        checker = TournamentCheker(
            start_registration_service=get_tournament_start_registration(),
            close_registration_service=get_tournament_close_registration(),
            finish_tournament_service=get_tournament_finish(),
            archive_tournament_service=get_tournament_archive(),
            notification_service=get_notification_service(),
        )
        checker.check()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60) from exc
