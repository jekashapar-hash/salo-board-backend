from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import *


# -------------------------- Auth ------------------------------------------


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"] = serializers.EmailField()
        if "username" in self.fields:
            del self.fields["username"]

    def validate(self, attrs):
        email = attrs.get("email")
        try:
            user = User.objects.get(email=email)
            attrs[self.username_field] = user.username
        except User.DoesNotExist:
            attrs[self.username_field] = "dummy_invalid_username"

        return super().validate(attrs)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


# ----------------------------------------------


class TournamentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = [
            "id",
            "title",
            "status",
            "start_date",
            "reg_open_at",
            "reg_close_at",
            "ended_at",
        ]
        read_only_fields = ("id",)


class TournamentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = [
            "id",
            "title",
            "description",
            "rules",
            "status",
            "start_date",
            "reg_open_at",
            "reg_close_at",
            "min_team_size",
            "max_team_size",
            "max_team",
            "is_team_visible",
            "ended_at",
        ]


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name", "status", "tournament"]
        read_only_fields = ("id", "status")


class TeamMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = TeamMember
        fields = [
            "id",
            "team",
            "user",
            "user_email",
            "user_username",
            "is_captain",
            "created_at",
        ]
        read_only_fields = ("id", "created_at", "team", "user", "is_captain")


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ("id", "created_at", "how_long_active", "status", "user")


class LeaderboardItemSerializer(serializers.Serializer):
    team_id = serializers.IntegerField()
    team_name = serializers.CharField()
    score = serializers.IntegerField()


# -------------------------- Rounds & Requirements ------------------------------------------


class RoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Round
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class EvaluationCriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationCriterion
        fields = "__all__"
        read_only_fields = ("id", "round")


class RoundRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoundRequirement
        fields = "__all__"
        read_only_fields = ("id", "round")


class RoundAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoundAttachment
        fields = "__all__"
        read_only_fields = ("id", "round")


# -------------------------- Submissions & Evaluations ------------------------------------------


class SubmissionSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id",
            "round",
            "team",
            "team_name",
            "github_url",
            "video_url",
            "demo_url",
            "description",
            "status",
            "created_at",
            "submitted_at",
        ]
        read_only_fields = ("id", "created_at", "submitted_at", "team")


class EvaluationSerializer(serializers.ModelSerializer):
    jury_username = serializers.CharField(source="jury.username", read_only=True)

    class Meta:
        model = Evaluation
        fields = [
            "id",
            "jury",
            "jury_username",
            "submission",
            "comment",
            "status",
            "created_at",
            "updated_at",
            "submitted_at",
        ]
        read_only_fields = (
            "id",
            "jury",
            "submission",
            "created_at",
            "updated_at",
            "submitted_at",
        )


class CriterionEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriterionEvaluation
        fields = "__all__"
        read_only_fields = ("id", "evaluation", "criterion")


class RequirementEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequirementEvaluation
        fields = "__all__"
        read_only_fields = ("id", "evaluation", "requirement")
