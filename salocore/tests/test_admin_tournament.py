"""
Тести для адмін-ендпоінтів турнірів:
  - GET/POST   /api/admin/tournaments
  - GET/PATCH/DELETE /api/admin/tournaments/<id>
  - PATCH      /api/admin/tournaments/<id>/start
  - GET/POST   /api/admin/tournaments/<id>/jury
  - DELETE     /api/admin/tournaments/<id>/jury/<uid>
  - GET/POST   /api/admin/tournaments/<id>/admin
  - DELETE     /api/admin/tournaments/<id>/admin/<uid>
"""

from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status

from salocore.models import Tournament, TournamentAdmin, TournamentJury, User

ADMIN_TOURNAMENTS_URL = "/api/admin/tournaments"


def admin_tournament_detail_url(tid):
    return f"/api/admin/tournaments/{tid}"


def admin_tournament_start_url(tid):
    return f"/api/admin/tournaments/{tid}/start"


def admin_jury_url(tid):
    return f"/api/admin/tournaments/{tid}/jury"


def admin_jury_detail_url(tid, uid):
    return f"/api/admin/tournaments/{tid}/jury/{uid}"


def admin_admins_url(tid):
    return f"/api/admin/tournaments/{tid}/admin"


def admin_admins_detail_url(tid, uid):
    return f"/api/admin/tournaments/{tid}/admin/{uid}"


# ─────────────────── Fixtures ─────────────────────────────────────────


@pytest.fixture
def jury_user(db):
    return User.objects.create_user(
        username="juryuser",
        email="jury@mail.com",
        password="JuryPass123!",
        invite_code="JURYCODE",
    )


# ─────────────────── AdminTournamentListView ───────────────────────────


