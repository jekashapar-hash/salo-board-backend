from django.contrib import admin
from django.urls import path
from .views import *

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", obtain_auth_token, name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
]
