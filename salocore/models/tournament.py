from django.db import models
from django.conf import settings


class Tournament(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DR", "Draft"
        REGISTRATION = "RG", "Registration"
        RUNNING = "RN", "Running"
        FINISHED = "FN", "Finished"

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
    max_team_size = models.IntegerField()
    is_team_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class TournamentJury(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    jury = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
