"""
Тести для адмін-ендпоінтів сабмітів та оцінок:
  - GET /api/admin/tournaments/<id>/rounds/<id>/submit
  - GET /api/admin/tournaments/<id>/rounds/<id>/submit/<id>
  - GET /api/admin/tournaments/<id>/rounds/<id>/evaluation
  - GET /api/admin/tournaments/<id>/rounds/<id>/evaluation/<id>
"""

import pytest
from django.utils import timezone
from rest_framework import status

from salocore.models import (
    Evaluation,
    Round,
    Submission,
    Team,
    TeamMember,
    Tournament,
    TournamentJury,
    User,
)


def admin_submit_list_url(tid, rid):
    return f"/api/admin/tournaments/{tid}/rounds/{rid}/submit"


def admin_submit_detail_url(tid, rid, sid):
    return f"/api/admin/tournaments/{tid}/rounds/{rid}/submit/{sid}"


def admin_eval_list_url(tid, rid):
    return f"/api/admin/tournaments/{tid}/rounds/{rid}/evaluation"


def admin_eval_detail_url(tid, rid, eid):
    return f"/api/admin/tournaments/{tid}/rounds/{rid}/evaluation/{eid}"


# ─────────────────── Fixtures ──────────────────────────────────────────


@pytest.fixture
def running_tournament_for_admin(db, admin_user, factory):
    return factory.create_tournament(admin_user, title="Admin Running T", status=Tournament.Status.RUNNING)


@pytest.fixture
def admin_round(db, running_tournament_for_admin, factory):
    return factory.create_round(running_tournament_for_admin, title="Admin Round", status=Round.Status.ACTIVE)


@pytest.fixture
def submit_team_admin(db, running_tournament_for_admin, user):
    t = Team.objects.create(
        tournament=running_tournament_for_admin, name="Submit Team Admin",
        status=Team.Status.REGISTRATED,
    )
    TeamMember.objects.create(team=t, user=user, is_captain=True)
    return t


@pytest.fixture
def admin_submission(db, submit_team_admin, admin_round, factory):
    return factory.create_submission(submit_team_admin, admin_round, status=Submission.Status.SUBMITTED)


@pytest.fixture
def jury_for_admin(db):
    return User.objects.create_user(
        username="juryadmin", email="juryadmin@mail.com",
        password="Pass123!", invite_code="JURYADM1",
    )


@pytest.fixture
def admin_evaluation(db, admin_submission, jury_for_admin, running_tournament_for_admin):
    TournamentJury.objects.create(
        tournament=running_tournament_for_admin, user=jury_for_admin
    )
    return Evaluation.objects.create(
        submission=admin_submission, jury=jury_for_admin,
        status=Evaluation.Status.DRAFT,
    )


# ─────────────────── AdminSubmissionListView ──────────────────────────


@pytest.mark.django_db
class TestAdminSubmissionList:

    def test_lists_submissions(
        self, admin_client, running_tournament_for_admin, admin_round, admin_submission
    ):
        response = admin_client.get(
            admin_submit_list_url(running_tournament_for_admin.id, admin_round.id)
        )
        assert response.status_code == status.HTTP_200_OK
        ids = [s["id"] for s in response.data]
        assert admin_submission.id in ids

    def test_returns_403_for_regular_user(
        self, auth_client_only, running_tournament_for_admin, admin_round
    ):
        response = auth_client_only.get(
            admin_submit_list_url(running_tournament_for_admin.id, admin_round.id)
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_401_unauthenticated(
        self, api_client, running_tournament_for_admin, admin_round
    ):
        response = api_client.get(
            admin_submit_list_url(running_tournament_for_admin.id, admin_round.id)
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_ordered_by_team_name(
        self, admin_client, running_tournament_for_admin, admin_round
    ):
        """Список впорядкований за назвою команди."""
        response = admin_client.get(
            admin_submit_list_url(running_tournament_for_admin.id, admin_round.id)
        )
        assert response.status_code == status.HTTP_200_OK


# ─────────────────── AdminSubmissionDetailView ────────────────────────


@pytest.mark.django_db
class TestAdminSubmissionDetail:

    def test_returns_submission(
        self, admin_client, running_tournament_for_admin, admin_round, admin_submission
    ):
        response = admin_client.get(
            admin_submit_detail_url(
                running_tournament_for_admin.id, admin_round.id, admin_submission.id
            )
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == admin_submission.id

    def test_returns_404_nonexistent(
        self, admin_client, running_tournament_for_admin, admin_round
    ):
        response = admin_client.get(
            admin_submit_detail_url(running_tournament_for_admin.id, admin_round.id, 99999)
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_403_for_regular_user(
        self, auth_client_only, running_tournament_for_admin, admin_round, admin_submission
    ):
        response = auth_client_only.get(
            admin_submit_detail_url(
                running_tournament_for_admin.id, admin_round.id, admin_submission.id
            )
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────── AdminEvaluationListView ──────────────────────────


@pytest.mark.django_db
class TestAdminEvaluationList:

    def test_lists_evaluations(
        self, admin_client, running_tournament_for_admin, admin_round, admin_evaluation
    ):
        response = admin_client.get(
            admin_eval_list_url(running_tournament_for_admin.id, admin_round.id)
        )
        assert response.status_code == status.HTTP_200_OK
        ids = [e["id"] for e in response.data]
        assert admin_evaluation.id in ids

    def test_returns_403_for_regular_user(
        self, auth_client_only, running_tournament_for_admin, admin_round
    ):
        response = auth_client_only.get(
            admin_eval_list_url(running_tournament_for_admin.id, admin_round.id)
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_empty_when_no_evaluations(
        self, admin_client, running_tournament_for_admin, admin_round
    ):
        response = admin_client.get(
            admin_eval_list_url(running_tournament_for_admin.id, admin_round.id)
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)


# ─────────────────── AdminEvaluationDetailView ────────────────────────


@pytest.mark.django_db
class TestAdminEvaluationDetail:

    def test_returns_evaluation(
        self, admin_client, running_tournament_for_admin, admin_round, admin_evaluation
    ):
        response = admin_client.get(
            admin_eval_detail_url(
                running_tournament_for_admin.id, admin_round.id, admin_evaluation.id
            )
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == admin_evaluation.id

    def test_returns_404_nonexistent(
        self, admin_client, running_tournament_for_admin, admin_round
    ):
        response = admin_client.get(
            admin_eval_detail_url(running_tournament_for_admin.id, admin_round.id, 99999)
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_403_for_regular_user(
        self, auth_client_only, running_tournament_for_admin, admin_round, admin_evaluation
    ):
        response = auth_client_only.get(
            admin_eval_detail_url(
                running_tournament_for_admin.id, admin_round.id, admin_evaluation.id
            )
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
