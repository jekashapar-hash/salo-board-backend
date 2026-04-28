from salocore.models import Notification, Round, Team, Tournament
from salocore.repositories.notification.dto import MessageDTO
from salocore.repositories.notification.factory import NotificationFactoryProtocol
from salocore.repositories.user.protocol import UserRepositoryProtocol


class NotificationServiceImpl:
    def __init__(self, repository_factory: NotificationFactoryProtocol, user_repository: UserRepositoryProtocol):
        self.__repository_factory = repository_factory
        self.__user_repository = user_repository

    # ── Tournament lifecycle ────────────────────────────────────────────────

    def reg_start(self, tournament: Tournament) -> None:
        self._broadcast_to_participants(tournament.id, self.__get_reg_start_message(tournament))

    def reg_end(self, tournament: Tournament) -> None:
        self._broadcast_to_participants(tournament.id, self.__get_reg_end_message(tournament))

    def finish_tournament(self, tournament: Tournament) -> None:
        self._broadcast_to_participants(tournament.id, self.__get_finish_tournament_message(tournament))

    # ── Round lifecycle ─────────────────────────────────────────────────────

    def start_round(self, round: Round) -> None:
        self._broadcast_to_participants(round.tournament_id, self.__get_start_round_message(round))

    def close_submissions(self, round: Round) -> None:
        self._broadcast_to_participants(round.tournament_id, self.__get_close_submissions_message(round))

    def finish_evaluation(self, round: Round) -> None:
        self._broadcast_to_participants(round.tournament_id, self.__get_finish_evaluation_message(round))

    # ── Invitations & kicks ─────────────────────────────────────────────────

    def team_invite(self, team: Team, target_user_id: int) -> None:
        self._send_to_user(target_user_id, self.__get_team_invite_message(team))

    def jury_invite(self, tournament: Tournament, target_user_id: int) -> None:
        self._send_to_user(target_user_id, self.__get_jury_invite_message(tournament))

    def admin_invite(self, tournament: Tournament, target_user_id: int) -> None:
        self._send_to_user(target_user_id, self.__get_admin_invite_message(tournament))

    def kicked_from_team(self, team: Team, target_user_id: int) -> None:
        self._send_to_user(target_user_id, self.__get_kicked_from_team_message(team))

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _broadcast_to_participants(self, tournament_id: int, message: MessageDTO) -> None:
        for user_profile in self.__user_repository.get_tournament_participants(tournament_id):
            for repo in self.__repository_factory.smart_make(user_profile):
                repo.send(message, user_profile)

    def _send_to_user(self, user_id: int, message: MessageDTO) -> None:
        user_profile = self.__user_repository.get_profile(user_id)
        for repo in self.__repository_factory.smart_make(user_profile):
            repo.send(message, user_profile)

    # ── Message builders ────────────────────────────────────────────────────

    def __get_reg_start_message(self, tournament: Tournament) -> MessageDTO:
        return MessageDTO(
            text=f"Реєстрація на турнір {tournament.title} відкрита!",
            title="Відкриття реєстрації",
            type=Notification.Type.TOURNAMENT_REG_START,
            action_type=Notification.ActionType.NONE,
            targetid=tournament.id,
            target="tournament",
            action_url=f"/tournaments/{tournament.id}",
        )

    def __get_reg_end_message(self, tournament: Tournament) -> MessageDTO:
        return MessageDTO(
            text=f"Реєстрація на турнір {tournament.title} завершена.",
            title="Закриття реєстрації",
            type=Notification.Type.TOURNAMENT_REG_END,
            action_type=Notification.ActionType.NONE,
            targetid=tournament.id,
            target="tournament",
            action_url=f"/tournaments/{tournament.id}",
        )

    def __get_finish_tournament_message(self, tournament: Tournament) -> MessageDTO:
        return MessageDTO(
            text=f"Турнір {tournament.title} завершено!",
            title="Завершення турніру",
            type=Notification.Type.TOURNAMENT_FINISHED,
            action_type=Notification.ActionType.NONE,
            targetid=tournament.id,
            target="tournament",
            action_url=f"/tournaments/{tournament.id}",
        )

    def __get_start_round_message(self, round: Round) -> MessageDTO:
        return MessageDTO(
            text=f"Розпочався етап {round.title}!",
            title="Початок етапу",
            type=Notification.Type.ROUND_STARTED,
            action_type=Notification.ActionType.NONE,
            targetid=round.id,
            target="round",
            action_url=f"/tournaments/{round.tournament_id}/rounds/{round.id}",
        )

    def __get_close_submissions_message(self, round: Round) -> MessageDTO:
        return MessageDTO(
            text=f"Прийом рішень для етапу {round.title} завершено.",
            title="Закінчення прийому рішень",
            type=Notification.Type.SUBMISSION_FINISHED,
            action_type=Notification.ActionType.NONE,
            targetid=round.id,
            target="round",
            action_url=f"/tournaments/{round.tournament_id}/rounds/{round.id}",
        )

    def __get_finish_evaluation_message(self, round: Round) -> MessageDTO:
        return MessageDTO(
            text=f"Оцінювання етапу {round.title} завершено.",
            title="Закінчення оцінювання",
            type=Notification.Type.EVALUATION_FINISHED,
            action_type=Notification.ActionType.NONE,
            targetid=round.id,
            target="round",
            action_url=f"/tournaments/{round.tournament_id}/rounds/{round.id}",
        )

    def __get_team_invite_message(self, team: Team) -> MessageDTO:
        return MessageDTO(
            text=f"Вас запросили до команди {team.name} на турнірі {team.tournament.title}.",
            title=f"Запрошення до команди {team.name}",
            type=Notification.Type.TEAM_INVITE,
            action_type=Notification.ActionType.YES_NO,
            targetid=team.id,
            target="team",
            action_url=f"/tournaments/{team.tournament_id}?team_id={team.id}",
            how_long_active_days=3,
        )

    def __get_jury_invite_message(self, tournament: Tournament) -> MessageDTO:
        return MessageDTO(
            text=f"Вас запросили як члена журі на турнір {tournament.title}.",
            title="Запрошення до журі",
            type=Notification.Type.JURY_INVITE,
            action_type=Notification.ActionType.NONE,
            targetid=tournament.id,
            target="tournament",
            action_url=f"/tournaments/{tournament.id}",
            how_long_active_days=7,
        )

    def __get_admin_invite_message(self, tournament: Tournament) -> MessageDTO:
        return MessageDTO(
            text=f"Вас додано як адміністратора турніру {tournament.title}.",
            title="Запрошення адміністратора",
            type=Notification.Type.ADMIN_INVITE,
            action_type=Notification.ActionType.NONE,
            targetid=tournament.id,
            target="tournament",
            action_url=f"/tournaments/{tournament.id}",
            how_long_active_days=7,
        )

    def __get_kicked_from_team_message(self, team: Team) -> MessageDTO:
        return MessageDTO(
            text=f"Вас виключено з команди {team.name} на турнірі {team.tournament.title}.",
            title="Виключення з команди",
            type=Notification.Type.KICKED_FROM_TEAM,
            action_type=Notification.ActionType.NONE,
            targetid=team.id,
            target="team",
            action_url=f"/tournaments/{team.tournament_id}",
        )
