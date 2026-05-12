from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

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
    TournamentAdmin,
    TournamentJury,
    User,
)

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

    def validate_email(self, value):
        return value.lower()


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
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    date_joined = serializers.DateTimeField(read_only=True)
    invite_code = serializers.CharField(read_only=True)

    # UserProfile fields
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    organization = serializers.CharField(max_length=100, required=False, allow_blank=True)
    telegram = serializers.CharField(max_length=100, required=False, allow_blank=True)
    discord = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def to_representation(self, instance):
        """instance is a User object"""
        profile = instance.userprofile
        return {
            "email": instance.email,
            "firstName": instance.first_name,
            "lastName": instance.last_name,
            "dateJoined": instance.date_joined,
            "inviteCode": instance.invite_code,
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

    def validate_telegram(self, value):
        if value:
            val = value.strip()
            if not (val.startswith("@") or val.startswith("t.me/") or val.startswith("https://t.me/")):
                raise serializers.ValidationError("Telegram має починатися з @, t.me/ або https://t.me/")
            if len(val) < 4:
                raise serializers.ValidationError("Введений рядок занадто короткий.")
        return value


class UserNameSerializer(serializers.Serializer):
    firstName = serializers.CharField(read_only=True, help_text="Ім'я користувача")
    lastName = serializers.CharField(read_only=True, help_text="Прізвище користувача")

    def to_representation(self, instance):
        return {
            "firstName": instance.first_name,
            "lastName": instance.last_name,
        }


class UserRolesSerializer(serializers.Serializer):
    participant = serializers.BooleanField(help_text="Користувач є у команді активного турніру")
    jury = serializers.BooleanField(help_text="Користувач є журі в активному турнірі")
    admin = serializers.BooleanField(help_text="Користувач є персоналом (staff)")


class UserTournamentHistoryItemSerializer(serializers.Serializer):
    """Один запис в історії участі користувача у турнірі."""

    id = serializers.IntegerField(help_text="ID турніру")
    title = serializers.CharField(help_text="Назва турніру")
    status = serializers.CharField(help_text="Статус турніру")
    start_date = serializers.DateTimeField(help_text="Дата початку")
    ended_at = serializers.DateTimeField(help_text="Дата завершення")
    role = serializers.ChoiceField(
        choices=["participant", "jury", "admin"],
        help_text="Роль користувача у цьому турнірі",
    )
    team_id = serializers.IntegerField(
        allow_null=True,
        help_text="ID команди (тільки для ролі participant)",
    )
    team_name = serializers.CharField(
        allow_null=True,
        help_text="Назва команди (тільки для ролі participant)",
    )


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

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        reg_open_at = attrs.get("reg_open_at", getattr(self.instance, "reg_open_at", None))
        reg_close_at = attrs.get("reg_close_at", getattr(self.instance, "reg_close_at", None))
        ended_at = attrs.get("ended_at", getattr(self.instance, "ended_at", None))

        errors = {}
        if reg_open_at and reg_close_at and reg_open_at > reg_close_at:
            errors["reg_close_at"] = "Реєстрація має закінчуватись після її початку або одночасно."
        if reg_close_at and start_date and reg_close_at > start_date:
            errors["start_date"] = "Турнір не може початися до закриття реєстрації."
        if start_date and ended_at and start_date > ended_at:
            errors["ended_at"] = "Турнір має закінчуватись після свого початку або одночасно."

        if errors:
            raise serializers.ValidationError(errors)
        return attrs


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

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        reg_open_at = attrs.get("reg_open_at", getattr(self.instance, "reg_open_at", None))
        reg_close_at = attrs.get("reg_close_at", getattr(self.instance, "reg_close_at", None))
        ended_at = attrs.get("ended_at", getattr(self.instance, "ended_at", None))

        errors = {}
        if reg_open_at and reg_close_at and reg_open_at > reg_close_at:
            errors["reg_close_at"] = "Реєстрація має закінчуватись після її початку або одночасно."
        if reg_close_at and start_date and reg_close_at > start_date:
            errors["start_date"] = "Турнір не може початися до закриття реєстрації."
        if start_date and ended_at and start_date > ended_at:
            errors["ended_at"] = "Турнір має закінчуватись після свого початку або одночасно."

        min_team = attrs.get("min_team_size", getattr(self.instance, "min_team_size", None))
        max_team_size = attrs.get("max_team_size", getattr(self.instance, "max_team_size", None))
        if min_team is not None and max_team_size is not None and min_team > max_team_size:
            errors["max_team_size"] = "Максимальний розмір команди не може бути меншим за мінімальний."

        max_team = attrs.get("max_team", getattr(self.instance, "max_team", None))
        if max_team is not None and max_team < 1:
            errors["max_team"] = "Максимальна кількість команд має бути більше 0."

        if min_team is not None and min_team < 1:
            errors["min_team_size"] = "Команда має складатися хоча б з однієї людини."

        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class TournamentJurySerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = TournamentJury
        fields = ["id", "user", "first_name", "last_name", "tournament"]
        read_only_fields = ["id", "user", "first_name", "last_name", "tournament"]


class TournamentAdminSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = TournamentAdmin
        fields = ["id", "user", "first_name", "last_name", "tournament"]
        read_only_fields = ["id", "user", "first_name", "last_name", "tournament"]


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name", "status", "tournament"]
        read_only_fields = ("id", "status")


class TeamMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_first_name = serializers.CharField(source="user.first_name", read_only=True)
    user_last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = TeamMember
        fields = [
            "id",
            "team",
            "user",
            "user_email",
            "user_first_name",
            "user_last_name",
            "is_captain",
            "created_at",
        ]
        read_only_fields = ("id", "created_at", "team", "user", "is_captain")


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ("id", "created_at", "how_long_active", "status", "user")


class LeaderboardRoundShortSerializer(serializers.Serializer):
    roundId = serializers.IntegerField(source="round_id")
    roundTitle = serializers.CharField(source="round_title")
    roundMaxScore = serializers.FloatField()
    teamRoundScore = serializers.FloatField()


class LeaderboardItemSerializer(serializers.Serializer):
    team_id = serializers.IntegerField()
    team_name = serializers.CharField()
    total_score = serializers.FloatField()
    rounds = LeaderboardRoundShortSerializer(many=True)


class LeaderboardCriterionSerializer(serializers.Serializer):
    criterion = serializers.IntegerField(source="criterion_id")
    category = serializers.CharField()
    title = serializers.CharField()
    score = serializers.FloatField()
    max_score = serializers.IntegerField()
    weight = serializers.IntegerField()


class LeaderboardTeamRoundSerializer(serializers.Serializer):
    round_id = serializers.IntegerField()
    round_title = serializers.CharField()
    criterions = LeaderboardCriterionSerializer(many=True)


# -------------------------- Rounds & Requirements ------------------------------------------


class RoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Round
        fields = "__all__"
        read_only_fields = ("id", "tournament")

    def validate(self, attrs):
        start_at = attrs.get("start_at", getattr(self.instance, "start_at", None))
        deadline = attrs.get("deadline", getattr(self.instance, "deadline", None))

        if start_at and deadline and start_at > deadline:
            raise serializers.ValidationError({"deadline": "Дедлайн раунду має бути після його початку або одночасно."})

        return attrs


class RoundShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Round
        exclude = ("description", "created_at", "updated_at")
        read_only_fields = ("id", "tournament")


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


class UserSubmissionSerializer(serializers.Serializer):
    """Сабміт з повним контекстом (турнір, раунд, команда) для особистого кабінету."""

    id = serializers.IntegerField(help_text="ID сабміту")
    status = serializers.CharField(help_text="Статус сабміту (DR/SB/LK)")
    github_url = serializers.CharField(help_text="Посилання на GitHub")
    video_url = serializers.CharField(help_text="Посилання на відео")
    demo_url = serializers.CharField(help_text="Посилання на демо")
    description = serializers.CharField(help_text="Опис рішення")
    created_at = serializers.DateTimeField(help_text="Дата створення")
    submitted_at = serializers.DateTimeField(allow_null=True, help_text="Дата подачі")
    # Команда
    team_id = serializers.IntegerField(help_text="ID команди")
    team_name = serializers.CharField(help_text="Назва команди")
    # Раунд
    round_id = serializers.IntegerField(help_text="ID раунду")
    round_title = serializers.CharField(help_text="Назва раунду")
    round_deadline = serializers.DateTimeField(help_text="Дедлайн раунду")
    # Турнір
    tournament_id = serializers.IntegerField(help_text="ID турніру")
    tournament_title = serializers.CharField(help_text="Назва турніру")
    tournament_status = serializers.CharField(help_text="Статус турніру")


class EvaluationSerializer(serializers.ModelSerializer):
    jury_first_name = serializers.CharField(source="jury.first_name", read_only=True)
    jury_last_name = serializers.CharField(source="jury.last_name", read_only=True)

    class Meta:
        model = Evaluation
        fields = [
            "id",
            "jury",
            "jury_first_name",
            "jury_last_name",
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

    def validate_score(self, value):
        # criterion is read_only, so it lives in the instance during PATCH
        criterion = getattr(self.instance, "criterion", None)
        if criterion is not None:
            if value < 0:
                raise serializers.ValidationError("Бал не може бути відёмним.")
            if value > criterion.max_score:
                raise serializers.ValidationError(f"Бал не може перевищувати максимальний бал ({criterion.max_score}).")
        return value


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
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "chat", "user", "first_name", "last_name", "text", "created_at"]
        read_only_fields = ["id", "chat", "user", "first_name", "last_name", "created_at"]
