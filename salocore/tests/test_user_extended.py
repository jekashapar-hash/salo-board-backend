"""
Тести для розширених view профілю:
  - GET /api/user/roles      → UserRolesView
  - GET /api/user/tournament-history → UserTournamentHistoryView
  - GET /api/user/submissions → UserSubmissionsView
"""

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from salocore.models import Round, Submission, Team, TeamMember, Tournament, TournamentAdmin, TournamentJury

# ─────────────────────────── UserRolesView ───────────────────────────


@pytest.mark.django_db
class TestUserRoles:
    url = reverse("user-roles")

    def test_returns_200(self, auth_client_only):
        response = auth_client_only.get(self.url)
        assert response.status_code == status.HTTP_200_OK

    def test_returns_401_unauthenticated(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_all_roles_false_by_default(self, auth_client_only):
        """Новий звичайний юзер — всі ролі False."""
        response = auth_client_only.get(self.url)
        assert response.data["participant"] is False
        assert response.data["jury"] is False
        assert response.data["admin"] is False

    def test_admin_true_for_staff(self, admin_client):
        """is_staff=True → admin=True."""
        response = admin_client.get(self.url)
        assert response.data["admin"] is True

    def test_participant_true_when_in_active_tournament(self, auth_client_only, team, tournament):
        """Юзер є учасником команди у REGISTRATION → participant=True."""
        assert tournament.status == Tournament.Status.REGISTRATION
        response = auth_client_only.get(self.url)
        assert response.data["participant"] is True

    def test_participant_false_for_finished_tournament(self, auth_client_only, user, tournament_finished):
        """FINISHED турнір не рахується → participant=False."""
        t = Team.objects.create(tournament=tournament_finished, name="T", status=Team.Status.REGISTRATED)
        TeamMember.objects.create(team=t, user=user, is_captain=True)
        response = auth_client_only.get(self.url)
        assert response.data["participant"] is False

    def test_jury_true_when_assigned_to_active_tournament(self, auth_client_only, user, tournament):
        """TournamentJury в REGISTRATION турнірі → jury=True."""
        TournamentJury.objects.create(tournament=tournament, user=user)
        response = auth_client_only.get(self.url)
        assert response.data["jury"] is True

    def test_jury_false_for_finished_tournament(self, auth_client_only, user, tournament_finished):
        """TournamentJury в FINISHED турнірі → jury=False."""
        TournamentJury.objects.create(tournament=tournament_finished, user=user)
        response = auth_client_only.get(self.url)
        assert response.data["jury"] is False


# ────────────────────── UserTournamentHistoryView ─────────────────────


@pytest.mark.django_db
class TestUserTournamentHistory:
    url = reverse("user-tournament-history")

    def test_returns_200(self, auth_client_only):
        response = auth_client_only.get(self.url)
        assert response.status_code == status.HTTP_200_OK

    def test_returns_401_unauthenticated(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_when_no_participation(self, auth_client_only):
        response = auth_client_only.get(self.url)
        assert response.data == []

    def test_participant_role_appears(self, auth_client_only, team, tournament):
        response = auth_client_only.get(self.url)
        roles = [item["role"] for item in response.data]
        assert "participant" in roles

    def test_jury_role_appears(self, auth_client_only, user, tournament):
        TournamentJury.objects.create(tournament=tournament, user=user)
        response = auth_client_only.get(self.url)
        roles = [item["role"] for item in response.data]
        assert "jury" in roles

    def test_admin_role_appears(self, auth_client_only, user, tournament):
        TournamentAdmin.objects.create(tournament=tournament, user=user)
        response = auth_client_only.get(self.url)
        roles = [item["role"] for item in response.data]
        assert "admin" in roles

    def test_multiple_roles_in_same_tournament(self, auth_client_only, user, team, tournament):
        """Якщо юзер є і учасником, і журі — два записи."""
        TournamentJury.objects.create(tournament=tournament, user=user)
        response = auth_client_only.get(self.url)
        tournament_ids = [item["id"] for item in response.data]
        assert tournament_ids.count(tournament.id) >= 2

    def test_active_tournaments_sorted_first(self, auth_client_only, user, tournament, tournament_finished):
        """REGISTRATION/RUNNING йдуть першими."""
        t_finished = Team.objects.create(tournament=tournament_finished, name="OldTeam", status=Team.Status.REGISTRATED)
        TeamMember.objects.create(team=t_finished, user=user, is_captain=True)
        # user є учасником team (tournament=REGISTRATION) завдяки фікстурі team (якщо передати)
        TournamentJury.objects.create(tournament=tournament, user=user)

        response = auth_client_only.get(self.url)
        statuses = [item["status"] for item in response.data]
        active = {Tournament.Status.REGISTRATION, Tournament.Status.RUNNING}
        # Перший запис — з активного турніру
        assert statuses[0] in active

    def test_response_contains_expected_fields(self, auth_client_only, team):
        response = auth_client_only.get(self.url)
        assert len(response.data) > 0
        item = response.data[0]
        for field in ("id", "title", "status", "role"):
            assert field in item


# ───────────────────────── UserSubmissionsView ────────────────────────


@pytest.mark.django_db
class TestUserSubmissions:
    url = reverse("user-submissions")

    def test_returns_200(self, auth_client_only):
        response = auth_client_only.get(self.url)
        assert response.status_code == status.HTTP_200_OK

    def test_returns_401_unauthenticated(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_when_no_teams(self, auth_client_only):
        response = auth_client_only.get(self.url)
        assert response.data == []

    def test_returns_submissions_for_user_teams(self, auth_client_only, team, tournament_running, admin_user, factory):
        """Якщо команда юзера має сабміт — він повертається."""
        round_obj = factory.create_round(tournament_running, status=Round.Status.ACTIVE)
        # Прив'язуємо команду до running-турніру
        team_running = Team.objects.create(tournament=tournament_running, name="MyTeam", status=Team.Status.REGISTRATED)
        # user вже є в auth_client_only
        # Отримаємо user з команди team (фікстура)
        member = TeamMember.objects.filter(team=team).first()
        TeamMember.objects.create(team=team_running, user=member.user, is_captain=True)

        factory.create_submission(team_running, round_obj)
        response = auth_client_only.get(self.url)
        assert len(response.data) >= 1

    def test_response_contains_expected_fields(self, auth_client_only, team, tournament_running, factory):
        """Перевірка структури відповіді."""
        round_obj = factory.create_round(tournament_running, status=Round.Status.ACTIVE)
        team_running = Team.objects.create(
            tournament=tournament_running, name="MyTeam2", status=Team.Status.REGISTRATED
        )
        member = TeamMember.objects.filter(team=team).first()
        TeamMember.objects.create(team=team_running, user=member.user, is_captain=True)
        factory.create_submission(team_running, round_obj)

        response = auth_client_only.get(self.url)
        assert len(response.data) >= 1
        item = response.data[0]
        for field in ("id", "status", "team_id", "team_name", "round_id", "tournament_id"):
            assert field in item

    def test_ordered_by_created_at_desc(self, auth_client_only, team, tournament_running, factory):
        """Сабміти повертаються від новішого до старішого."""
        round1 = factory.create_round(tournament_running, title="R1", status=Round.Status.ACTIVE)
        round2 = factory.create_round(tournament_running, title="R2", status=Round.Status.ACTIVE)
        team_running = Team.objects.create(
            tournament=tournament_running, name="MyTeam3", status=Team.Status.REGISTRATED
        )
        member = TeamMember.objects.filter(team=team).first()
        TeamMember.objects.create(team=team_running, user=member.user, is_captain=True)
        s1 = factory.create_submission(team_running, round1)
        # Мануально зміщуємо час створення s1 у минуле
        Submission.objects.filter(id=s1.id).update(created_at=timezone.now() - timezone.timedelta(seconds=10))
        s2 = factory.create_submission(team_running, round2)

        response = auth_client_only.get(self.url)
        ids = [item["id"] for item in response.data]
        assert ids.index(s2.id) < ids.index(s1.id)
