"""
Тести для сповіщень:
  - GET   /api/notifications           → NotificationListView
  - GET   /api/notifications/archive   → NotificationArchiveListView
  - PATCH /api/notifications/<id>      → NotificationDetailView
"""

import pytest
from django.utils import timezone
from rest_framework import status

from salocore.models import Notification, Team, TeamMember, Tournament, User

NOTIF_LIST_URL = "/api/notifications"
NOTIF_ARCHIVE_URL = "/api/notifications/archive"


def notif_detail_url(nid):
    return f"/api/notifications/{nid}"


# ─────────────────────── Fixtures ─────────────────────────────────────


@pytest.fixture
def notif_unread(db, user):
    return Notification.objects.create(
        user=user,
        type=Notification.Type.TOURNAMENT_FINISHED,
        title="Unread",
        message="Body",
        action_type=Notification.ActionType.NONE,
        status=Notification.Status.UNREAD,
        how_long_active=timezone.now() + timezone.timedelta(days=1),
    )


@pytest.fixture
def notif_read(db, user):
    return Notification.objects.create(
        user=user,
        type=Notification.Type.TOURNAMENT_FINISHED,
        title="Read",
        message="Body",
        action_type=Notification.ActionType.NONE,
        status=Notification.Status.READ,
        how_long_active=timezone.now() + timezone.timedelta(days=1),
    )


@pytest.fixture
def notif_archived(db, user):
    return Notification.objects.create(
        user=user,
        type=Notification.Type.TOURNAMENT_FINISHED,
        title="Archived",
        message="Body",
        action_type=Notification.ActionType.NONE,
        status=Notification.Status.ARCHIVED,
        how_long_active=timezone.now() + timezone.timedelta(days=1),
    )


@pytest.fixture
def reg_tournament_for_notif(db, admin_user, factory):
    return factory.create_tournament(admin_user, title="Notif T", status=Tournament.Status.REGISTRATION)


@pytest.fixture
def invite_team(db, reg_tournament_for_notif, other_user):
    """Команда з other_user як капітаном (для invite-тестів)."""
    t = Team.objects.create(
        tournament=reg_tournament_for_notif, name="InviteTeam",
        status=Team.Status.REGISTRATED,
    )
    TeamMember.objects.create(team=t, user=other_user, is_captain=True)
    return t


@pytest.fixture
def notif_team_invite(db, user, invite_team):
    """TEAM_INVITE сповіщення для user, запрошення ще активне."""
    return Notification.objects.create(
        user=user,
        type=Notification.Type.TEAM_INVITE,
        title="Invite",
        message="You are invited",
        action_type=Notification.ActionType.YES_NO,
        status=Notification.Status.UNREAD,
        how_long_active=timezone.now() + timezone.timedelta(days=1),
        action_url=f"http://example.com/accept?team_id={invite_team.id}",
    )


@pytest.fixture
def notif_team_invite_expired(db, user, invite_team):
    return Notification.objects.create(
        user=user,
        type=Notification.Type.TEAM_INVITE,
        title="Expired Invite",
        message="Expired",
        action_type=Notification.ActionType.YES_NO,
        status=Notification.Status.UNREAD,
        how_long_active=timezone.now() - timezone.timedelta(days=1),
        action_url=f"http://example.com/accept?team_id={invite_team.id}",
    )


# ─────────────────── NotificationListView ────────────────────────────


