from django.db import models
from django.utils import timezone
from saloboard import settings


class Tournament(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DR", "Draft"
        REGISTRATION = "RG", "Registration"
        RUNNING = "RN", "Running"
        FINISHED = "FN", "Finished"
        ARCHIVED = "AR", "Archived"

    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField()
    rules = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    start_date = models.DateTimeField()
    reg_open_at = models.DateTimeField()
    reg_close_at = models.DateTimeField()
    min_team_size = models.IntegerField()
    max_team_size = models.IntegerField()
    max_team = models.IntegerField()
    is_team_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField()

    def __str__(self):
        return self.title


class TournamentJury(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)


class TournamentAdmin(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
