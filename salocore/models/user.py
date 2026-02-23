from django.contrib.auth.models import AbstractUser
from django.db import models
from .tournament import Tournament


class User(AbstractUser):

    class Role(models.TextChoices):
        JURY = "JR", "Jury"
        PARTICIPANT = "PT", "Participant"
        ADMIN = "AD", "Admin"

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.PARTICIPANT
    )

    def __str__(self):
        return self.username


class UserAdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)


class UserJuryProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)


class TournamentHistory(models.Model):
    user = models.ForeignKey('UserParticipantProfile', on_delete=models.CASCADE)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)


class UserParticipantProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    city = models.CharField(max_length=100)
    organization = models.CharField(max_length=100)
    telegram = models.CharField(max_length=100)
    discord = models.CharField(max_length=100)
    tournament_history = models.ForeignKey(TournamentHistory, on_delete=models.CASCADE)
