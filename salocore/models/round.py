from django.core.validators import MinValueValidator
from django.db import models

from .tournament import Tournament


class Round(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DR", "Draft"
        ACTIVE = "AC", "Active"
        SUBMISSION_CLOSED = "SC", "Submission Closed"
        EVALUATED = "EV", "Evaluated"

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField()
    order_index = models.IntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    start_at = models.DateTimeField()
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class EvaluationCriterion(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    category = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    max_score = models.IntegerField(validators=[MinValueValidator(1)])
    weight = models.IntegerField(validators=[MinValueValidator(1)])
    order_index = models.IntegerField()

    def __str__(self):
        return self.title


class RoundRequirement(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    text = models.TextField()
    order_index = models.IntegerField()

    def __str__(self):
        return self.text


class RoundAttachment(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    label = models.CharField(max_length=100)
    url = models.CharField(max_length=200)
    order_index = models.IntegerField()
