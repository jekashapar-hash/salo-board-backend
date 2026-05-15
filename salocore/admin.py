from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

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
    UserTelegramProfile,
)
from .models import (
    TournamentAdmin as TournamentAdminModel,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "invite_code")
    list_filter = ("is_staff", "is_superuser", "is_active")
    fieldsets = None  # Disable tabs/fieldsets
    fields = (
        "username",
        "password",
        "first_name",
        "last_name",
        "email",
        "is_staff",
        "is_active",
        "is_superuser",
        "last_login",
        "date_joined",
        "invite_code",
    )


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "created_at", "updated_at")
    search_fields = ("title", "description")
    list_filter = ("status", "created_at")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "tournament", "created_at")
    search_fields = ("name", "tournament__title")
    list_filter = ("tournament", "created_at")


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ("title", "tournament", "order_index", "status")
    list_filter = ("tournament", "status")
    search_fields = ("title", "tournament__title")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("team", "round", "created_at")
    list_filter = ("round__tournament", "round")
    search_fields = ("team__name", "round__title")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "type", "status", "created_at")
    list_filter = ("type", "status", "created_at")
    search_fields = ("user__username", "title", "message")


@admin.register(UserTelegramProfile)
class UserTelegramProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "chat_id", "created_at", "updated_at")
    search_fields = ("user__username", "chat_id")


@admin.register(TournamentJury)
class TournamentJuryAdmin(admin.ModelAdmin):
    list_display = ("tournament", "user")
    list_filter = ("tournament",)
    search_fields = ("tournament__title", "user__username")


@admin.register(TournamentAdminModel)
class TournamentAdminModelAdmin(admin.ModelAdmin):
    list_display = ("tournament", "user")
    list_filter = ("tournament",)
    search_fields = ("tournament__title", "user__username")


# Simple registration for other models
admin.site.register(UserProfile)
admin.site.register(EvaluationCriterion)
admin.site.register(RoundRequirement)
admin.site.register(RoundAttachment)
admin.site.register(TeamMember)
admin.site.register(Evaluation)
admin.site.register(CriterionEvaluation)
admin.site.register(RequirementEvaluation)
admin.site.register(Chat)
admin.site.register(Message)
