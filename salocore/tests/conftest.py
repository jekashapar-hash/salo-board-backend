import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from salocore.models import (
    EvaluationCriterion,
    Round,
    RoundAttachment,
    RoundRequirement,
    Submission,
    Team,
    TeamMember,
    Tournament,
    User,
)

# ─────────────────────────── Base clients ────────────────────────────


@pytest.fixture
def api_client():
    """Чистий DRF-клієнт без авторизації."""
    return APIClient()


@pytest.fixture
def user(db):
    """Звичайний користувач у БД."""
    return User.objects.create_user(
        username="testuser",
        email="testuser@mail.com",
        password="TestPass123!",
        invite_code="TESTCODE",
    )


@pytest.fixture
def auth_client(api_client, user):
    """DRF-клієнт, авторизований як user, + його refresh-токен."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client, str(refresh)


@pytest.fixture
def auth_client_only(api_client, user):
    """DRF-клієнт авторизований як user (без refresh токена)."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


# ─────────────────────────── Admin users ────────────────────────────


@pytest.fixture
def admin_user(db):
    """Стаф-юзер (is_staff=True)."""
    return User.objects.create_user(
        username="adminuser",
        email="admin@mail.com",
        password="AdminPass123!",
        is_staff=True,
        invite_code="ADMINCODE",
    )


@pytest.fixture
def superuser(db):
    """Суперюзер (is_staff=True + is_superuser=True)."""
    return User.objects.create_superuser(
        username="superuser",
        email="super@mail.com",
        password="SuperPass123!",
    )


