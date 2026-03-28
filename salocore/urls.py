from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from .views import *
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", CustomTokenObtainPairView.as_view(), name="login"),
    path("token/refresh", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("schema", SpectacularAPIView.as_view(), name="schema"),
    path("docs", SpectacularSwaggerView.as_view(url_name="schema")),
    path("redoc", SpectacularRedocView.as_view(url_name="schema")),
    path("tournaments/", TournamentListView.as_view(), name="tournament-list"),
    path(
        "tournaments/<int:tournament_id>/",
        TournamentDetailView.as_view(),
        name="tournament-detail",
    ),
    path(
        "tournaments/<int:tournament_id>/teams",
        TournamentTeamsView.as_view(),
        name="tournament-teams",
    ),
    path(
        "tournaments/<int:tournament_id>/leaderboard",
        TournamentLeaderboardView.as_view(),
        name="tournament-leaderboard",
    ),
    path(
        "tournaments/<int:tournament_id>/rounds",
        RoundListView.as_view(),
        name="tournament-rounds",
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>",
        RoundDetailView.as_view(),
        name="tournament-round-detail",
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>/criterions",
        CriterionListView.as_view(),
        name="tournament-round-criterions",
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>/requirements",
        RequirementListView.as_view(),
        name="tournament-round-requirements",
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>/attachments",
        AttachmentListView.as_view(),
        name="tournament-round-attachments",
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>/submissions",
        SubmissionListView.as_view(),
        name="tournament-round-submissions",
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>/submissions/<int:submission_id>",
        SubmissionDetailView.as_view(),
        name="tournament-round-submission-detail",
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>/submissions/<int:submission_id>/evaluation",
        EvaluationDetailView.as_view(),
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>/evaluations/<int:eval_id>/criterion-evaluations",
        EvaluationCriterionListView.as_view(),
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>/evaluations/<int:eval_id>/criterion-evaluations/<int:crit_eval_id>",
        CriterionEvaluationDetailView.as_view(),
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>/evaluations/<int:eval_id>/requirement-evaluations",
        EvaluationRequirementListView.as_view(),
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>/evaluations/<int:eval_id>/requirement-evaluations/<int:req_eval_id>",
        RequirementEvaluationDetailView.as_view(),
    ),
]

