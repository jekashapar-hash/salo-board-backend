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
    path("login", obtain_auth_token, name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("schema", SpectacularAPIView.as_view(), name="schema"),
    path("docs", SpectacularSwaggerView.as_view(url_name="schema")),
    path("redoc", SpectacularRedocView.as_view(url_name="schema")),
]