@pytest.mark.django_db
class TestAdminTournamentList:
    def test_get_returns_200_for_admin(self, admin_client):
        response = admin_client.get(ADMIN_TOURNAMENTS_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_get_returns_403_for_regular_user(self, auth_client_only):
        response = auth_client_only.get(ADMIN_TOURNAMENTS_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_returns_401_unauthenticated(self, api_client):
        response = api_client.get(ADMIN_TOURNAMENTS_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_superuser_sees_all_tournaments(self, superuser_client, tournament, tournament_draft):
        response = superuser_client.get(ADMIN_TOURNAMENTS_URL)
        ids = [t["id"] for t in response.data]
        assert tournament.id in ids
        assert tournament_draft.id in ids

    def test_staff_sees_only_own_tournaments(self, admin_client, admin_user, tournament, user, factory):
        """Стаф без superuser бачить тільки свої турніри (де creator або admin)."""
        other_t = factory.create_tournament(user, title="Other T", status=Tournament.Status.DRAFT)
        response = admin_client.get(ADMIN_TOURNAMENTS_URL)
        ids = [t["id"] for t in response.data]
        assert tournament.id in ids
        assert other_t.id not in ids

    def test_post_creates_tournament(self, admin_client):
        now = timezone.now()
        payload = {
            "title": "New Admin T",
            "description": "D",
            "rules": "Rules",
            "max_team": 5,
            "max_team_size": 3,
            "min_team_size": 1,
            "is_team_visible": True,
            "reg_open_at": now.isoformat(),
            "reg_close_at": (now + timezone.timedelta(days=1)).isoformat(),
            "start_date": (now + timezone.timedelta(days=2)).isoformat(),
            "ended_at": (now + timezone.timedelta(days=3)).isoformat(),
        }
        response = admin_client.post(ADMIN_TOURNAMENTS_URL, payload)
        if response.status_code != 201:
            print(f"DEBUG ADMIN POST: {response.data}")
        assert response.status_code == status.HTTP_201_CREATED

    def test_post_sets_creator_as_current_user(self, admin_client, admin_user):
        now = timezone.now()
        payload = {
            "title": "Creator T",
            "description": "D",
            "rules": "Rules",
            "max_team": 5,
            "max_team_size": 3,
            "min_team_size": 1,
            "is_team_visible": True,
            "reg_open_at": now.isoformat(),
            "reg_close_at": (now + timezone.timedelta(days=1)).isoformat(),
            "start_date": (now + timezone.timedelta(days=2)).isoformat(),
            "ended_at": (now + timezone.timedelta(days=3)).isoformat(),
        }
        response = admin_client.post(ADMIN_TOURNAMENTS_URL, payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert Tournament.objects.get(id=response.data["id"]).creator == admin_user


# ─────────────────── AdminTournamentDetailView ────────────────────────


@pytest.mark.django_db
class TestAdminTournamentDetail:
    def test_get_returns_200(self, admin_client, tournament_draft):
        response = admin_client.get(admin_tournament_detail_url(tournament_draft.id))
        assert response.status_code == status.HTTP_200_OK

    def test_patch_edits_draft_tournament(self, admin_client, tournament_draft):
        response = admin_client.patch(admin_tournament_detail_url(tournament_draft.id), {"title": "Updated"})
        assert response.status_code == status.HTTP_200_OK
        tournament_draft.refresh_from_db()
        assert tournament_draft.title == "Updated"

    def test_patch_fails_non_draft(self, admin_client, tournament):
        with patch("salocore.views.admin_tournament.get_tournament_cheker") as m:
            m.return_value.check.return_value = None
            response = admin_client.patch(admin_tournament_detail_url(tournament.id), {"title": "X"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_forbidden_for_non_creator(self, admin_client, factory):
        """Не creator не може редагувати (IsTournamentCreatorOrReadOnly)."""
        # Створюємо турнір іншим адміном
        other_admin = factory.create_user(email="other@admin.com", is_staff=True)
        other_tournament = factory.create_tournament(other_admin, title="Other Draft", status=Tournament.Status.DRAFT)

        # Спробуємо відредагувати через admin_client (який є admin_user, а не other_admin)
        response = admin_client.patch(admin_tournament_detail_url(other_tournament.id), {"title": "Stolen"})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_draft_tournament(self, admin_client, tournament_draft):
        response = admin_client.delete(admin_tournament_detail_url(tournament_draft.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_fails_non_draft(self, admin_client, tournament):
        response = admin_client.delete(admin_tournament_detail_url(tournament.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────── AdminTournamentStartView ─────────────────────────


@pytest.mark.django_db
class TestAdminTournamentStart:
    def test_starts_draft_tournament_with_jury(self, admin_client, tournament_draft, jury_user):
        TournamentJury.objects.create(tournament=tournament_draft, user=jury_user)
        with patch("salocore.views.admin_tournament.get_tournament_cheker") as m:
            m.return_value.check.return_value = None
            response = admin_client.patch(admin_tournament_start_url(tournament_draft.id))
        assert response.status_code == status.HTTP_200_OK
        tournament_draft.refresh_from_db()
        assert tournament_draft.status == Tournament.Status.REGISTRATION

    def test_fails_if_no_jury(self, admin_client, tournament_draft):
        with patch("salocore.views.admin_tournament.get_tournament_cheker") as m:
            m.return_value.check.return_value = None
            response = admin_client.patch(admin_tournament_start_url(tournament_draft.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_fails_if_not_draft(self, admin_client, tournament):
        response = admin_client.patch(admin_tournament_start_url(tournament.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_returns_403_for_non_creator(self, superuser_client, user, jury_user, factory):
        other_draft = factory.create_tournament(user, title="OtherD", status=Tournament.Status.DRAFT)
        TournamentJury.objects.create(tournament=other_draft, user=jury_user)
        # admin_user (fixture) не є creator → IsTournamentCreator блокує
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        admin2 = User.objects.create_user(
            username="admin2",
            email="admin2@mail.com",
            password="A123!",
            is_staff=True,
            invite_code="ADM2CODE",
        )
        client2 = APIClient()
        refresh = RefreshToken.for_user(admin2)
        client2.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        with patch("salocore.views.admin_tournament.get_tournament_cheker") as m:
            m.return_value.check.return_value = None
            response = client2.patch(admin_tournament_start_url(other_draft.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────── AdminTournamentJuryView ─────────────────────────


@pytest.mark.django_db
class TestAdminTournamentJury:
    def test_get_lists_jury(self, admin_client, tournament_draft, jury_user):
        TournamentJury.objects.create(tournament=tournament_draft, user=jury_user)
        response = admin_client.get(admin_jury_url(tournament_draft.id))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_post_adds_jury_by_invite_code(self, admin_client, tournament_draft, jury_user):
        response = admin_client.post(
            admin_jury_url(tournament_draft.id),
            {"invite_code": jury_user.invite_code},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert TournamentJury.objects.filter(tournament=tournament_draft, user=jury_user).exists()

    def test_post_fails_if_already_jury(self, admin_client, tournament_draft, jury_user):
        TournamentJury.objects.create(tournament=tournament_draft, user=jury_user)
        response = admin_client.post(
            admin_jury_url(tournament_draft.id),
            {"invite_code": jury_user.invite_code},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_post_fails_if_user_not_found(self, admin_client, tournament_draft):
        response = admin_client.post(admin_jury_url(tournament_draft.id), {"invite_code": "NOTEXIST"})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_post_fails_if_no_invite_code(self, admin_client, tournament_draft):
        response = admin_client.post(admin_jury_url(tournament_draft.id), {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_removes_jury(self, admin_client, tournament_draft, jury_user):
        TournamentJury.objects.create(tournament=tournament_draft, user=jury_user)
        response = admin_client.delete(admin_jury_detail_url(tournament_draft.id, jury_user.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not TournamentJury.objects.filter(tournament=tournament_draft, user=jury_user).exists()


# ─────────────────── AdminTournamentAdminsView ────────────────────────


@pytest.mark.django_db
class TestAdminTournamentAdmins:
    def test_post_adds_admin_by_invite_code(self, admin_client, tournament_draft, other_user):
        response = admin_client.post(
            admin_admins_url(tournament_draft.id),
            {"invite_code": other_user.invite_code},
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_post_fails_if_already_admin(self, admin_client, tournament_draft, other_user):
        TournamentAdmin.objects.create(tournament=tournament_draft, user=other_user)
        response = admin_client.post(
            admin_admins_url(tournament_draft.id),
            {"invite_code": other_user.invite_code},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_removes_admin(self, admin_client, tournament_draft, other_user):
        TournamentAdmin.objects.create(tournament=tournament_draft, user=other_user)
        response = admin_client.delete(admin_admins_detail_url(tournament_draft.id, other_user.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
