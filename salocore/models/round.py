from django.db.models import IntegerField
from django.db import models
from .tournament import Tournament


class Round(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DR", "Draft"
        ACTIVE = "RG", "Active"
        SUBMISSION_CLOSED = "SC", "Submission Closed"
        EVALUATED = "EV", "Evaluated"

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField()
    requirements = models.TextField()
    orderindex = IntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    start_at = models.DateTimeField()
    deadline = models.DateTimeField()
    attachment = models.ForeignKey()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class EvaluationCriterion(models.Model):

    class Category(models.TextChoices):
        BACKEND = "BE", "Backend"
        DATABASE = "DB", "Database"
        FRONTEND = "FE", "Frontend"
        FUNCTIONALITY = "FU", "Functionality"

    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=Category.choices)
    title = models.CharField(max_length=100)
    max_score = models.IntegerField()
    weight = models.IntegerField()
    order_index = IntegerField()

    def __str__(self):
        return self.title


class RoundRequirement(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    text = models.TextField()
    has_value = models.BooleanField(default=False)
    order_index = IntegerField()

    def __str__(self):
        return self.text
