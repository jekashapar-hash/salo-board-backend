from django.db import models


class Team(models.Model):

    class Status(models.TextChoices):
        REGISTRATED = "RG", "Registrated"
        DISQUALIFIED = "DQ", "Disqualified"
        ARCHIVED = "AR", "Archived"

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    captain = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices)
    registrated_at = models.DateTimeField(auto_now_add=True)


class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
