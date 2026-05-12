"""
Тести для:
  - GET /api/tournaments/<id>/rounds              → RoundListView
  - GET /api/tournaments/<id>/rounds/<id>         → RoundDetailView
  - GET /api/.../rounds/<id>/criterions           → CriterionListView
  - GET /api/.../rounds/<id>/requirements         → RequirementListView
  - GET /api/.../rounds/<id>/attachments          → AttachmentListView
"""

from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from salocore.models import (
    EvaluationCriterion,
    Round,
    RoundAttachment,
    RoundRequirement,
    Tournament,
)


# ─────────────────────────── Fixtures ────────────────────────────────


@pytest.fixture
def round_active(db, tournament_running):
    now = timezone.now()
    return Round.objects.create(
        tournament=tournament_running,
        title="Active Round",
        description="Desc",
        status=Round.Status.ACTIVE,
        start_at=now,
        deadline=now + timezone.timedelta(days=3),
        order_index=1,
    )


@pytest.fixture
def round_draft(db, tournament_running, admin_user):
    """Draft-раунд, tournament_running.creator == admin_user."""
    now = timezone.now()
    return Round.objects.create(
        tournament=tournament_running,
        title="Draft Round",
        description="Desc",
        status=Round.Status.DRAFT,
        start_at=now,
        deadline=now + timezone.timedelta(days=5),
        order_index=2,
    )


@pytest.fixture
def criterion(db, round_active):
    return EvaluationCriterion.objects.create(
        round=round_active, category="Cat", title="Crit 1",
        max_score=10, weight=1, order_index=1,
    )


@pytest.fixture
def requirement(db, round_active):
    return RoundRequirement.objects.create(
        round=round_active, text="Requirement 1", order_index=1,
    )


@pytest.fixture
def attachment(db, round_active):
    return RoundAttachment.objects.create(
        round=round_active, label="Attach 1", url="http://x.com",
        order_index=1,
    )


# ──────────────────────────── RoundListView ───────────────────────────


@pytest.mark.django_db
class TestRoundList:
    def url(self, tid):
        return reverse("tournament-rounds", kwargs={"tournament_id": tid})

    def test_returns_200_authenticated(self, auth_client_only, tournament_running, round_active):
        with patch("salocore.views.round.get_tournament_cheker") as m:
            m.return_value.check.return_value = None
            response = auth_client_only.get(self.url(tournament_running.id))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_401_unauthenticated(self, api_client, tournament_running):
        response = api_client.get(self.url(tournament_running.id))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_404_nonexistent_tournament(self, auth_client_only):
        with patch("salocore.views.round.get_tournament_cheker") as m:
            m.return_value.check.return_value = None
            response = auth_client_only.get(self.url(99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_drafts_hidden_for_non_creator(self, auth_client_only, tournament_running, round_draft):
        """Звичайний юзер не є creator → DRAFT не видно."""
        with patch("salocore.views.round.get_tournament_cheker") as m:
            m.return_value.check.return_value = None
            response = auth_client_only.get(self.url(tournament_running.id))
        ids = [r["id"] for r in response.data]
        assert round_draft.id not in ids

    def test_drafts_visible_for_creator(self, admin_client, tournament_running, round_draft):
        """Creator (admin_user) бачить DRAFT."""
        with patch("salocore.views.round.get_tournament_cheker") as m:
            m.return_value.check.return_value = None
            response = admin_client.get(self.url(tournament_running.id))
        ids = [r["id"] for r in response.data]
        assert round_draft.id in ids

    def test_filter_by_status(self, auth_client_only, tournament_running, round_active, round_draft):
        with patch("salocore.views.round.get_tournament_cheker") as m:
            m.return_value.check.return_value = None
            response = auth_client_only.get(
                self.url(tournament_running.id), {"status": Round.Status.ACTIVE}
            )
        ids = [r["id"] for r in response.data]
        assert round_active.id in ids
        assert round_draft.id not in ids


# ─────────────────────────── RoundDetailView ─────────────────────────


@pytest.mark.django_db
class TestRoundDetail:
    def url(self, tid, rid):
        return reverse("tournament-round-detail", kwargs={"tournament_id": tid, "round_id": rid})

    def test_returns_200_authenticated(self, auth_client_only, tournament_running, round_active):
        with patch("salocore.views.round.get_round_cheker") as m:
            m.return_value.check.return_value = None
            response = auth_client_only.get(self.url(tournament_running.id, round_active.id))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_401_unauthenticated(self, api_client, tournament_running, round_active):
        response = api_client.get(self.url(tournament_running.id, round_active.id))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_404_nonexistent(self, auth_client_only, tournament_running):
        with patch("salocore.views.round.get_round_cheker") as m:
            m.return_value.check.return_value = None
            response = auth_client_only.get(self.url(tournament_running.id, 99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_draft_forbidden_for_non_creator(self, auth_client_only, tournament_running, round_draft):
        """Non-creator намагається отримати DRAFT → 403."""
        with patch("salocore.views.round.get_round_cheker") as m:
            m.return_value.check.return_value = None
            response = auth_client_only.get(self.url(tournament_running.id, round_draft.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_draft_accessible_for_creator(self, admin_client, tournament_running, round_draft):
        with patch("salocore.views.round.get_round_cheker") as m:
            m.return_value.check.return_value = None
            response = admin_client.get(self.url(tournament_running.id, round_draft.id))
        assert response.status_code == status.HTTP_200_OK


# ──────────────────────── CriterionListView ───────────────────────────


@pytest.mark.django_db
class TestCriterionList:
    def url(self, tid, rid):
        return reverse("tournament-round-criterions", kwargs={"tournament_id": tid, "round_id": rid})

    def test_returns_200_without_auth(self, api_client, tournament_running, round_active):
        response = api_client.get(self.url(tournament_running.id, round_active.id))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_404_nonexistent_round(self, api_client, tournament_running):
        response = api_client.get(self.url(tournament_running.id, 99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_criteria(self, api_client, tournament_running, round_active, criterion):
        response = api_client.get(self.url(tournament_running.id, round_active.id))
        ids = [c["id"] for c in response.data]
        assert criterion.id in ids


# ─────────────────────── RequirementListView ──────────────────────────


@pytest.mark.django_db
class TestRequirementList:
    def url(self, tid, rid):
        return reverse("tournament-round-requirements", kwargs={"tournament_id": tid, "round_id": rid})

    def test_returns_200(self, api_client, tournament_running, round_active):
        response = api_client.get(self.url(tournament_running.id, round_active.id))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_404_nonexistent_round(self, api_client, tournament_running):
        response = api_client.get(self.url(tournament_running.id, 99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_requirements(self, api_client, tournament_running, round_active, requirement):
        response = api_client.get(self.url(tournament_running.id, round_active.id))
        ids = [r["id"] for r in response.data]
        assert requirement.id in ids


# ─────────────────────── AttachmentListView ───────────────────────────


@pytest.mark.django_db
class TestAttachmentList:
    def url(self, tid, rid):
        return reverse("tournament-round-attachments", kwargs={"tournament_id": tid, "round_id": rid})

    def test_returns_200(self, api_client, tournament_running, round_active):
        response = api_client.get(self.url(tournament_running.id, round_active.id))
        assert response.status_code == status.HTTP_200_OK

    def test_returns_404_nonexistent_round(self, api_client, tournament_running):
        response = api_client.get(self.url(tournament_running.id, 99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_attachments(self, api_client, tournament_running, round_active, attachment):
        response = api_client.get(self.url(tournament_running.id, round_active.id))
        ids = [a["id"] for a in response.data]
        assert attachment.id in ids
