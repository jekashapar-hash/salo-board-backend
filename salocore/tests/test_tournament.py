"""
Тести для публічних ендпоінтів турнірів:
  - GET /api/tournaments                    → TournamentListView
  - GET /api/tournaments/archive            → ArchivedTournamentListView
  - GET /api/tournaments/<id>              → TournamentDetailView
  - GET /api/tournaments/<id>/teams        → TournamentTeamsView
  - GET /api/tournaments/<id>/leaderboard  → TournamentLeaderboardView
  - GET /api/tournaments/<id>/jury         → TournamentJuryView
  - GET /api/tournaments/<id>/admins       → TournamentAdminView
"""

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from salocore.models import Tournament, TournamentAdmin, TournamentJury

# ─────────────────────────── TournamentListView ──────────────────────


@pytest.mark.django_db
class TestTournamentList:
    url = reverse("tournament-list")

    def test_returns_200_without_auth(self, api_client, tournament):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK

    def test_excludes_archived_tournaments(self, api_client, tournament, tournament_archived):
        response = api_client.get(self.url)
        ids = [t["id"] for t in response.data["results"]]
        assert tournament.id in ids
        assert tournament_archived.id not in ids

    def test_filter_by_name(self, api_client, tournament):
        response = api_client.get(self.url, {"name": "Test"})
        assert all("Test" in t["title"] for t in response.data["results"])

    def test_filter_by_name_no_match(self, api_client, tournament):
        response = api_client.get(self.url, {"name": "НемаєТакого123"})
        assert response.data["results"] == []

    def test_filter_by_status(self, api_client, tournament, tournament_draft):
        response = api_client.get(self.url, {"status": Tournament.Status.REGISTRATION})
        ids = [t["id"] for t in response.data["results"]]
        assert tournament.id in ids
        assert tournament_draft.id not in ids

    def test_filter_by_role_unauthenticated_returns_empty(self, api_client, tournament):
        """Без токена + role=participant → пустий список."""
        response = api_client.get(self.url, {"role": "participant"})
        assert response.data["results"] == []

    def test_filter_by_role_participant(self, auth_client_only, user, team, tournament):
        """Юзер учасник команди → відображається при role=participant."""
        response = auth_client_only.get(self.url, {"role": "participant"})
        ids = [t["id"] for t in response.data["results"]]
        assert tournament.id in ids

    def test_filter_by_role_jury(self, auth_client_only, user, tournament):
        TournamentJury.objects.create(tournament=tournament, user=user)
        response = auth_client_only.get(self.url, {"role": "jury"})
        ids = [t["id"] for t in response.data["results"]]
        assert tournament.id in ids

    def test_filter_by_role_admin(self, auth_client_only, user, tournament):
        TournamentAdmin.objects.create(tournament=tournament, user=user)
        response = auth_client_only.get(self.url, {"role": "admin"})
        ids = [t["id"] for t in response.data["results"]]
        assert tournament.id in ids

    def test_filter_by_role_all_returns_all(self, auth_client_only, tournament):
        response = auth_client_only.get(self.url, {"role": "all"})
        ids = [t["id"] for t in response.data["results"]]
        assert tournament.id in ids


# ───────────────────── ArchivedTournamentListView ─────────────────────


@pytest.mark.django_db
class TestArchivedTournamentList:
    url = reverse("tournament-archive-list")

    def test_returns_200(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK

    def test_returns_only_archived(self, api_client, tournament, tournament_archived):
        response = api_client.get(self.url)
        ids = [t["id"] for t in response.data["results"]]
        assert tournament_archived.id in ids
        assert tournament.id not in ids

    def test_filter_by_name(self, api_client, tournament_archived):
        response = api_client.get(self.url, {"name": "Archived"})
        assert len(response.data["results"]) >= 1
        assert all("Archived" in t["title"] for t in response.data["results"])


# ────────────────────────── TournamentDetailView ─────────────────────


@pytest.mark.django_db
class TestTournamentDetail:
    def url(self, tid):
        return reverse("tournament-detail", kwargs={"tournament_id": tid})

    def test_returns_200_without_auth(self, api_client, tournament):
        response = api_client.get(self.url(tournament.id))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_404_for_nonexistent(self, api_client):
        response = api_client.get(self.url(99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_response_contains_key_fields(self, api_client, tournament):
        response = api_client.get(self.url(tournament.id))
        for field in ("id", "title", "status"):
            assert field in response.data


# ─────────────────────────── TournamentTeamsView ─────────────────────


@pytest.mark.django_db
class TestTournamentTeams:
    def url(self, tid):
        return reverse("tournament-teams", kwargs={"tournament_id": tid})

    def test_returns_200_when_visible(self, api_client, tournament, team):
        assert tournament.is_team_visible is True
        response = api_client.get(self.url(tournament.id))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_403_when_hidden(self, api_client, admin_user, factory):
        hidden = factory.create_tournament(admin_user, title="Hidden", is_team_visible=False)
        response = api_client.get(self.url(hidden.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_for_nonexistent(self, api_client):
        response = api_client.get(self.url(99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_lists_teams(self, api_client, tournament, team):
        response = api_client.get(self.url(tournament.id))
        ids = [t["id"] for t in response.data]
        assert team.id in ids


# ──────────────────────── TournamentLeaderboardView ──────────────────


@pytest.mark.django_db
class TestTournamentLeaderboard:
    def url(self, tid):
        return reverse("tournament-leaderboard", kwargs={"tournament_id": tid})

    def test_returns_200_when_visible(self, api_client, tournament):
        with patch("salocore.views.tournament.get_leaderboard_use_case") as mock_uc:
            mock_uc.return_value.get_leaderboard.return_value = []
            response = api_client.get(self.url(tournament.id))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_403_when_hidden(self, api_client, admin_user, factory):
        hidden = factory.create_tournament(admin_user, title="Hidden LB", is_team_visible=False)
        response = api_client.get(self.url(hidden.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_for_nonexistent(self, api_client):
        response = api_client.get(self.url(99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ──────────────────────── TournamentJuryView ─────────────────────────


@pytest.mark.django_db
class TestTournamentJury:
    def url(self, tid):
        return reverse("tournament-jury", kwargs={"tournament_id": tid})

    def test_returns_200_authenticated(self, auth_client_only, tournament):
        response = auth_client_only.get(self.url(tournament.id))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_401_unauthenticated(self, api_client, tournament):
        response = api_client.get(self.url(tournament.id))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_404_for_nonexistent(self, auth_client_only):
        response = auth_client_only.get(self.url(99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_lists_jury_members(self, auth_client_only, tournament, other_user):
        TournamentJury.objects.create(tournament=tournament, user=other_user)
        response = auth_client_only.get(self.url(tournament.id))
        assert len(response.data) == 1


# ──────────────────────── TournamentAdminView ────────────────────────


@pytest.mark.django_db
class TestTournamentAdmins:
    def url(self, tid):
        return reverse("tournament-admins", kwargs={"tournament_id": tid})

    def test_returns_200_authenticated(self, auth_client_only, tournament):
        response = auth_client_only.get(self.url(tournament.id))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_401_unauthenticated(self, api_client, tournament):
        response = api_client.get(self.url(tournament.id))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_404_for_nonexistent(self, auth_client_only):
        response = auth_client_only.get(self.url(99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_lists_admins(self, auth_client_only, tournament, other_user):
        TournamentAdmin.objects.create(tournament=tournament, user=other_user)
        response = auth_client_only.get(self.url(tournament.id))
        assert len(response.data) == 1
