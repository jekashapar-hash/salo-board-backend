from django.conf import settings
from django.db import models

from .tournament import Tournament


class Team(models.Model):
    class Status(models.TextChoices):
        REGISTRATED = "RG", "Registrated"
        DISQUALIFIED = "DQ", "Disqualified"
        ARCHIVED = "AR", "Archived"

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_captain = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
