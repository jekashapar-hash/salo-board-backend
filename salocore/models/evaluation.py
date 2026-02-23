from django.db import models
from django.conf import settings
from .round import EvaluationCreterion, RoundRequirement
from .submission import Submission


class Evaluation(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DR", "Draft"
        SUBMITTED = "SB", "Submitted"

    jury = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    comment = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_all_requirement_satisfied = models.BooleanField(default=False)


class CreterionScore(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE)
    creterion = models.ForeignKey(EvaluationCreterion, on_delete=models.CASCADE)
    score = models.IntegerField()
    comment = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)


class RequirementEvaluation(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE)
    requirement = models.ForeignKey(RoundRequirement, on_delete=models.CASCADE)
    is_satisfied = models.BooleanField(default=False)
    comment = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
