"""
Тести для команд:
  - GET  /api/teams                             → TeamListView
  - POST /api/teams                             → TeamListView
  - GET  /api/teams/archive                     → TeamArchiveListView
  - GET  /api/teams/<id>                        → TeamDetailView
"""

import pytest
from django.utils import timezone
from rest_framework import status

from salocore.models import Team, TeamMember, Tournament

TEAMS_URL = "/api/teams"
TEAMS_ARCHIVE_URL = "/api/teams/archive"


def team_detail_url(team_id):
    return f"/api/teams/{team_id}"


# ──────────────────────────── TeamListView ────────────────────────────


@pytest.mark.django_db
class TestTeamListGet:
    url = TEAMS_URL

    def test_returns_200(self, auth_client_only):
        response = auth_client_only.get(self.url)
        assert response.status_code == status.HTTP_200_OK

    def test_returns_401_unauthenticated(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_only_user_teams(self, auth_client_only, team, other_user, tournament):
        """Повертає тільки команди поточного юзера."""
        other_team = Team.objects.create(
            tournament=tournament, name="Other Team", status=Team.Status.REGISTRATED
        )
        TeamMember.objects.create(team=other_team, user=other_user, is_captain=True)

        response = auth_client_only.get(self.url)
        ids = [t["id"] for t in response.data]
        assert team.id in ids
        assert other_team.id not in ids

    def test_excludes_archived_and_disqualified(self, auth_client_only, user, tournament):
        """ARCHIVED і DISQUALIFIED не повертаються."""
        t_arch = Team.objects.create(tournament=tournament, name="Arch", status=Team.Status.ARCHIVED)
        t_disq = Team.objects.create(tournament=tournament, name="Disq", status=Team.Status.DISQUALIFIED)
        TeamMember.objects.create(team=t_arch, user=user, is_captain=True)
        TeamMember.objects.create(team=t_disq, user=user, is_captain=True)

        response = auth_client_only.get(self.url)
        ids = [t["id"] for t in response.data]
        assert t_arch.id not in ids
        assert t_disq.id not in ids


@pytest.mark.django_db
class TestTeamListPost:
    url = TEAMS_URL

    def test_creates_team_and_captain(self, auth_client_only, tournament):
        """POST → 201, юзер стає капітаном."""
        payload = {"tournament": tournament.id, "name": "New Team"}
        response = auth_client_only.post(self.url, payload)
        assert response.status_code == status.HTTP_201_CREATED
        team = Team.objects.get(id=response.data["id"])
        assert TeamMember.objects.filter(team=team, is_captain=True).exists()

    def test_fails_duplicate_name_in_same_tournament(self, auth_client_only, team, tournament):
        """Назва вже існує в тому ж турнірі → 400."""
        payload = {"tournament": tournament.id, "name": team.name}
        response = auth_client_only.post(self.url, payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_fails_when_registration_closed(self, auth_client_only, tournament_running):
        """Турнір не в REGISTRATION → 400."""
        payload = {"tournament": tournament_running.id, "name": "Late Team"}
        response = auth_client_only.post(self.url, payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_fails_when_max_teams_reached(self, auth_client_only, admin_user, factory):
        """Досягнуто max_team → 400."""
        t = factory.create_tournament(admin_user, title="Full Tournament", max_team=1)
        Team.objects.create(tournament=t, name="Existing Team", status=Team.Status.REGISTRATED)
        response = auth_client_only.post(self.url, {"tournament": t.id, "name": "Extra Team"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_returns_401_unauthenticated(self, api_client, tournament):
        response = api_client.post(self.url, {"tournament": tournament.id, "name": "X"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ─────────────────────── TeamArchiveListView ──────────────────────────


@pytest.mark.django_db
class TestTeamArchiveList:
    url = TEAMS_ARCHIVE_URL

    def test_returns_200(self, auth_client_only):
        response = auth_client_only.get(self.url)
        assert response.status_code == status.HTTP_200_OK

    def test_returns_401_unauthenticated(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_archived_teams(self, auth_client_only, user, tournament):
        archived = Team.objects.create(
            tournament=tournament, name="Old Team", status=Team.Status.ARCHIVED
        )
        TeamMember.objects.create(team=archived, user=user, is_captain=True)
        response = auth_client_only.get(self.url)
        ids = [t["id"] for t in response.data]
        assert archived.id in ids

    def test_returns_teams_from_finished_tournament(self, auth_client_only, user, tournament_finished):
        t = Team.objects.create(
            tournament=tournament_finished, name="Finished Team", status=Team.Status.REGISTRATED
        )
        TeamMember.objects.create(team=t, user=user, is_captain=True)
        response = auth_client_only.get(self.url)
        ids = [item["id"] for item in response.data]
        assert t.id in ids

    def test_excludes_active_teams(self, auth_client_only, team):
        """Активна команда не в архіві."""
        response = auth_client_only.get(self.url)
        ids = [t["id"] for t in response.data]
        assert team.id not in ids


# ──────────────────────────── TeamDetailView ─────────────────────────


@pytest.mark.django_db
class TestTeamDetail:

    def test_returns_200_for_member(self, auth_client_only, team):
        response = auth_client_only.get(team_detail_url(team.id))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_401_unauthenticated(self, api_client, team):
        response = api_client.get(team_detail_url(team.id))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_404_nonexistent(self, auth_client_only):
        response = auth_client_only.get(team_detail_url(99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_forbidden_when_hidden_and_not_member(self, other_client, admin_user, factory):
        """is_team_visible=False + юзер не учасник → 403."""
        t = factory.create_tournament(
            admin_user, title="Hidden T", is_team_visible=False
        )
        hidden_team = Team.objects.create(tournament=t, name="Secret", status=Team.Status.REGISTRATED)
        response = other_client.get(team_detail_url(hidden_team.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_visible_for_member_even_when_hidden(self, auth_client_only, user, admin_user, factory):
        """Учасник бачить команду, навіть якщо is_team_visible=False."""
        t = factory.create_tournament(
            admin_user, title="Hidden T2", is_team_visible=False
        )
        hidden_team = Team.objects.create(tournament=t, name="MySecret", status=Team.Status.REGISTRATED)
        TeamMember.objects.create(team=hidden_team, user=user, is_captain=True)
        response = auth_client_only.get(team_detail_url(hidden_team.id))
        assert response.status_code == status.HTTP_200_OK
