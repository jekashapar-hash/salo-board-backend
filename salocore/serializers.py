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


class UserProfileSerializer(serializers.Serializer):
    # User fields
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)

    # UserProfile fields
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    organization = serializers.CharField(max_length=100, required=False, allow_blank=True)
    telegram = serializers.CharField(max_length=100, required=False, allow_blank=True)
    discord = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def to_representation(self, instance):
        """instance is a User object"""
        profile = instance.userprofile
        return {
            "firstName": instance.first_name,
            "lastName": instance.last_name,
            "city": profile.city,
            "organization": profile.organization,
            "telegram": profile.telegram,
            "discord": profile.discord,
        }

    def update(self, instance, validated_data):
        # Update User fields
        user_fields = ("first_name", "last_name")
        profile_fields = ("city", "organization", "telegram", "discord")

        user_updated = False
        for field in user_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
                user_updated = True
        if user_updated:
            instance.save(update_fields=[f for f in user_fields if f in validated_data])

        profile = instance.userprofile
        for field in profile_fields:
            if field in validated_data:
                setattr(profile, field, validated_data[field])
        profile.save()

        return instance


class UserNameSerializer(serializers.Serializer):
    firstName = serializers.CharField(read_only=True, help_text="Ім'я користувача")
    lastName = serializers.CharField(read_only=True, help_text="Прізвище користувача")

    def to_representation(self, instance):
        return {
            "firstName": instance.first_name,
            "lastName": instance.last_name,
        }


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

class TournamentJurySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = TournamentJury
        fields = ['id', 'user', 'username', 'tournament']
        read_only_fields = ['id', 'user', 'username', 'tournament']

class TournamentAdminSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = TournamentAdmin
        fields = ['id', 'user', 'username', 'tournament']
        read_only_fields = ['id', 'user', 'username', 'tournament']


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


# -------------------------- Chat ------------------------------------------

class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = ["id", "user", "is_solved", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class MessageSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "chat", "user", "username", "text", "created_at"]
        read_only_fields = ["id", "chat", "user", "username", "created_at"]