@pytest.mark.django_db
class TestNotificationList:

    def test_returns_200(self, auth_client_only):
        response = auth_client_only.get(NOTIF_LIST_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_returns_401_unauthenticated(self, api_client):
        response = api_client.get(NOTIF_LIST_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_own_notifications_only(self, auth_client_only, notif_unread, other_user):
        other_notif = Notification.objects.create(
            user=other_user, type=Notification.Type.TOURNAMENT_FINISHED,
            title="Other", message="B", action_type=Notification.ActionType.NONE,
            status=Notification.Status.UNREAD,
            how_long_active=timezone.now() + timezone.timedelta(days=1),
        )
        response = auth_client_only.get(NOTIF_LIST_URL)
        ids = [n["id"] for n in response.data]
        assert notif_unread.id in ids
        assert other_notif.id not in ids

    def test_filter_by_status_unread(self, auth_client_only, notif_unread, notif_read):
        response = auth_client_only.get(NOTIF_LIST_URL, {"status": "UR"})
        ids = [n["id"] for n in response.data]
        assert notif_unread.id in ids
        assert notif_read.id not in ids

    def test_filter_by_multiple_statuses(self, auth_client_only, notif_unread, notif_read):
        response = auth_client_only.get(NOTIF_LIST_URL, {"status": "UR,RD"})
        ids = [n["id"] for n in response.data]
        assert notif_unread.id in ids
        assert notif_read.id in ids

    def test_no_filter_returns_all_statuses(
        self, auth_client_only, notif_unread, notif_read, notif_archived
    ):
        response = auth_client_only.get(NOTIF_LIST_URL)
        ids = [n["id"] for n in response.data]
        assert notif_unread.id in ids
        assert notif_read.id in ids
        assert notif_archived.id in ids


# ─────────────────── NotificationArchiveListView ──────────────────────


@pytest.mark.django_db
class TestNotificationArchiveList:

    def test_returns_200(self, auth_client_only):
        response = auth_client_only.get(NOTIF_ARCHIVE_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_returns_only_archived(self, auth_client_only, notif_unread, notif_archived):
        response = auth_client_only.get(NOTIF_ARCHIVE_URL)
        ids = [n["id"] for n in response.data]
        assert notif_archived.id in ids
        assert notif_unread.id not in ids

    def test_returns_401_unauthenticated(self, api_client):
        response = api_client.get(NOTIF_ARCHIVE_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ─────────────────── NotificationDetailView PATCH ────────────────────


@pytest.mark.django_db
class TestNotificationDetail:

    def test_action_read(self, auth_client_only, notif_unread):
        response = auth_client_only.patch(
            notif_detail_url(notif_unread.id), {"action": "read"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        notif_unread.refresh_from_db()
        assert notif_unread.status == Notification.Status.READ

    def test_action_archive(self, auth_client_only, notif_unread):
        response = auth_client_only.patch(
            notif_detail_url(notif_unread.id), {"action": "archive"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        notif_unread.refresh_from_db()
        assert notif_unread.status == Notification.Status.ARCHIVED

    def test_action_reject(self, auth_client_only, notif_team_invite):
        response = auth_client_only.patch(
            notif_detail_url(notif_team_invite.id), {"action": "reject"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        notif_team_invite.refresh_from_db()
        assert notif_team_invite.status == Notification.Status.ARCHIVED

    def test_action_accept_invite_adds_member(
        self, auth_client_only, user, notif_team_invite, invite_team
    ):
        response = auth_client_only.patch(
            notif_detail_url(notif_team_invite.id), {"action": "accept"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert TeamMember.objects.filter(team=invite_team, user=user).exists()

    def test_action_accept_expired_invite(
        self, auth_client_only, notif_team_invite_expired
    ):
        response = auth_client_only.patch(
            notif_detail_url(notif_team_invite_expired.id),
            {"action": "accept"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_action_accept_full_team(
        self, auth_client_only, user, admin_user, reg_tournament_for_notif, factory
    ):
        """Команда вже переповнена → 400."""
        full_t = factory.create_tournament(
            admin_user, title="Full", max_team=5, max_team_size=1
        )
        full_team = Team.objects.create(
            tournament=full_t, name="Full Team", status=Team.Status.REGISTRATED
        )
        cap_user = User.objects.create_user(
            username="capfull", email="capfull@mail.com",
            password="P123!", invite_code="CAPFULL1",
        )
        TeamMember.objects.create(team=full_team, user=cap_user, is_captain=True)
        notif = Notification.objects.create(
            user=user, type=Notification.Type.TEAM_INVITE,
            title="Full Invite", message="B", action_type=Notification.ActionType.YES_NO,
            status=Notification.Status.UNREAD,
            how_long_active=timezone.now() + timezone.timedelta(days=1),
            action_url=f"http://example.com/accept?team_id={full_team.id}",
        )
        response = auth_client_only.patch(
            notif_detail_url(notif.id), {"action": "accept"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unknown_action(self, auth_client_only, notif_unread):
        response = auth_client_only.patch(
            notif_detail_url(notif_unread.id), {"action": "fly"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_act_on_foreign_notification(self, other_client, notif_unread):
        """Чужа нотифікація → 404."""
        response = other_client.patch(
            notif_detail_url(notif_unread.id), {"action": "read"}, format="json"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_401_unauthenticated(self, api_client, notif_unread):
        response = api_client.patch(
            notif_detail_url(notif_unread.id), {"action": "read"}, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
