from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User, Tournament, Team, Round, Submission, CriterionEvaluation
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce
from .serializers import *
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample,
    OpenApiParameter,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# -------------------------- Auth ------------------------------------------


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        summary="Логін",
        description="Отримання JWT: access і refresh токенів через JSON body.",
        responses={
            200: TokenResponseSerializer,
            400: OpenApiResponse(
                description="Не передані обов'язкові поля (email або password)",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Validation Error",
                        value={
                            "email": ["This field is required."],
                            "password": ["This field is required."],
                        },
                    )
                ],
            ),
            401: OpenApiResponse(
                description="Невірний логін або пароль (No active account found with the given credentials)",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Unauthorized",
                        value={
                            "detail": "No active account found with the given credentials"
                        },
                    )
                ],
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenRefreshView(TokenRefreshView):
    @extend_schema(
        summary="Оновлення токена",
        description="Отримання нового access токена по refresh токену.",
        responses={
            200: OpenApiResponse(
                description="Успішне оновлення токена",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Success",
                        value={"access": "eyJhbGciOiJIUzI1NiIsInR5c..."},
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Не передано refresh токен",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Validation Error",
                        value={"refresh": ["This field is required."]},
                    )
                ],
            ),
            401: OpenApiResponse(
                description="Недійсний або прострочений refresh токен",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Unauthorized",
                        value={
                            "detail": "Token is invalid or expired",
                            "code": "token_not_valid",
                        },
                    )
                ],
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RegisterView(APIView):
    permission_classes = [AllowAny]  # <-- доступ без авторизації

    @extend_schema(
        summary="Реєстрація",
        description="Реєстрація нового користувача і отримання JWT токенів",
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(
                description="Успішна реєстрація",
                response=TokenResponseSerializer,
            ),
            400: OpenApiResponse(
                description="Помилка валідації або такий користувач вже існує",
                response=dict,
                examples=[
                    OpenApiExample(
                        "User Exists",
                        value={"error": "Користувач вже існує"},
                    ),
                    OpenApiExample(
                        "Validation Error",
                        value={
                            "email": ["This field is required."],
                            "password": ["This field is required."],
                        },
                    ),
                ],
            ),
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        if User.objects.filter(email=email).exists():
            return Response({"error": "Користувач з таким email вже існує"}, status=400)

        import uuid
        import string
        import random

        username = str(uuid.uuid4())

        invite_code = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=8)
        )
        while User.objects.filter(invite_code=invite_code).exists():
            invite_code = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=8)
            )

        user = User.objects.create_user(
            username=username, email=email, password=password, invite_code=invite_code
        )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Логаут",
        description="Видаляє refresh токен поточного користувача (додає в blacklist)",
        request=LogoutRequestSerializer,
        responses={
            200: OpenApiResponse(
                description="Успішний вихід",
                response=LogoutResponseSerializer,
            ),
            400: OpenApiResponse(
                description="Невалідний токен, відсутній токен або користувач не авторизовані",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Missing Token",
                        value={"error": "Refresh токен обов'язковий"},
                    ),
                    OpenApiExample(
                        "Invalid Token / Error",
                        value={"error": "Невалідний токен або ви не авторизовані"},
                    ),
                ],
            ),
            401: OpenApiResponse(
                description="Користувач не авторизований",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Unauthorized",
                        value={
                            "detail": "Authentication credentials were not provided."
                        },
                    )
                ],
            ),
        },
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"error": "Refresh токен обов'язковий"}, status=400)

            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Вихід успішний"}, status=200)
        except Exception:
            return Response(
                {"error": "Невалідний токен або ви не авторизовані"}, status=400
            )


# ---------------------------------------------------------------------
# ---------------------------------------------------------------------
# ---------------------------------------------------------------------


class TournamentListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Список турнірів",
        description="Отримання списку всіх турнірів. Можна фільтрувати за назвою або статусом.",
        parameters=[
            OpenApiParameter(
                name="name", description="Пошук по назві", required=False, type=str
            ),
            OpenApiParameter(
                name="status",
                description="Фільтр по статусу (напр. DR, RG)",
                required=False,
                type=str,
            ),
        ],
        responses={200: TournamentSerializer(many=True)},
    )
    def get(self, request):
        queryset = Tournament.objects.all()

        name = request.query_params.get("name")
        if name:
            queryset = queryset.filter(title__icontains=name)

        status_param = request.query_params.get("status")
        if status_param and status_param != "all":
            queryset = queryset.filter(status=status_param)

        serializer = TournamentSerializer(queryset, many=True)
        return Response(serializer.data)


class TournamentDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Деталі турніру",
        description="Отримання детальної інформації про конкретний турнір за ID.",
        responses={
            200: TournamentDetailSerializer,
            404: OpenApiResponse(
                description="Турнір не знайдено",
                response=dict,
                examples=[
                    OpenApiExample("Not Found", value={"error": "Турнір не найден"})
                ],
            ),
        },
    )
    def get(self, request, tournament_id):
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response(
                {"error": "Турнир не найден"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = TournamentDetailSerializer(tournament)
        return Response(serializer.data)


class TournamentTeamsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Команди турніру",
        description="Отримання списку команд цього турніру, якщо is_team_visible = True.",
        responses={
            200: TeamSerializer(many=True),
            403: OpenApiResponse(
                description="Перегляд команд заборонено (is_team_visible=False)"
            ),
            404: OpenApiResponse(description="Турнір не знайдено"),
        },
    )
    def get(self, request, tournament_id):
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response(
                {"error": "Турнір не знайдено"}, status=status.HTTP_404_NOT_FOUND
            )

        if not tournament.is_team_visible:
            return Response(
                {"error": "Перегляд команд заборонено"},
                status=status.HTTP_403_FORBIDDEN,
            )

        teams = Team.objects.filter(tournament=tournament)
        serializer = TeamSerializer(teams, many=True)
        return Response(serializer.data)


class TournamentLeaderboardView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Лідерборд турніру",
        description="Отримання відсортованого списку команд і їх оцінок з останнього завершеного раунду.",
        responses={
            200: LeaderboardItemSerializer(many=True),
            404: OpenApiResponse(description="Турнір не знайдено"),
        },
    )
    def get(self, request, tournament_id):
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response(
                {"error": "Турнір не знайдено"}, status=status.HTTP_404_NOT_FOUND
            )

        # Шукаємо останній завершений раунд турніру
        last_round = (
            Round.objects.filter(tournament=tournament, status=Round.Status.EVALUATED)
            .order_by("-orderIndex")
            .first()
        )

        if not last_round:
            return Response([], status=status.HTTP_200_OK)

        # Отримуємо сабміти раунду та рахуємо суму балів
        submissions = (
            Submission.objects.filter(round=last_round)
            .select_related("team")
            .annotate(
                total_score=Coalesce(
                    Sum("evaluation__criterionevaluation__score"), Value(0)
                )
            )
        )

        leaderboard_data = []
        for submission in submissions:
            leaderboard_data.append(
                {
                    "team_id": submission.team.id,
                    "team_name": submission.team.name,
                    "score": submission.total_score,
                }
            )

        # Сортування за зменшенням оцінки
        leaderboard_data.sort(key=lambda x: x["score"], reverse=True)

        serializer = LeaderboardItemSerializer(leaderboard_data, many=True)
        return Response(serializer.data)


# ----------------------ROUNDS----------------------


from .utils import check_and_update_round_deadlines, check_tournament_deadlines
from .permissions import IsTournamentCreator, IsTournamentJury, IsTournamentParticipant


class RoundListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Список раундів турніру",
        description="Повертає раунди турніру. Чернетки бачить тільки творець турніру.",
        parameters=[
            OpenApiParameter(
                name="status",
                description="Фільтр по статусу (напр. AC, EV)",
                required=False,
                type=str,
            )
        ],
        responses=RoundSerializer(many=True),
    )
    def get(self, request, tournament_id):
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        check_tournament_deadlines(tournament)

        rounds = Round.objects.filter(tournament=tournament)

        status_param = request.query_params.get("status")
        if status_param:
            rounds = rounds.filter(status=status_param)

        if tournament.creator != request.user:
            rounds = rounds.exclude(status=Round.Status.DRAFT)

        serializer = RoundSerializer(rounds, many=True)
        return Response(serializer.data)


class RoundDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Деталі раунду", responses=RoundSerializer)
    def get(self, request, tournament_id, round_id):
        try:
            round_obj = Round.objects.get(id=round_id, tournament_id=tournament_id)
        except Round.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        check_and_update_round_deadlines(round_obj)

        if (
            round_obj.status == Round.Status.DRAFT
            and round_obj.tournament.creator != request.user
        ):
            return Response(
                {"error": "Чернетки недоступні"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = RoundSerializer(round_obj)
        return Response(serializer.data)


class CriterionListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Список критеріїв раунду",
        responses=EvaluationCriterionSerializer(many=True),
    )
    def get(self, request, tournament_id, round_id):
        try:
            round_obj = Round.objects.get(id=round_id, tournament_id=tournament_id)
        except Round.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        criterions = EvaluationCriterion.objects.filter(round=round_obj)
        serializer = EvaluationCriterionSerializer(criterions, many=True)
        return Response(serializer.data)


class RequirementListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Список вимог раунду", responses=RoundRequirementSerializer(many=True)
    )
    def get(self, request, tournament_id, round_id):
        try:
            round_obj = Round.objects.get(id=round_id, tournament_id=tournament_id)
        except Round.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        requirements = RoundRequirement.objects.filter(round=round_obj)
        serializer = RoundRequirementSerializer(requirements, many=True)
        return Response(serializer.data)


class AttachmentListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Список матеріалів раунду",
        responses=RoundAttachmentSerializer(many=True),
    )
    def get(self, request, tournament_id, round_id):
        try:
            round_obj = Round.objects.get(id=round_id, tournament_id=tournament_id)
        except Round.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        attachments = RoundAttachment.objects.filter(round=round_obj)
        serializer = RoundAttachmentSerializer(attachments, many=True)
        return Response(serializer.data)


# ----------------------SUBMISSIONS----------------------

# ----------------------EVALUATIONS----------------------


class EvaluationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Деталі або створення оцінки", responses=EvaluationSerializer
    )
    def get(self, request, tournament_id, round_id, submission_id):
        is_jury = TournamentJury.objects.filter(
            tournament_id=tournament_id, user=request.user
        ).exists()
        is_creator = Tournament.objects.filter(
            id=tournament_id, creator=request.user
        ).exists()

        if not (is_jury or is_creator):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            sub = Submission.objects.get(id=submission_id, round_id=round_id)
        except Submission.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        evaluation = Evaluation.objects.filter(
            submission=sub, jury=request.user
        ).first()

        if not evaluation and is_jury:
            evaluation = Evaluation.objects.create(
                submission=sub, jury=request.user, status=Evaluation.Status.DRAFT
            )
            criterions = EvaluationCriterion.objects.filter(round=sub.round)
            for c in criterions:
                CriterionEvaluation.objects.create(
                    evaluation=evaluation, criterion=c, score=0, comment=""
                )

            reqs = RoundRequirement.objects.filter(round=sub.round)
            for r in reqs:
                RequirementEvaluation.objects.create(
                    evaluation=evaluation, requirement=r, is_satisfied=False, comment=""
                )

        if not evaluation:
            return Response(
                {"error": "Оцінка не знайдена."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = EvaluationSerializer(evaluation)
        return Response(serializer.data)

    @extend_schema(
        summary="Оновлення оцінки",
        request=EvaluationSerializer,
        responses=EvaluationSerializer,
    )
    def patch(self, request, tournament_id, round_id, submission_id):
        evaluation = Evaluation.objects.filter(
            submission_id=submission_id, jury=request.user
        ).first()
        if not evaluation:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if (
            evaluation.status == Evaluation.Status.SUBMITTED
            and request.data.get("status") != Evaluation.Status.DRAFT
        ):
            return Response(
                {"error": "Оцінка вже збережена. Скасуйте для редагування."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_status = request.data.get("status")
        if (
            new_status == Evaluation.Status.SUBMITTED
            and evaluation.status == Evaluation.Status.DRAFT
        ):
            evaluation.submitted_at = timezone.now()

        serializer = EvaluationSerializer(evaluation, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CriterionEvaluationDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CriterionEvaluationSerializer

    @extend_schema(
        summary="Оновлення балу за критерій",
        request=CriterionEvaluationSerializer,
        responses={200: CriterionEvaluationSerializer},
    )
    def patch(self, request, tournament_id, round_id, submission_id, crit_eval_id):
        try:
            ce = CriterionEvaluation.objects.get(
                id=crit_eval_id,
                evaluation__submission_id=submission_id,
                evaluation__jury=request.user,
            )
        except CriterionEvaluation.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if ce.evaluation.status == Evaluation.Status.SUBMITTED:
            return Response(
                {"error": "Робота вже оцінена і не є чернеткою."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CriterionEvaluationSerializer(ce, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RequirementEvaluationDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RequirementEvaluationSerializer

    @extend_schema(
        summary="Оновлення вимоги",
        request=RequirementEvaluationSerializer,
        responses={200: RequirementEvaluationSerializer},
    )
    def patch(self, request, tournament_id, round_id, submission_id, req_eval_id):
        try:
            re = RequirementEvaluation.objects.get(
                id=req_eval_id,
                evaluation__submission_id=submission_id,
                evaluation__jury=request.user,
            )
        except RequirementEvaluation.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if re.evaluation.status == Evaluation.Status.SUBMITTED:
            return Response(
                {"error": "Робота вже оцінена."}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = RequirementEvaluationSerializer(
            re, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EvaluationCriterionListView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CriterionEvaluationSerializer

    @extend_schema(
        summary="Список оцінених критеріїв",
        responses={200: CriterionEvaluationSerializer(many=True)},
    )
    def get(self, request, tournament_id, round_id, submission_id):
        criterions = CriterionEvaluation.objects.filter(
            evaluation__submission_id=submission_id
        )
        if not Tournament.objects.filter(
            id=tournament_id, creator=request.user
        ).exists():
            criterions = criterions.filter(evaluation__jury=request.user)
        serializer = CriterionEvaluationSerializer(criterions, many=True)
        return Response(serializer.data)


class EvaluationRequirementListView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RequirementEvaluationSerializer

    @extend_schema(
        summary="Список перевірених вимог",
        responses={200: RequirementEvaluationSerializer(many=True)},
    )
    def get(self, request, tournament_id, round_id, submission_id):
        reqs = RequirementEvaluation.objects.filter(
            evaluation__submission_id=submission_id
        )
        if not Tournament.objects.filter(
            id=tournament_id, creator=request.user
        ).exists():
            reqs = reqs.filter(evaluation__jury=request.user)
        serializer = RequirementEvaluationSerializer(reqs, many=True)
        return Response(serializer.data)


# ----------------------TEAMS----------------------


class TeamListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Список команд користувача",
        description="Повертає список всіх команд, до яких зараз входить користувач (окрім архівованих/дискваліфікованих).",
        responses={200: TeamSerializer(many=True)},
    )
    def get(self, request):
        teams = Team.objects.filter(teammember__user=request.user).exclude(
            status__in=[Team.Status.ARCHIVED, Team.Status.DISQUALIFIED]
        )
        serializer = TeamSerializer(teams, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Створення команди",
        description="Дозволяє створити нову команду. Поточний користувач автоматично стає капітаном цієї команди.",
        request=TeamSerializer,
        responses={
            201: TeamSerializer,
            400: OpenApiResponse(description="Помилка валідації"),
        },
    )
    def post(self, request):
        serializer = TeamSerializer(data=request.data)
        if serializer.is_valid():
            team = serializer.save(status=Team.Status.REGISTRATED)
            TeamMember.objects.create(team=team, user=request.user, is_captain=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TeamArchiveListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Архів команд користувача",
        description="Повертає список команд поточного користувача зі статусом ARCHIVED, або всі команди, де турнір вже завершився.",
        responses={200: TeamSerializer(many=True)},
    )
    def get(self, request):
        from django.db.models import Q

        teams = (
            Team.objects.filter(teammember__user=request.user)
            .filter(
                Q(status=Team.Status.ARCHIVED)
                | Q(tournament__status=Tournament.Status.FINISHED)
            )
            .distinct()
        )
        serializer = TeamSerializer(teams, many=True)
        return Response(serializer.data)


class TeamDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Деталі команди",
        description="Отримання загальної інформації про обрану команду за її ID.",
        responses={
            200: TeamSerializer,
            404: OpenApiResponse(description="Команда не знайдена"),
        },
    )
    def get(self, request, team_id):
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = TeamSerializer(team)
        return Response(serializer.data)


class TeamParticipantListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TeamMemberSerializer

    @extend_schema(
        summary="Переглянути учасників команди",
        description="Повертає список всіх поточних учасників команди за її ID.",
        responses={
            200: TeamMemberSerializer(many=True),
            404: OpenApiResponse(description="Команда не знайдена"),
        },
    )
    def get(self, request, team_id):
        members = TeamMember.objects.filter(team_id=team_id)
        serializer = TeamMemberSerializer(members, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Додати учасника (надіслати запрошення)",
        description="Створює сповіщення типу TEAM_INVITE для вказаного користувача. Користувач не додається в команду доки не прийме запрошення.",
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="ID користувача",
            )
        ],
        responses={
            201: OpenApiResponse(
                description="Запрошення надіслано успішно",
                response=dict,
                examples=[
                    OpenApiExample("Success", value={"status": "Запрошення надіслано."})
                ],
            ),
            400: OpenApiResponse(
                description="Не валідно (команда переповнена або реєстрація закрита)",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Error",
                        value={
                            "error": "Максимальна кількість учасників вже досягнута."
                        },
                    )
                ],
            ),
            403: OpenApiResponse(
                description="Не капітан",
                response=dict,
                examples=[
                    OpenApiExample("Forbidden", value={"error": "Ви не капітан."})
                ],
            ),
            404: OpenApiResponse(description="Користувач або команда не знайдена"),
        },
    )
    def post(self, request, team_id):
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        is_captain = TeamMember.objects.filter(
            team=team, user=request.user, is_captain=True
        ).exists()
        if not is_captain:
            return Response(
                {"error": "Ви не капітан."}, status=status.HTTP_403_FORBIDDEN
            )

        check_tournament_deadlines(team.tournament)
        if team.tournament.status != Tournament.Status.REGISTRATION:
            return Response(
                {"error": "Реєстрація не йде."}, status=status.HTTP_400_BAD_REQUEST
            )

        if team.teammember_set.count() >= team.tournament.max_team_size:
            return Response(
                {"error": "Максимальна кількість учасників вже досягнута."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_user_id = request.data.get("user_id") or request.query_params.get(
            "user_id"
        )
        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Користувач не знайдений."}, status=status.HTTP_404_NOT_FOUND
            )

        from datetime import timedelta
        from django.utils import timezone

        from .models import Notification

        Notification.objects.create(
            user=target_user,
            title=f"Запрошення в команду {team.name}",
            message=f"Вас запросили в команду {team.name} на турнірі {team.tournament.title}.",
            type=Notification.Type.TEAM_INVITE,
            action_type=Notification.ActionType.YES_NO,
            action_url=f"/tournaments/{team.tournament.id}?team_id={team.id}",
            how_long_active=timezone.now() + timedelta(days=3),
        )
        return Response(
            {"status": "Запрошення надіслано."}, status=status.HTTP_201_CREATED
        )


class TeamParticipantDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Видалити/Покинути команду",
        description="Видаляє учасника з команди. Якщо передати user_id='me' - поточний юзер покидає команду. Капітан може передати new_captain_id.",
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="ID учасника або рядок 'me'",
            ),
        ],
        request=dict,
        responses={
            204: OpenApiResponse(
                description="Учасника успішно видалено / Команду покинуто"
            ),
            400: OpenApiResponse(
                description="Помилка бізнес логіки (наприклад, не передано ID нового капітана)",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Error",
                        value={"error": "Ви капітан. Передайте new_captain_id."},
                    )
                ],
            ),
            403: OpenApiResponse(
                description="Недостатньо прав",
                response=dict,
                examples=[
                    OpenApiExample("Forbidden", value={"error": "Ви не капітан."})
                ],
            ),
            404: OpenApiResponse(description="Команду або учасника не знайдено"),
        },
    )
    def delete(self, request, team_id, user_id):
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        check_tournament_deadlines(team.tournament)
        reg_finished = team.tournament.status != Tournament.Status.REGISTRATION

        try:
            target_id = request.user.id if user_id == "me" else int(user_id)
            target_member = TeamMember.objects.get(team=team, user_id=target_id)
            initiator_member = TeamMember.objects.get(team=team, user=request.user)
        except TeamMember.DoesNotExist:
            return Response(
                {"error": "Учасник не знайдений в цій команді."},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_self_delete = target_member == initiator_member

        if reg_finished:
            current_count = team.teammember_set.count()
            if current_count <= team.tournament.min_team_size:
                if current_count == 1:
                    team.delete()
                    return Response(
                        {"status": "Команду видалено."},
                        status=status.HTTP_204_NO_CONTENT,
                    )
                else:
                    return Response(
                        {
                            "error": "Неможливо видалити, реєстрація завершена і досягнуто мінімум учасників."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        if is_self_delete:
            if initiator_member.is_captain:
                if team.teammember_set.count() > 1:
                    new_captain_id = request.data.get("new_captain_id")
                    if not new_captain_id:
                        return Response(
                            {"error": "Ви капітан. Передайте new_captain_id."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    try:
                        new_cap = TeamMember.objects.get(
                            team=team, user_id=new_captain_id
                        )
                        new_cap.is_captain = True
                        new_cap.save()
                    except TeamMember.DoesNotExist:
                        return Response(
                            {"error": "Новий капітан не знайдений у команді."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                target_member.delete()
                if team.teammember_set.count() == 0:
                    team.delete()
            else:
                target_member.delete()
        else:
            if not initiator_member.is_captain:
                return Response(
                    {"error": "Ви не капітан."}, status=status.HTTP_403_FORBIDDEN
                )
            if target_member.is_captain:
                return Response(
                    {"error": "Неможливо видалити капітана."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            target_member.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class TeamCanCreateParticipantView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Чи можна додати учасника",
        description="Перевіряє, чи поточний користувач є капітаном, чи відкрита реєстрація турніру та чи не досягнуто ліміт на розмір команди.",
        responses={
            200: OpenApiResponse(
                description="Логічне значення (True/False)", response=bool
            )
        },
    )
    def get(self, request, team_id):
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        is_captain = TeamMember.objects.filter(
            team=team, user=request.user, is_captain=True
        ).exists()
        can_add = (
            is_captain
            and team.tournament.status == Tournament.Status.REGISTRATION
            and team.teammember_set.count() < team.tournament.max_team_size
        )
        return Response(can_add)


# ----------------------TEAM SUBMISSIONS----------------------


class TeamSubmitListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Список сабмітів команди",
        description="Отримує всі створені сабміти для вказаної команди.",
        responses={
            200: SubmissionSerializer(many=True),
            403: OpenApiResponse(description="Користувач не є учасником цієї команди"),
        },
    )
    def get(self, request, team_id):
        if not TeamMember.objects.filter(team_id=team_id, user=request.user).exists():
            return Response(status=status.HTTP_403_FORBIDDEN)
        submissions = Submission.objects.filter(team_id=team_id)
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Створення сабміту",
        description="Керує подачею рішення (сабмітом) на раунд. Тіло запиту повинно обов'язково містити round (ID раунду).",
        request=SubmissionSerializer,
        responses={
            201: SubmissionSerializer,
            400: OpenApiResponse(
                description="Помилка валідації, дедлайн пройшов, або сабміт вже існує",
                response=dict,
                examples=[
                    OpenApiExample("Error", value={"error": "Термін здачі пройшов."})
                ],
            ),
            403: OpenApiResponse(description="Користувач не є учасником цієї команди"),
            404: OpenApiResponse(description="Раунд не знайдено"),
        },
    )
    def post(self, request, team_id):
        if not TeamMember.objects.filter(team_id=team_id, user=request.user).exists():
            return Response(status=status.HTTP_403_FORBIDDEN)
        round_id = request.data.get("round")
        if not round_id:
            return Response(
                {"error": "Вкажіть round"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            round_obj = Round.objects.get(id=round_id, tournament__team__id=team_id)
        except Round.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if timezone.now() > round_obj.deadline:
            return Response(
                {"error": "Термін здачі пройшов."}, status=status.HTTP_400_BAD_REQUEST
            )

        if Submission.objects.filter(round_id=round_id, team_id=team_id).exists():
            return Response(
                {"error": "Сабміт вже створений."}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SubmissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                round=round_obj, team_id=team_id, status=Submission.Status.DRAFT
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TeamSubmitDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Редагування сабміту",
        description="Часткове оновлення інформації про сабміт. Можна відправити сабміт (status=SU) або повернути до чернетки (status=DR).",
        request=SubmissionSerializer,
        responses={
            200: SubmissionSerializer,
            400: OpenApiResponse(
                description="Дедлайн пройшов, або некоректна зміна статусу"
            ),
            403: OpenApiResponse(description="Користувач не учасник команди"),
            404: OpenApiResponse(description="Сабміт не знайдено"),
        },
    )
    def patch(self, request, team_id, submit_id):
        if not TeamMember.objects.filter(team_id=team_id, user=request.user).exists():
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            sub = Submission.objects.get(id=submit_id, team_id=team_id)
        except Submission.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        round_passed = timezone.now() > sub.round.deadline
        new_status = request.data.get("status")

        if round_passed:
            return Response(
                {"error": "Термін здачі пройшов."}, status=status.HTTP_400_BAD_REQUEST
            )

        if (
            sub.status == Submission.Status.SUBMITTED
            and new_status != Submission.Status.DRAFT
        ):
            return Response(
                {"error": "Сабміт відправлено. Скасуйте (status=DR), щоб редагувати."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubmissionSerializer(sub, data=request.data, partial=True)
        if serializer.is_valid():
            if (
                new_status == Submission.Status.SUBMITTED
                and sub.status == Submission.Status.DRAFT
            ):
                sub.submitted_at = timezone.now()
                serializer.save(submitted_at=timezone.now())
            else:
                serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ----------------------NOTIFICATIONS----------------------


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Список поточних сповіщень",
        description="Повертає список всіх актуальних сповіщень користувача. Може бути відфільтровано за статусом (наприклад, UR - Unread, RD - Read).",
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Кома-розділені статуси: UR, RD, AR",
            )
        ],
        responses={200: NotificationSerializer(many=True)},
    )
    def get(self, request):
        from .models import Notification

        status_param = request.query_params.get("status")
        nots = Notification.objects.filter(user=request.user)
        if status_param:
            statuses = status_param.split(",")
            nots = nots.filter(status__in=statuses)
        serializer = NotificationSerializer(nots, many=True)
        return Response(serializer.data)


class NotificationArchiveListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Архів сповіщень",
        description="Повертає всі сповіщення користувача, які мають статус ARCHIVED (AR).",
        responses={200: NotificationSerializer(many=True)},
    )
    def get(self, request):
        from .models import Notification

        nots = Notification.objects.filter(
            user=request.user, status=Notification.Status.ARCHIVED
        )
        serializer = NotificationSerializer(nots, many=True)
        return Response(serializer.data)


class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Дії зі сповіщеннями (read, archive, accept, reject)",
        description="Єдиний ендпоінт для взаємодії зі сповіщеннями через action: 'read', 'archive', 'accept', 'reject'. Якщо це TEAM_INVITE, 'accept' автоматично додасть учасника в команду.",
        request=dict,
        responses={
            200: OpenApiResponse(
                description="Успішно оновлено",
                response=dict,
                examples=[OpenApiExample("Success", value={"status": "AR"})],
            ),
            400: OpenApiResponse(
                description="Логічна помилка (запрошення минуло, команда повна, юзер вже в турнірі)",
                response=dict,
                examples=[
                    OpenApiExample("Error", value={"error": "Запрошення минуло."})
                ],
            ),
            404: OpenApiResponse(description="Сповіщення не знайдене"),
        },
    )
    def patch(self, request, notification_id):
        from django.utils import timezone
        from .models import Notification

        try:
            notif = Notification.objects.get(id=notification_id, user=request.user)
        except Notification.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action")
        if action == "read":
            notif.status = Notification.Status.READ
            notif.save(update_fields=["status"])
        elif action == "archive":
            notif.status = Notification.Status.ARCHIVED
            notif.save(update_fields=["status"])
        elif action == "accept" and notif.type == Notification.Type.TEAM_INVITE:
            if timezone.now() > notif.how_long_active:
                notif.status = Notification.Status.ARCHIVED
                notif.save(update_fields=["status"])
                return Response(
                    {"error": "Запрошення минуло."}, status=status.HTTP_400_BAD_REQUEST
                )

            import urllib.parse as urlparse

            parsed = urlparse.urlparse(notif.action_url)
            query = urlparse.parse_qs(parsed.query)
            team_id = query.get("team_id", [None])[0]

            if not team_id:
                return Response(
                    {"error": "Пошкоджене запрошення (немає team_id)"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                team = Team.objects.get(id=team_id)
            except Team.DoesNotExist:
                return Response(
                    {"error": "Команда не існує."}, status=status.HTTP_400_BAD_REQUEST
                )

            if team.teammember_set.count() >= team.tournament.max_team_size:
                return Response(
                    {"error": "Команда вже повна."}, status=status.HTTP_400_BAD_REQUEST
                )

            if team.tournament.status != Tournament.Status.REGISTRATION:
                return Response(
                    {"error": "Реєстрація закрита."}, status=status.HTTP_400_BAD_REQUEST
                )

            if (
                TeamMember.objects.filter(
                    team__tournament=team.tournament, user=request.user
                )
                .exclude(team__status=Team.Status.DISQUALIFIED)
                .exists()
            ):
                return Response(
                    {"error": "Ви вже є в цьому турнірі."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            TeamMember.objects.create(team=team, user=request.user)
            notif.status = Notification.Status.ARCHIVED
            notif.save(update_fields=["status"])
        elif action == "reject":
            notif.status = Notification.Status.ARCHIVED
            notif.save(update_fields=["status"])

        return Response({"status": getattr(notif, "status", None)})