@pytest.fixture
def admin_client(api_client, admin_user):
    """DRF-клієнт авторизований як admin_user."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def superuser_client(api_client, superuser):
    """DRF-клієнт авторизований як superuser."""
    refresh = RefreshToken.for_user(superuser)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


# ─────────────────────────── Tournament fixtures ─────────────────────


@pytest.fixture
def tournament(db, admin_user):
    """Турнір у стані REGISTRATION."""
    now = timezone.now()
    return Tournament.objects.create(
        title="Test Tournament",
        description="Desc",
        rules="Rules",
        status=Tournament.Status.REGISTRATION,
        creator=admin_user,
        max_team=10,
        max_team_size=5,
        min_team_size=1,
        is_team_visible=True,
        reg_open_at=now,
        reg_close_at=now + timezone.timedelta(days=1),
        start_date=now + timezone.timedelta(days=2),
        ended_at=now + timezone.timedelta(days=3),
    )


@pytest.fixture
def tournament_draft(db, admin_user):
    """Турнір у стані DRAFT."""
    now = timezone.now()
    return Tournament.objects.create(
        title="Draft Tournament",
        description="Desc",
        rules="Rules",
        status=Tournament.Status.DRAFT,
        creator=admin_user,
        max_team=10,
        max_team_size=5,
        min_team_size=1,
        is_team_visible=True,
        reg_open_at=now,
        reg_close_at=now + timezone.timedelta(days=1),
        start_date=now + timezone.timedelta(days=2),
        ended_at=now + timezone.timedelta(days=3),
    )


@pytest.fixture
def tournament_running(db, admin_user):
    """Турнір у стані RUNNING."""
    now = timezone.now()
    return Tournament.objects.create(
        title="Running Tournament",
        description="Desc",
        rules="Rules",
        status=Tournament.Status.RUNNING,
        creator=admin_user,
        max_team=10,
        max_team_size=5,
        min_team_size=1,
        is_team_visible=True,
        reg_open_at=now - timezone.timedelta(days=2),
        reg_close_at=now - timezone.timedelta(days=1),
        start_date=now,
        ended_at=now + timezone.timedelta(days=1),
    )


@pytest.fixture
def tournament_finished(db, admin_user):
    """Турнір у стані FINISHED."""
    now = timezone.now()
    return Tournament.objects.create(
        title="Finished Tournament",
        description="Desc",
        rules="Rules",
        status=Tournament.Status.FINISHED,
        creator=admin_user,
        max_team=10,
        max_team_size=5,
        min_team_size=1,
        is_team_visible=True,
        reg_open_at=now - timezone.timedelta(days=4),
        reg_close_at=now - timezone.timedelta(days=3),
        start_date=now - timezone.timedelta(days=2),
        ended_at=now - timezone.timedelta(days=1),
    )


@pytest.fixture
def tournament_archived(db, admin_user):
    """Архівний турнір."""
    now = timezone.now()
    return Tournament.objects.create(
        title="Archived Tournament",
        description="Desc",
        rules="Rules",
        status=Tournament.Status.ARCHIVED,
        creator=admin_user,
        max_team=10,
        max_team_size=5,
        min_team_size=1,
        is_team_visible=True,
        start_date=now - timezone.timedelta(days=30),
        reg_open_at=now - timezone.timedelta(days=40),
        reg_close_at=now - timezone.timedelta(days=35),
        ended_at=now - timezone.timedelta(days=20),
    )


# ────────────────────────── Helpers ──────────────────────────────────


class ModelFactory:
    @staticmethod
    def create_user(**kwargs):
        from salocore.models import User

        defaults = {
            "username": "testuser",
            "email": "test@user.com",
            "password": "Password123!",
            "first_name": "Test",
            "last_name": "User",
            "invite_code": "TESTCODE",
        }
        defaults.update(kwargs)
        # Using create_user to handle password hashing
        password = defaults.pop("password")
        user = User.objects.create_user(**defaults)
        user.set_password(password)
        user.save()
        return user

    @staticmethod
    def create_tournament(admin_user, **kwargs):
        now = timezone.now()
        defaults = {
            "title": "Default Tournament",
            "description": "Default Description",
            "rules": "Default Rules",
            "status": Tournament.Status.REGISTRATION,
            "creator": admin_user,
            "max_team": 10,
            "max_team_size": 5,
            "min_team_size": 1,
            "is_team_visible": True,
            "reg_open_at": now,
            "reg_close_at": now + timezone.timedelta(days=1),
            "start_date": now + timezone.timedelta(days=2),
            "ended_at": now + timezone.timedelta(days=3),
        }
        defaults.update(kwargs)
        return Tournament.objects.create(**defaults)

    @staticmethod
    def create_round(tournament, **kwargs):
        now = timezone.now()
        defaults = {
            "title": "Default Round",
            "description": "Default Description",
            "order_index": 1,
            "status": Round.Status.DRAFT,
            "start_at": now,
            "deadline": now + timezone.timedelta(days=7),
        }
        defaults.update(kwargs)
        return Round.objects.create(tournament=tournament, **defaults)

    @staticmethod
    def create_submission(team, round_obj, **kwargs):
        defaults = {
            "github_url": "https://github.com/test",
            "video_url": "https://video.com/test",
            "demo_url": "https://demo.com/test",
            "description": "Default Description",
            "status": Submission.Status.DRAFT,
        }
        defaults.update(kwargs)
        return Submission.objects.create(team=team, round=round_obj, **defaults)

    @staticmethod
    def create_criterion(round_obj, **kwargs):
        defaults = {
            "category": "Default Category",
            "title": "Default Criterion",
            "max_score": 10,
            "weight": 1,
            "order_index": 1,
        }
        defaults.update(kwargs)
        return EvaluationCriterion.objects.create(round=round_obj, **defaults)

    @staticmethod
    def create_requirement(round_obj, **kwargs):
        defaults = {
            "text": "Default Requirement",
            "order_index": 1,
        }
        defaults.update(kwargs)
        return RoundRequirement.objects.create(round=round_obj, **defaults)

    @staticmethod
    def create_attachment(round_obj, **kwargs):
        defaults = {
            "label": "Default Attachment",
            "url": "https://example.com/default",
            "order_index": 1,
        }
        defaults.update(kwargs)
        return RoundAttachment.objects.create(round=round_obj, **defaults)


@pytest.fixture
def factory():
    return ModelFactory


# ─────────────────────────── Team fixtures ───────────────────────────


@pytest.fixture
def team(db, tournament, user):
    """Команда з user як капітаном."""
    t = Team.objects.create(
        tournament=tournament,
        name="Team Alpha",
        status=Team.Status.REGISTRATED,
    )
    TeamMember.objects.create(team=t, user=user, is_captain=True)
    return t


@pytest.fixture
def other_user(db):
    """Інший звичайний користувач."""
    return User.objects.create_user(
        username="otheruser",
        email="other@mail.com",
        password="OtherPass123!",
        invite_code="OTHRCODE",
    )


@pytest.fixture
def other_client(api_client, other_user):
    """DRF-клієнт авторизований як other_user."""
    refresh = RefreshToken.for_user(other_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client
