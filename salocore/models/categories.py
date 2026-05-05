from django.conf import settings
from django.db import models


class Chat(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_solved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    class ActionType(models.TextChoices):
        YES_NO = "YN", "Yes/No"
        NONE = "NN", "None"
        MESSAGE = "MG", "Message"

    class Type(models.TextChoices):
        JURY_INVITE = "JI", "Jury Invite"
        TEAM_INVITE = "TI", "Team Invite"
        ADMIN_INVITE = "AI", "Admin Invite"
        KICKED_FROM_TEAM = "KT", "Kicked from Team"
        KICKED_FROM_JURY = "KJ", "Kicked from Jury"
        KICKED_FROM_ADMIN = "KA", "Kicked from Admin"
        TOURNAMENT_REG_START = "TRS", "Tournament reg start"
        TOURNAMENT_REG_END = "TRE", "Tournament reg end"
        TOURNAMENT_FINISHED = "TF", "Tournament finished"
        ROUND_STARTED = "RS", "Round started"
        SUBMISSION_DEADLINE_SOON = "SD", "Submission Deadline Soon"
        SUBMISSION_FINISHED = "SF", "Submission finished"
        EVALUATION_FINISHED = "EF", "Evaluation Finished"

    class Status(models.TextChoices):
        UNREAD = "UR", "Unread"
        READ = "RD", "Read"
        ARCHIVED = "AR", "Archived"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=Type.choices)
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    action_url = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNREAD)
    how_long_active = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
