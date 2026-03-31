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
    path("tournaments", TournamentListView.as_view(), name="tournament-list"),
    path(
        "tournaments/<int:tournament_id>",
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
        "teams",
        TeamListView.as_view(),
    ),
    path(
        "teams/archive",
        TeamArchiveListView.as_view(),
    ),
    path(
        "teams/<int:team_id>",
        TeamDetailView.as_view(),
    ),
    path(
        "teams/<int:team_id>/participant",
        TeamParticipantListCreateView.as_view(),
    ),
    path(
        "teams/<int:team_id>/participant/<str:user_id>",
        TeamParticipantDetailView.as_view(),
    ),
    path(
        "teams/<int:team_id>/participant/can-add",
        TeamCanCreateParticipantView.as_view(),
    ),
    path(
        "teams/<int:team_id>/submit",
        TeamSubmitListView.as_view(),
    ),
    path(
        "teams/<int:team_id>/submit/<int:submit_id>",
        TeamSubmitDetailView.as_view(),
    ),
    path(
        "notifications",
        NotificationListView.as_view(),
    ),
    path(
        "notifications/archive",
        NotificationArchiveListView.as_view(),
    ),
    path(
        "notifications/<int:notification_id>",
        NotificationDetailView.as_view(),
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>/submissions/<int:submission_id>/evaluation",
        EvaluationDetailView.as_view(),
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>/submissions/<int:submission_id>/evaluation/criterion-evaluation",
        EvaluationCriterionListView.as_view(),
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>/submissions/<int:submission_id>/evaluation/criterion-evaluation/<int:crit_eval_id>",
        CriterionEvaluationDetailView.as_view(),
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>/submissions/<int:submission_id>/evaluation/requirement-evaluation",
        EvaluationRequirementListView.as_view(),
    ),
    path(
        "tournaments/<int:tournament_id>/rounds/<int:round_id>/submissions/<int:submission_id>/evaluation/requirement-evaluation/<int:req_eval_id>",
        RequirementEvaluationDetailView.as_view(),
    ),
    path(
        "user",
        UserProfileView.as_view(),
        name="user-profile",
    ),
    path("admin/tournaments", AdminTournamentListView.as_view()),
    path("admin/tournaments/<int:tournament_id>", AdminTournamentDetailView.as_view()),
    path(
        "admin/tournaments/<int:tournament_id>/start",
        AdminTournamentStartView.as_view(),
    ),
    path(
        "admin/tournaments/<int:tournament_id>/jury", AdminTournamentJuryView.as_view()
    ),
    path(
        "admin/tournaments/<int:tournament_id>/admin",
        AdminTournamentAdminsView.as_view(),
    ),
    path("admin/tournaments/<int:tournament_id>/rounds", AdminRoundListView.as_view()),
    path(
        "admin/tournaments/<int:tournament_id>/rounds/<int:round_id>",
        AdminRoundDetailView.as_view(),
    ),
    path(
        "admin/tournaments/<int:tournament_id>/rounds/<int:round_id>/start",
        AdminRoundStartView.as_view(),
    ),
    path(
        "admin/tournaments/<int:tournament_id>/rounds/<int:round_id>/attachment",
        AdminRoundAttachmentView.as_view(),
    ),
    path(
        "admin/tournaments/<int:tournament_id>/rounds/<int:round_id>/requirement",
        AdminRoundRequirementView.as_view(),
    ),
    path(
        "admin/tournaments/<int:tournament_id>/rounds/<int:round_id>/criterion",
        AdminRoundCriterionView.as_view(),
    ),
    path("admin/tournaments/<int:tournament_id>/teams", AdminTeamListView.as_view()),
    path(
        "admin/tournaments/<int:tournament_id>/teams/<int:team_id>/disqualify",
        AdminTeamDisqualifyView.as_view(),
    ),
    path(
        "admin/tournaments/<int:tournament_id>/teams/<int:team_id>/participants",
        AdminParticipantListView.as_view(),
    ),
    path(
        "admin/tournaments/<int:tournament_id>/teams/<int:team_id>/participants/<int:user_id>",
        AdminParticipantDetailView.as_view(),
    ),
    path(
        "admin/tournaments/<int:tournament_id>/rounds/<int:round_id>/submit",
        AdminSubmissionListView.as_view(),
    ),
    path(
        "admin/tournaments/<int:tournament_id>/rounds/<int:round_id>/submit/<int:submission_id>",
        AdminSubmissionDetailView.as_view(),
    ),
    path(
        "admin/tournaments/<int:tournament_id>/rounds/<int:round_id>/evaluation",
        AdminEvaluationListView.as_view(),
    ),
    path(
        "admin/tournaments/<int:tournament_id>/rounds/<int:round_id>/evaluation/<int:evaluation_id>",
        AdminEvaluationDetailView.as_view(),
    ),
]
