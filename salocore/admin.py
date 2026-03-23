from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Tournament)
admin.site.register(TournamentJury)
admin.site.register(Round)
admin.site.register(EvaluationCriterion)
admin.site.register(RoundRequirement)
admin.site.register(Submission)
admin.site.register(Evaluation)
admin.site.register(CriterionEvaluation)
admin.site.register(RequirementEvaluation)
admin.site.register(User)
