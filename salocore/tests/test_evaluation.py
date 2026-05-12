"""
Тести для оцінювання:
  - GET/PATCH /api/tournaments/<id>/rounds/<id>/submissions/<id>/evaluation
  - PATCH     .../criterion-evaluation/<id>
  - PATCH     .../requirement-evaluation/<id>
  - GET       /api/tournaments/<id>/jury-evaluations
  - GET       /api/tournaments/<id>/jury-evaluations/count
"""

from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status

from salocore.models import (
    CriterionEvaluation,
    Evaluation,
    EvaluationCriterion,
    RequirementEvaluation,
    Round,
    RoundRequirement,
    Submission,
    Team,
    TeamMember,
    Tournament,
    TournamentJury,
)


def evaluation_url(tid, rid, sid):
    return f"/api/tournaments/{tid}/rounds/{rid}/submissions/{sid}/evaluation"


def crit_eval_url(tid, rid, sid):
    return f"/api/tournaments/{tid}/rounds/{rid}/submissions/{sid}/evaluation/criterion-evaluation"


def crit_eval_detail_url(tid, rid, sid, ceid):
    return f"/api/tournaments/{tid}/rounds/{rid}/submissions/{sid}/evaluation/criterion-evaluation/{ceid}"


def req_eval_url(tid, rid, sid):
    return f"/api/tournaments/{tid}/rounds/{rid}/submissions/{sid}/evaluation/requirement-evaluation"


def req_eval_detail_url(tid, rid, sid, reid):
    return f"/api/tournaments/{tid}/rounds/{rid}/submissions/{sid}/evaluation/requirement-evaluation/{reid}"


def jury_evaluations_url(tid):
    return f"/api/tournaments/{tid}/jury-evaluations"


def jury_evaluations_count_url(tid):
    return f"/api/tournaments/{tid}/jury-evaluations/count"


# ─────────────────── Fixtures ──────────────────────────────────────────


@pytest.fixture
def jury_user(db):
    from salocore.models import User
    return User.objects.create_user(
        username="juryeval", email="juryeval@mail.com",
        password="JuryPass123!", invite_code="JUREVAL1",
    )


@pytest.fixture
def jury_client(api_client, jury_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(jury_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def eval_tournament(db, admin_user, factory):
    return factory.create_tournament(admin_user, title="Eval T", status=Tournament.Status.RUNNING)


@pytest.fixture
def eval_round(db, eval_tournament, factory):
    return factory.create_round(eval_tournament, title="Eval Round", status=Round.Status.ACTIVE)


@pytest.fixture
def eval_team(db, eval_tournament, user):
    t = Team.objects.create(
        tournament=eval_tournament, name="Eval Team",
        status=Team.Status.REGISTRATED,
    )
    TeamMember.objects.create(team=t, user=user, is_captain=True)
    return t


@pytest.fixture
def submission(db, eval_team, eval_round, factory):
    return factory.create_submission(eval_team, eval_round, status=Submission.Status.SUBMITTED)


@pytest.fixture
def jury_assignment(db, eval_tournament, jury_user):
    return TournamentJury.objects.create(tournament=eval_tournament, user=jury_user)


@pytest.fixture
def criterion(db, eval_round, factory):
    return factory.create_criterion(eval_round, title="Crit")


@pytest.fixture
def requirement(db, eval_round):
    return RoundRequirement.objects.create(round=eval_round, text="Req", order_index=1)


@pytest.fixture
def evaluation_draft(db, submission, jury_user, jury_assignment):
    return Evaluation.objects.create(
        submission=submission, jury=jury_user, status=Evaluation.Status.DRAFT
    )


@pytest.fixture
def criterion_evaluation(db, evaluation_draft, criterion):
    return CriterionEvaluation.objects.create(
        evaluation=evaluation_draft, criterion=criterion, score=0, comment=""
    )


@pytest.fixture
def requirement_evaluation(db, evaluation_draft, requirement):
    return RequirementEvaluation.objects.create(
        evaluation=evaluation_draft, requirement=requirement,
        is_satisfied=False, comment=""
    )


# ─────────────────── EvaluationDetailView GET ─────────────────────────


@pytest.mark.django_db
class TestEvaluationDetailGet:

    def test_jury_gets_200_and_evaluation_created(
        self, jury_client, eval_tournament, eval_round, submission, jury_assignment
    ):
        """GET від журі → evaluation автоматично створюється."""
        with patch("salocore.views.evaluation.get_round_cheker"):
            response = jury_client.get(
                evaluation_url(eval_tournament.id, eval_round.id, submission.id)
            )
        assert response.status_code == status.HTTP_200_OK
        assert Evaluation.objects.filter(submission=submission, jury=jury_assignment.user).exists()

    def test_returns_403_for_non_jury_non_creator(
        self, auth_client_only, eval_tournament, eval_round, submission
    ):
        response = auth_client_only.get(
            evaluation_url(eval_tournament.id, eval_round.id, submission.id)
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_creator_gets_200_without_creating_evaluation(
        self, admin_client, eval_tournament, eval_round, submission, evaluation_draft, jury_user
    ):
        """Creator може переглянути evaluation."""
        response = admin_client.get(
            evaluation_url(eval_tournament.id, eval_round.id, submission.id) + f"?jury_id={jury_user.id}"
        )
        assert response.status_code == status.HTTP_200_OK


# ─────────────────── EvaluationDetailView PATCH ───────────────────────


@pytest.mark.django_db
class TestEvaluationDetailPatch:

    def test_patch_updates_status_to_submitted(
        self, jury_client, eval_tournament, eval_round, submission, evaluation_draft
    ):
        with patch("salocore.views.evaluation.get_round_cheker") as m:
            m.return_value.check.return_value = None
            response = jury_client.patch(
                evaluation_url(eval_tournament.id, eval_round.id, submission.id),
                {"status": Evaluation.Status.SUBMITTED},
            )
        assert response.status_code == status.HTTP_200_OK
        evaluation_draft.refresh_from_db()
        assert evaluation_draft.status == Evaluation.Status.SUBMITTED

    def test_patch_fails_if_already_submitted(
        self, jury_client, eval_tournament, eval_round, submission, evaluation_draft
    ):
        evaluation_draft.status = Evaluation.Status.SUBMITTED
        evaluation_draft.save()
        response = jury_client.patch(
            evaluation_url(eval_tournament.id, eval_round.id, submission.id),
            {"status": Evaluation.Status.SUBMITTED},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_can_revert_to_draft(
        self, jury_client, eval_tournament, eval_round, submission, evaluation_draft
    ):
        evaluation_draft.status = Evaluation.Status.SUBMITTED
        evaluation_draft.save()
        response = jury_client.patch(
            evaluation_url(eval_tournament.id, eval_round.id, submission.id),
            {"status": Evaluation.Status.DRAFT},
        )
        assert response.status_code == status.HTTP_200_OK


# ─────────────────── CriterionEvaluationDetailView ────────────────────


@pytest.mark.django_db
class TestCriterionEvaluationDetail:

    def test_patch_updates_score(
        self, jury_client, eval_tournament, eval_round, submission,
        evaluation_draft, criterion_evaluation
    ):
        response = jury_client.patch(
            crit_eval_detail_url(
                eval_tournament.id, eval_round.id,
                submission.id, criterion_evaluation.id
            ),
            {"score": 8},
        )
        assert response.status_code == status.HTTP_200_OK
        criterion_evaluation.refresh_from_db()
        assert criterion_evaluation.score == 8

    def test_patch_fails_if_evaluation_submitted(
        self, jury_client, eval_tournament, eval_round, submission,
        evaluation_draft, criterion_evaluation
    ):
        evaluation_draft.status = Evaluation.Status.SUBMITTED
        evaluation_draft.save()
        response = jury_client.patch(
            crit_eval_detail_url(
                eval_tournament.id, eval_round.id,
                submission.id, criterion_evaluation.id
            ),
            {"score": 5},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_for_foreign_entry(
        self, jury_client, eval_tournament, eval_round, submission
    ):
        response = jury_client.patch(
            crit_eval_detail_url(eval_tournament.id, eval_round.id, submission.id, 99999),
            {"score": 5},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ─────────────────── RequirementEvaluationDetailView ──────────────────


@pytest.mark.django_db
class TestRequirementEvaluationDetail:

    def test_patch_updates_is_satisfied(
        self, jury_client, eval_tournament, eval_round, submission,
        evaluation_draft, requirement_evaluation
    ):
        response = jury_client.patch(
            req_eval_detail_url(
                eval_tournament.id, eval_round.id,
                submission.id, requirement_evaluation.id
            ),
            {"is_satisfied": True},
        )
        assert response.status_code == status.HTTP_200_OK
        requirement_evaluation.refresh_from_db()
        assert requirement_evaluation.is_satisfied is True

    def test_patch_fails_if_submitted(
        self, jury_client, eval_tournament, eval_round, submission,
        evaluation_draft, requirement_evaluation
    ):
        evaluation_draft.status = Evaluation.Status.SUBMITTED
        evaluation_draft.save()
        response = jury_client.patch(
            req_eval_detail_url(
                eval_tournament.id, eval_round.id,
                submission.id, requirement_evaluation.id
            ),
            {"is_satisfied": True},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────── TournamentJuryEvaluationsView ────────────────────


@pytest.mark.django_db
class TestTournamentJuryEvaluations:

    def test_returns_200_for_jury(
        self, jury_client, eval_tournament, jury_assignment
    ):
        response = jury_client.get(jury_evaluations_url(eval_tournament.id))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_403_for_non_jury(self, auth_client_only, eval_tournament):
        response = auth_client_only.get(jury_evaluations_url(eval_tournament.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_nonexistent_tournament(self, jury_client):
        response = jury_client.get(jury_evaluations_url(99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_filter_by_status_draft(
        self, jury_client, eval_tournament, submission, evaluation_draft, jury_assignment
    ):
        response = jury_client.get(
            jury_evaluations_url(eval_tournament.id),
            {"status": Evaluation.Status.DRAFT},
        )
        ids = [e["id"] for e in response.data]
        assert evaluation_draft.id in ids


# ─────────────────── TournamentJuryEvaluationsCountView ───────────────


@pytest.mark.django_db
class TestTournamentJuryEvaluationsCount:

    def test_returns_count(
        self, jury_client, eval_tournament, submission, evaluation_draft, jury_assignment
    ):
        response = jury_client.get(jury_evaluations_count_url(eval_tournament.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_returns_403_for_non_jury(self, auth_client_only, eval_tournament):
        response = auth_client_only.get(jury_evaluations_count_url(eval_tournament.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN
