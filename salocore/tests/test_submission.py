"""
Тести для сабмітів:
  - GET  /api/teams/<id>/submit              → TeamSubmitListView
  - POST /api/teams/<id>/submit              → TeamSubmitListView
  - PATCH /api/teams/<id>/submit/<sub_id>    → TeamSubmitDetailView
"""

import pytest
from django.utils import timezone
from rest_framework import status

from salocore.models import Round, Submission, Team, TeamMember, Tournament


def submit_list_url(team_id):
    return f"/api/teams/{team_id}/submit"


def submit_detail_url(team_id, sub_id):
    return f"/api/teams/{team_id}/submit/{sub_id}"


# ─────────────────────── Fixtures ─────────────────────────────────────


@pytest.fixture
def running_tournament(db, admin_user, factory):
    return factory.create_tournament(admin_user, title="Running T", status=Tournament.Status.RUNNING)


@pytest.fixture
def round_future(db, running_tournament, factory):
    """Раунд з дедлайном у майбутньому."""
    return factory.create_round(
        running_tournament, title="Round Future",
        status=Round.Status.ACTIVE,
        deadline=timezone.now() + timezone.timedelta(days=3),
    )


@pytest.fixture
def round_past(db, running_tournament, factory):
    """Раунд з дедлайном у минулому."""
    return factory.create_round(
        running_tournament, title="Round Past",
        status=Round.Status.ACTIVE,
        deadline=timezone.now() - timezone.timedelta(days=1),
    )


@pytest.fixture
def submit_team(db, running_tournament, user):
    """Команда, де user є учасником."""
    t = Team.objects.create(
        tournament=running_tournament, name="Submit Team",
        status=Team.Status.REGISTRATED,
    )
    TeamMember.objects.create(team=t, user=user, is_captain=True)
    return t


@pytest.fixture
def submission(db, submit_team, round_future, factory):
    return factory.create_submission(submit_team, round_future)


# ──────────────────── TeamSubmitListView GET ──────────────────────────


@pytest.mark.django_db
class TestTeamSubmitListGet:

    def test_returns_200_for_member(self, auth_client_only, submit_team):
        response = auth_client_only.get(submit_list_url(submit_team.id))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_403_for_non_member(self, other_client, submit_team):
        response = other_client.get(submit_list_url(submit_team.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_401_unauthenticated(self, api_client, submit_team):
        response = api_client.get(submit_list_url(submit_team.id))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_lists_submissions(self, auth_client_only, submit_team, submission):
        response = auth_client_only.get(submit_list_url(submit_team.id))
        ids = [s["id"] for s in response.data]
        assert submission.id in ids


# ──────────────────── TeamSubmitListView POST ─────────────────────────


@pytest.mark.django_db
class TestTeamSubmitListPost:

    def test_creates_submission_as_draft(self, auth_client_only, submit_team, round_future):
        payload = {
            "round": round_future.id,
            "githubUrl": "https://github.com/t",
            "videoUrl": "https://v.com/t",
            "demoUrl": "https://d.com/t",
            "description": "Desc",
            "status": Submission.Status.DRAFT,
        }
        response = auth_client_only.post(submit_list_url(submit_team.id), payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert Submission.objects.filter(team=submit_team, round=round_future).exists()

    def test_fails_if_no_round_provided(self, auth_client_only, submit_team):
        response = auth_client_only.post(submit_list_url(submit_team.id), {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_fails_if_deadline_passed(self, auth_client_only, submit_team, round_past):
        response = auth_client_only.post(
            submit_list_url(submit_team.id), {"round": round_past.id}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_fails_if_submission_already_exists(
        self, auth_client_only, submit_team, round_future, submission
    ):
        response = auth_client_only.post(
            submit_list_url(submit_team.id), {"round": round_future.id}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_fails_for_non_member(self, other_client, submit_team, round_future):
        response = other_client.post(
            submit_list_url(submit_team.id), {"round": round_future.id}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ──────────────────── TeamSubmitDetailView PATCH ──────────────────────


@pytest.mark.django_db
class TestTeamSubmitDetailPatch:

    def test_patch_updates_fields(self, auth_client_only, submit_team, submission):
        response = auth_client_only.patch(
            submit_detail_url(submit_team.id, submission.id),
            {"github_url": "https://github.com/example"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["github_url"] == "https://github.com/example"

    def test_patch_fails_if_deadline_passed(
        self, auth_client_only, submit_team, round_past, factory
    ):
        sub = factory.create_submission(submit_team, round_past)
        response = auth_client_only.patch(
            submit_detail_url(submit_team.id, sub.id),
            {"github_url": "https://github.com/x"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_submit_sets_submitted_at(self, auth_client_only, submit_team, submission):
        response = auth_client_only.patch(
            submit_detail_url(submit_team.id, submission.id),
            {"status": Submission.Status.SUBMITTED},
        )
        assert response.status_code == status.HTTP_200_OK
        submission.refresh_from_db()
        assert submission.submitted_at is not None

    def test_patch_fails_if_already_submitted_without_draft(
        self, auth_client_only, submit_team, submission
    ):
        submission.status = Submission.Status.SUBMITTED
        submission.save()
        response = auth_client_only.patch(
            submit_detail_url(submit_team.id, submission.id),
            {"github_url": "https://github.com/hack"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_can_revert_to_draft(self, auth_client_only, submit_team, submission):
        submission.status = Submission.Status.SUBMITTED
        submission.save()
        response = auth_client_only.patch(
            submit_detail_url(submit_team.id, submission.id),
            {"status": Submission.Status.DRAFT},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_patch_fails_for_non_member(self, other_client, submit_team, submission):
        response = other_client.patch(
            submit_detail_url(submit_team.id, submission.id),
            {"github_url": "https://github.com/x"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_for_nonexistent(self, auth_client_only, submit_team):
        response = auth_client_only.patch(
            submit_detail_url(submit_team.id, 99999), {}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
