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
]
