from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from salocore.models import Notification, Team, TeamMember


def team_invites_url(team_id):
    return f"/api/teams/{team_id}/invites"

@pytest.mark.django_db
class TestTeamInvitationList:
    def test_returns_200_for_member(self, auth_client_only, team):
        response = auth_client_only.get(team_invites_url(team.id))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_403_for_non_member(self, other_client, team):
        response = other_client.get(team_invites_url(team.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_for_nonexistent_team(self, auth_client_only):
        response = auth_client_only.get(team_invites_url(99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_only_team_specific_invites(self, auth_client_only, user, team, tournament, other_user):
        """Возвращает приглашения только для указанной команды."""
        now = timezone.now()
        
        # Команда пользователя (он в ней мембер по дефолту из фикстуры team?)
        # Уточним членство
        TeamMember.objects.get_or_create(team=team, user=user)
        
        # Приглашение от НАШЕЙ команды
        our_invite = Notification.objects.create(
            user=other_user,
            title="Our Invite",
            message="Join us",
            type=Notification.Type.TEAM_INVITE,
            action_type=Notification.ActionType.YES_NO,
            status=Notification.Status.UNREAD,
            action_url=f"/tournaments/{team.tournament_id}?team_id={team.id}",
            how_long_active=now + timedelta(days=1)
        )
        
        # Приглашение от ДРУГОЙ команды
        other_team = Team.objects.create(tournament=tournament, name="Other", status=Team.Status.REGISTRATED)
        other_invite = Notification.objects.create(
            user=other_user,
            title="Other Invite",
            message="Join them",
            type=Notification.Type.TEAM_INVITE,
            action_type=Notification.ActionType.YES_NO,
            status=Notification.Status.UNREAD,
            action_url=f"/tournaments/{team.tournament_id}?team_id={other_team.id}",
            how_long_active=now + timedelta(days=1)
        )

        response = auth_client_only.get(team_invites_url(team.id))
        assert response.status_code == status.HTTP_200_OK
        
        ids = [n["id"] for n in response.data]
        assert our_invite.id in ids
        assert other_invite.id not in ids
        assert len(ids) == 1

    def test_filters_out_expired_and_archived(self, auth_client_only, user, team, other_user):
        """Исключает просроченные и архивированные приглашения."""
        now = timezone.now()
        TeamMember.objects.get_or_create(team=team, user=user)

        # Активное
        active = Notification.objects.create(
            user=other_user,
            type=Notification.Type.TEAM_INVITE,
            status=Notification.Status.UNREAD,
            action_url=f"?team_id={team.id}",
            how_long_active=now + timedelta(days=1),
            title="A", message="M"
        )
        
        # Просроченное
        expired = Notification.objects.create(
            user=other_user,
            type=Notification.Type.TEAM_INVITE,
            status=Notification.Status.UNREAD,
            action_url=f"?team_id={team.id}",
            how_long_active=now - timedelta(days=1),
            title="E", message="M"
        )
        
        # Архивованное
        archived = Notification.objects.create(
            user=other_user,
            type=Notification.Type.TEAM_INVITE,
            status=Notification.Status.ARCHIVED,
            action_url=f"?team_id={team.id}",
            how_long_active=now + timedelta(days=1),
            title="Ar", message="M"
        )

        response = auth_client_only.get(team_invites_url(team.id))
        ids = [n["id"] for n in response.data]
        assert active.id in ids
        assert expired.id not in ids
        assert archived.id not in ids
