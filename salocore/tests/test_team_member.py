"""
Тести для учасників команди:
  - GET  /api/teams/<id>/participant           → TeamParticipantListCreateView
  - POST /api/teams/<id>/participant           → TeamParticipantListCreateView
  - DELETE /api/teams/<id>/participant/<uid>   → TeamParticipantDetailView
  - GET  /api/teams/<id>/participant/can-add   → TeamCanCreateParticipantView
"""

from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status

from salocore.models import Team, TeamMember, Tournament, User


def participants_url(team_id):
    return f"/api/teams/{team_id}/participant"


def participant_detail_url(team_id, user_id):
    return f"/api/teams/{team_id}/participant/{user_id}"


def can_add_url(team_id):
    return f"/api/teams/{team_id}/participant/can-add"


# ─────────────────────── Fixtures ─────────────────────────────────────


@pytest.fixture
def captain_user(db):
    return User.objects.create_user(
        username="captain", email="captain@mail.com",
        password="CaptPass123!", invite_code="CAPTCODE",
    )


@pytest.fixture
def captain_client(api_client, captain_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(captain_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def member_user(db):
    return User.objects.create_user(
        username="member", email="member@mail.com",
        password="MembPass123!", invite_code="MEMBCODE",
    )


@pytest.fixture
def member_client(api_client, member_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(member_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def reg_tournament(db, admin_user, factory):
    return factory.create_tournament(admin_user, title="Reg T", status=Tournament.Status.REGISTRATION)


@pytest.fixture
def captain_team(db, reg_tournament, captain_user):
    t = Team.objects.create(
        tournament=reg_tournament, name="CaptTeam", status=Team.Status.REGISTRATED
    )
    TeamMember.objects.create(team=t, user=captain_user, is_captain=True)
    return t


@pytest.fixture
def member_team(db, captain_team, member_user):
    """Команда де є і captain і member."""
    TeamMember.objects.create(team=captain_team, user=member_user, is_captain=False)
    return captain_team


# ──────────────────── TeamParticipantListCreateView GET ───────────────


@pytest.mark.django_db
class TestTeamParticipantListGet:

    def test_returns_200_for_member(self, captain_client, captain_team):
        response = captain_client.get(participants_url(captain_team.id))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_403_for_non_member(self, other_client, captain_team):
        response = other_client.get(participants_url(captain_team.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_401_unauthenticated(self, api_client, captain_team):
        response = api_client.get(participants_url(captain_team.id))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_lists_all_members(self, captain_client, member_team):
        response = captain_client.get(participants_url(member_team.id))
        assert len(response.data) == 2


# ──────────────────── TeamParticipantListCreateView POST ──────────────


@pytest.mark.django_db
class TestTeamParticipantCreate:

    def test_sends_invite_successfully(self, captain_client, captain_team, other_user):
        with patch("salocore.views.team_member.get_notification_service") as m:
            m.return_value.team_invite.return_value = None
            response = captain_client.post(
                participants_url(captain_team.id),
                {"invite_code": other_user.invite_code},
            )
        assert response.status_code == status.HTTP_201_CREATED

    def test_fails_if_not_captain(self, member_client, member_team):
        with patch("salocore.views.team_member.get_notification_service"):
            response = member_client.post(
                participants_url(member_team.id), {"invite_code": "ANYCODE"}
            )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_fails_if_registration_closed(self, captain_client, admin_user, captain_user, factory):
        running_t = factory.create_tournament(
            admin_user, title="Running", status=Tournament.Status.RUNNING
        )
        running_team = Team.objects.create(
            tournament=running_t, name="RTeam", status=Team.Status.REGISTRATED
        )
        TeamMember.objects.create(team=running_team, user=captain_user, is_captain=True)
        response = captain_client.post(
            participants_url(running_team.id), {"invite_code": "ANYCODE"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_fails_if_no_invite_code(self, captain_client, captain_team):
        response = captain_client.post(participants_url(captain_team.id), {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_fails_if_user_not_found(self, captain_client, captain_team):
        response = captain_client.post(
            participants_url(captain_team.id), {"invite_code": "NOTEXIST"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_fails_if_user_already_in_tournament(self, captain_client, member_team, member_user):
        with patch("salocore.views.team_member.get_notification_service"):
            response = captain_client.post(
                participants_url(member_team.id),
                {"invite_code": member_user.invite_code},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ──────────────────── TeamParticipantDetailView DELETE ────────────────


@pytest.mark.django_db
class TestTeamParticipantDelete:

    def test_member_can_leave_team(self, member_client, member_team, member_user):
        response = member_client.delete(
            participant_detail_url(member_team.id, "me")
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not TeamMember.objects.filter(team=member_team, user=member_user).exists()

    def test_captain_must_pass_new_captain_when_multiple_members(
        self, captain_client, member_team
    ):
        response = captain_client.delete(
            participant_detail_url(member_team.id, "me"), data={}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_captain_can_transfer_and_leave(self, captain_client, member_team, member_user):
        response = captain_client.delete(
            participant_detail_url(member_team.id, "me"),
            data={"new_captain_id": member_user.id},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert TeamMember.objects.get(team=member_team, user=member_user).is_captain

    def test_captain_can_kick_member(self, captain_client, member_team, member_user):
        response = captain_client.delete(
            participant_detail_url(member_team.id, member_user.id)
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_non_captain_cannot_kick(self, member_client, member_team, captain_user):
        response = member_client.delete(
            participant_detail_url(member_team.id, captain_user.id)
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_if_not_in_team(self, captain_client, captain_team, other_user):
        response = captain_client.delete(
            participant_detail_url(captain_team.id, other_user.id)
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ─────────────────── TeamCanCreateParticipantView ─────────────────────


@pytest.mark.django_db
class TestTeamCanAdd:

    def test_returns_true_for_captain_during_registration(self, captain_client, captain_team):
        response = captain_client.get(can_add_url(captain_team.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data is True

    def test_returns_false_for_non_captain(self, member_client, member_team):
        response = member_client.get(can_add_url(member_team.id))
        assert response.data is False

    def test_returns_false_when_registration_closed(self, captain_client, captain_user, admin_user, factory):
        running_t = factory.create_tournament(
            admin_user, title="Running2", status=Tournament.Status.RUNNING
        )
        running_team = Team.objects.create(
            tournament=running_t, name="RT2", status=Team.Status.REGISTRATED
        )
        TeamMember.objects.create(team=running_team, user=captain_user, is_captain=True)
        response = captain_client.get(can_add_url(running_team.id))
        assert response.data is False

    def test_returns_404_nonexistent_team(self, captain_client):
        response = captain_client.get(can_add_url(99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND
