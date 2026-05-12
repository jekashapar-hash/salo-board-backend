"""
Тести для адмін-ендпоінтів раундів:
  - GET/POST   /api/admin/tournaments/<id>/rounds
  - GET/PATCH/DELETE /api/admin/tournaments/<id>/rounds/<id>
  - PATCH      /api/admin/tournaments/<id>/rounds/<id>/start
  - POST/DELETE для attachments, requirements, criteria
"""

from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status

from salocore.models import (
    EvaluationCriterion,
    Round,
    RoundAttachment,
    RoundRequirement,
    Tournament,
)


def admin_rounds_url(tid):
    return f"/api/admin/tournaments/{tid}/rounds"


def admin_round_detail_url(tid, rid):
    return f"/api/admin/tournaments/{tid}/rounds/{rid}"


def admin_round_start_url(tid, rid):
    return f"/api/admin/tournaments/{tid}/rounds/{rid}/start"


def admin_attachment_url(tid, rid):
    return f"/api/admin/tournaments/{tid}/rounds/{rid}/attachment"


def admin_attachment_detail_url(tid, rid, pk):
    return f"/api/admin/tournaments/{tid}/rounds/{rid}/attachment/{pk}"


def admin_requirement_url(tid, rid):
    return f"/api/admin/tournaments/{tid}/rounds/{rid}/requirement"


def admin_requirement_detail_url(tid, rid, pk):
    return f"/api/admin/tournaments/{tid}/rounds/{rid}/requirement/{pk}"


def admin_criterion_url(tid, rid):
    return f"/api/admin/tournaments/{tid}/rounds/{rid}/criterion"


def admin_criterion_detail_url(tid, rid, pk):
    return f"/api/admin/tournaments/{tid}/rounds/{rid}/criterion/{pk}"


# ─────────────────── Fixtures ──────────────────────────────────────────


@pytest.fixture
def running_t(db, admin_user, factory):
    return factory.create_tournament(admin_user, title="Running T", status=Tournament.Status.RUNNING)


@pytest.fixture
def draft_round(db, tournament_draft, factory):
    return factory.create_round(tournament_draft, title="Draft Round", status=Round.Status.DRAFT)


@pytest.fixture
def active_round(db, running_t, factory):
    return factory.create_round(running_t, title="Active Round", status=Round.Status.ACTIVE)


@pytest.fixture
def round_with_crit_and_req(db, running_t, factory):
    r = factory.create_round(running_t, title="Full Round", status=Round.Status.DRAFT, order_index=2)
    factory.create_criterion(r, title="Crit 1")
    factory.create_requirement(r, text="Req 1")
    return r


# ─────────────────── AdminRoundListView ────────────────────────────────


@pytest.mark.django_db
class TestAdminRoundList:

    def test_get_lists_rounds(self, admin_client, tournament_draft, draft_round):
        response = admin_client.get(admin_rounds_url(tournament_draft.id))
        assert response.status_code == status.HTTP_200_OK
        ids = [r["id"] for r in response.data]
        assert draft_round.id in ids

    def test_returns_403_for_regular_user(self, auth_client_only, tournament_draft):
        response = auth_client_only.get(admin_rounds_url(tournament_draft.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_post_creates_round(self, admin_client, tournament_draft):
        payload = {
            "title": "New Round", "description": "Desc",
            "order_index": 1,
            "start_at": timezone.now().isoformat(),
            "deadline": (timezone.now() + timezone.timedelta(days=1)).isoformat(),
        }
        response = admin_client.post(admin_rounds_url(tournament_draft.id), payload)
        assert response.status_code == status.HTTP_201_CREATED

    def test_post_fails_invalid_data(self, admin_client, tournament_draft):
        response = admin_client.post(admin_rounds_url(tournament_draft.id), {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────── AdminRoundDetailView ─────────────────────────────


@pytest.mark.django_db
class TestAdminRoundDetail:

    def test_get_returns_round(self, admin_client, tournament_draft, draft_round):
        response = admin_client.get(admin_round_detail_url(tournament_draft.id, draft_round.id))
        assert response.status_code == status.HTTP_200_OK

    def test_patch_edits_draft_round(self, admin_client, tournament_draft, draft_round):
        with patch("salocore.views.admin_round.get_round_cheker") as m:
            m.return_value.check.return_value = None
            response = admin_client.patch(
                admin_round_detail_url(tournament_draft.id, draft_round.id),
                {"title": "Updated Round"},
            )
        assert response.status_code == status.HTTP_200_OK
        draft_round.refresh_from_db()
        assert draft_round.title == "Updated Round"

    def test_patch_fails_non_draft(self, admin_client, running_t, active_round):
        response = admin_client.patch(
            admin_round_detail_url(running_t.id, active_round.id),
            {"title": "X"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_draft_round(self, admin_client, tournament_draft, draft_round):
        response = admin_client.delete(
            admin_round_detail_url(tournament_draft.id, draft_round.id)
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_fails_non_draft(self, admin_client, running_t, active_round):
        response = admin_client.delete(
            admin_round_detail_url(running_t.id, active_round.id)
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────── AdminRoundStartView ──────────────────────────────


@pytest.mark.django_db
class TestAdminRoundStart:

    def test_activates_round_with_crit_and_req(self, admin_client, running_t, round_with_crit_and_req):
        with patch("salocore.views.admin_round.get_round_cheker") as m:
            m.return_value.check.return_value = None
            response = admin_client.patch(
                admin_round_start_url(running_t.id, round_with_crit_and_req.id)
            )
        assert response.status_code == status.HTTP_200_OK
        round_with_crit_and_req.refresh_from_db()
        assert round_with_crit_and_req.status == Round.Status.ACTIVE

    def test_fails_if_no_criteria(self, admin_client, running_t, factory):
        r = factory.create_round(running_t, title="No Crit", status=Round.Status.DRAFT, order_index=3)
        factory.create_requirement(r, text="Req")
        response = admin_client.patch(admin_round_start_url(running_t.id, r.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_fails_if_no_requirements(self, admin_client, running_t, factory):
        r = factory.create_round(running_t, title="No Req", status=Round.Status.DRAFT, order_index=4)
        factory.create_criterion(r, title="C")
        response = admin_client.patch(admin_round_start_url(running_t.id, r.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_fails_if_tournament_not_running(self, admin_client, tournament_draft, draft_round, factory):
        factory.create_criterion(draft_round, title="C")
        factory.create_requirement(draft_round, text="R")
        response = admin_client.patch(
            admin_round_start_url(tournament_draft.id, draft_round.id)
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_fails_if_not_draft(self, admin_client, running_t, active_round):
        response = admin_client.patch(admin_round_start_url(running_t.id, active_round.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────── Attachments ──────────────────────────────────────


@pytest.mark.django_db
class TestAdminRoundAttachment:

    def test_post_creates_attachment(self, admin_client, tournament_draft, draft_round):
        response = admin_client.post(
            admin_attachment_url(tournament_draft.id, draft_round.id),
            {"label": "Attach 1", "url": "https://example.com", "order_index": 1},
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_delete_removes_attachment(self, admin_client, tournament_draft, draft_round, factory):
        att = factory.create_attachment(draft_round, label="A")
        response = admin_client.delete(
            admin_attachment_detail_url(tournament_draft.id, draft_round.id, att.id)
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_returns_404_nonexistent(self, admin_client, tournament_draft, draft_round):
        response = admin_client.delete(
            admin_attachment_detail_url(tournament_draft.id, draft_round.id, 99999)
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ─────────────────── Requirements ─────────────────────────────────────


@pytest.mark.django_db
class TestAdminRoundRequirement:

    def test_post_creates_requirement(self, admin_client, tournament_draft, draft_round):
        response = admin_client.post(
            admin_requirement_url(tournament_draft.id, draft_round.id),
            {"text": "Must have tests", "order_index": 1},
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_delete_removes_requirement(self, admin_client, tournament_draft, draft_round, factory):
        req = factory.create_requirement(draft_round, text="R")
        response = admin_client.delete(
            admin_requirement_detail_url(tournament_draft.id, draft_round.id, req.id)
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


# ─────────────────── Criteria ─────────────────────────────────────────


@pytest.mark.django_db
class TestAdminRoundCriterion:

    def test_post_creates_criterion(self, admin_client, tournament_draft, draft_round):
        response = admin_client.post(
            admin_criterion_url(tournament_draft.id, draft_round.id),
            {
                "title": "Innovation", "category": "Cat", "max_score": 20,
                "weight": 1, "order_index": 1
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_delete_removes_criterion(self, admin_client, tournament_draft, draft_round, factory):
        crit = factory.create_criterion(draft_round, title="C")
        response = admin_client.delete(
            admin_criterion_detail_url(tournament_draft.id, draft_round.id, crit.id)
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
