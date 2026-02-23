from django.db import models
from .round import Round
from .team import Team


class Submission(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DR", "Draft"
        SUBMITTED = "SB", "Submitted"
        LOCKED = "LK", "Locked"

    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    github_url = models.CharField(max_length=200)
    video_url = models.CharField(max_length=200)
    demo_url = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
