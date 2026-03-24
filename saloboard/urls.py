from django.contrib import admin
from django.urls import path
from salocore.views import *

urlpatterns = [
    path("admin", admin.site.urls),
    path("api/", include("salocore.urls")),
]
