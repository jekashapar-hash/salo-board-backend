from django.contrib import admin

from .models import (
    Chat,
    CriterionEvaluation,
    Evaluation,
    EvaluationCriterion,
    Message,
    Notification,
    RequirementEvaluation,
    Round,
    RoundAttachment,
    RoundRequirement,
    Submission,
    Team,
    TeamMember,
    Tournament,
    TournamentJury,
    User,
    UserProfile,
)
from .models import (
    TournamentAdmin as TournamentAdminModel,
)

admin.site.register(User)
admin.site.register(UserProfile)
admin.site.register(Tournament)
admin.site.register(TournamentJury)
admin.site.register(TournamentAdminModel)
admin.site.register(Round)
admin.site.register(EvaluationCriterion)
admin.site.register(RoundRequirement)
admin.site.register(RoundAttachment)
admin.site.register(Team)
admin.site.register(TeamMember)
admin.site.register(Submission)
admin.site.register(Evaluation)
admin.site.register(CriterionEvaluation)
admin.site.register(RequirementEvaluation)
admin.site.register(Chat)
admin.site.register(Message)
admin.site.register(Notification)
