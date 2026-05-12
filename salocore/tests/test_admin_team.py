"""
Тести для адмін-ендпоінтів команд:
  - GET   /api/admin/tournaments/<id>/teams
  - PATCH /api/admin/tournaments/<id>/teams/<id>/disqualify
  - GET   /api/admin/tournaments/<id>/teams/<id>/participants
  - PATCH /api/admin/tournaments/<id>/teams/<id>/participants/<uid>
  - DELETE /api/admin/tournaments/<id>/teams/<id>/participants/<uid>
"""

import pytest
from django.utils import timezone
from rest_framework import status

from salocore.models import Team, TeamMember, Tournament, User


def admin_teams_url(tid):
    return f"/api/admin/tournaments/{tid}/teams"


def admin_team_disqualify_url(tid, team_id):
    return f"/api/admin/tournaments/{tid}/teams/{team_id}/disqualify"


def admin_participants_url(tid, team_id):
    return f"/api/admin/tournaments/{tid}/teams/{team_id}/participants"


def admin_participant_detail_url(tid, team_id, uid):
    return f"/api/admin/tournaments/{tid}/teams/{team_id}/participants/{uid}"


# ─────────────────── Fixtures ──────────────────────────────────────────


@pytest.fixture
def admin_team(db, tournament, user):
    """Команда з user як капітаном у турнірі tournament."""
    t = Team.objects.create(
        tournament=tournament, name="Admin Team", status=Team.Status.REGISTRATED
    )
    TeamMember.objects.create(team=t, user=user, is_captain=True)
    return t


@pytest.fixture
def second_member(db, admin_team):
    """Другий учасник команди admin_team."""
    member = User.objects.create_user(
        username="member2", email="member2@mail.com",
        password="Pass123!", invite_code="MEM2CODE",
    )
    TeamMember.objects.create(team=admin_team, user=member, is_captain=False)
    return member


# ─────────────────── AdminTeamListView ────────────────────────────────


@pytest.mark.django_db
class TestAdminTeamList:

    def test_lists_all_teams(self, admin_client, tournament, admin_team):
        response = admin_client.get(admin_teams_url(tournament.id))
        assert response.status_code == status.HTTP_200_OK
        ids = [t["id"] for t in response.data]
        assert admin_team.id in ids

    def test_returns_403_for_regular_user(self, auth_client_only, tournament):
        response = auth_client_only.get(admin_teams_url(tournament.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_401_unauthenticated(self, api_client, tournament):
        response = api_client.get(admin_teams_url(tournament.id))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ─────────────────── AdminTeamDisqualifyView ──────────────────────────


@pytest.mark.django_db
class TestAdminTeamDisqualify:

    def test_disqualifies_team(self, admin_client, tournament, admin_team):
        response = admin_client.patch(
            admin_team_disqualify_url(tournament.id, admin_team.id)
        )
        assert response.status_code == status.HTTP_200_OK
        admin_team.refresh_from_db()
        assert admin_team.status == Team.Status.DISQUALIFIED

    def test_returns_404_nonexistent_team(self, admin_client, tournament):
        response = admin_client.patch(admin_team_disqualify_url(tournament.id, 99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_403_for_regular_user(self, auth_client_only, tournament, admin_team):
        response = auth_client_only.patch(
            admin_team_disqualify_url(tournament.id, admin_team.id)
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────── AdminParticipantListView ─────────────────────────


@pytest.mark.django_db
class TestAdminParticipantList:

    def test_lists_members(self, admin_client, tournament, admin_team, user):
        response = admin_client.get(admin_participants_url(tournament.id, admin_team.id))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_returns_403_for_regular_user(self, auth_client_only, tournament, admin_team):
        response = auth_client_only.get(
            admin_participants_url(tournament.id, admin_team.id)
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────── AdminParticipantDetailView ───────────────────────


@pytest.mark.django_db
class TestAdminParticipantDetail:

    def test_patch_transfers_captain(
        self, admin_client, tournament, admin_team, user, second_member
    ):
        """PATCH → другий учасник стає капітаном, старий капітан — ні."""
        response = admin_client.patch(
            admin_participant_detail_url(tournament.id, admin_team.id, second_member.id)
        )
        assert response.status_code == status.HTTP_200_OK

        old_captain = TeamMember.objects.get(team=admin_team, user=user)
        new_captain = TeamMember.objects.get(team=admin_team, user=second_member)
        assert new_captain.is_captain is True
        assert old_captain.is_captain is False

    def test_patch_returns_404_nonexistent_member(
        self, admin_client, tournament, admin_team
    ):
        response = admin_client.patch(
            admin_participant_detail_url(tournament.id, admin_team.id, 99999)
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_removes_member(
        self, admin_client, tournament, admin_team, second_member
    ):
        response = admin_client.delete(
            admin_participant_detail_url(tournament.id, admin_team.id, second_member.id)
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not TeamMember.objects.filter(
            team=admin_team, user=second_member
        ).exists()

    def test_delete_returns_404_nonexistent_member(
        self, admin_client, tournament, admin_team
    ):
        response = admin_client.delete(
            admin_participant_detail_url(tournament.id, admin_team.id, 99999)
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_returns_403_for_regular_user(
        self, auth_client_only, tournament, admin_team, second_member
    ):
        response = auth_client_only.delete(
            admin_participant_detail_url(tournament.id, admin_team.id, second_member.id)
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
