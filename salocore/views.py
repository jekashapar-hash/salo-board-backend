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


# --------------------------------------------------------------


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


class SubmissionListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Список сабмітів раунду", responses=SubmissionSerializer(many=True)
    )
    def get(self, request, tournament_id, round_id):
        try:
            round_obj = Round.objects.get(id=round_id, tournament_id=tournament_id)
        except Round.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        check_and_update_round_deadlines(round_obj)

        is_creator = round_obj.tournament.creator == request.user
        is_jury = TournamentJury.objects.filter(
            tournament_id=tournament_id, user=request.user
        ).exists()

        if is_creator or is_jury:
            submissions = Submission.objects.filter(round_id=round_id)
        else:
            submissions = Submission.objects.filter(
                round_id=round_id, team__teammember__user=request.user
            )

        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Створення сабміту",
        request=SubmissionSerializer,
        responses=SubmissionSerializer,
    )
    def post(self, request, tournament_id, round_id):
        is_participant = (
            TeamMember.objects.filter(
                team__tournament_id=tournament_id, user=request.user
            )
            .exclude(team__status=Team.Status.DISQUALIFIED)
            .first()
        )

        if not is_participant:
            return Response(
                {"error": "Ви не є учасником або команда дискваліфікована."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            round_obj = Round.objects.get(id=round_id, tournament_id=tournament_id)
        except Round.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if timezone.now() > round_obj.deadline:
            return Response(
                {"error": "Термін здачі пройшов."}, status=status.HTTP_400_BAD_REQUEST
            )

        if Submission.objects.filter(
            round_id=round_id, team=is_participant.team
        ).exists():
            return Response(
                {"error": "Сабміт вже створений."}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SubmissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                round=round_obj,
                team=is_participant.team,
                status=Submission.Status.DRAFT,
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubmissionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, round_id, submission_id, user):
        try:
            sub = Submission.objects.get(id=submission_id, round_id=round_id)
            if (
                sub.round.tournament.creator == user
                or TournamentJury.objects.filter(
                    tournament=sub.round.tournament, user=user
                ).exists()
            ):
                return sub
            if sub.team.teammember_set.filter(user=user).exists():
                return sub
            return None
        except Submission.DoesNotExist:
            return None

    @extend_schema(summary="Деталі сабміту", responses=SubmissionSerializer)
    def get(self, request, tournament_id, round_id, submission_id):
        sub = self.get_object(round_id, submission_id, request.user)
        if not sub:
            return Response(status=status.HTTP_404_NOT_FOUND)

        check_and_update_round_deadlines(sub.round)
        serializer = SubmissionSerializer(sub)
        return Response(serializer.data)

    @extend_schema(
        summary="Редагування сабміту",
        request=SubmissionSerializer,
        responses=SubmissionSerializer,
    )
    def patch(self, request, tournament_id, round_id, submission_id):
        sub = self.get_object(round_id, submission_id, request.user)
        if not sub:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not sub.team.teammember_set.filter(user=request.user).exists():
            return Response(
                {"error": "Лише учасники команди можуть редагувати сабміт."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if sub.team.status == Team.Status.DISQUALIFIED:
            return Response(
                {"error": "Команда дискваліфікована."}, status=status.HTTP_403_FORBIDDEN
            )

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

    @extend_schema(
        summary="Оновлення балу за критерій", request=CriterionEvaluationSerializer
    )
    def patch(self, request, tournament_id, round_id, eval_id, crit_eval_id):
        try:
            ce = CriterionEvaluation.objects.get(
                id=crit_eval_id, evaluation_id=eval_id, evaluation__jury=request.user
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

    @extend_schema(summary="Оновлення вимоги", request=RequirementEvaluationSerializer)
    def patch(self, request, tournament_id, round_id, eval_id, req_eval_id):
        try:
            re = RequirementEvaluation.objects.get(
                id=req_eval_id, evaluation_id=eval_id, evaluation__jury=request.user
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

    @extend_schema(summary="Список оцінених критеріїв")
    def get(self, request, tournament_id, round_id, eval_id):
        criterions = CriterionEvaluation.objects.filter(evaluation_id=eval_id)
        if not Tournament.objects.filter(
            id=tournament_id, creator=request.user
        ).exists():
            criterions = criterions.filter(evaluation__jury=request.user)
        serializer = CriterionEvaluationSerializer(criterions, many=True)
        return Response(serializer.data)


class EvaluationRequirementListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Список перевірених вимог")
    def get(self, request, tournament_id, round_id, eval_id):
        reqs = RequirementEvaluation.objects.filter(evaluation_id=eval_id)
        if not Tournament.objects.filter(
            id=tournament_id, creator=request.user
        ).exists():
            reqs = reqs.filter(evaluation__jury=request.user)
        serializer = RequirementEvaluationSerializer(reqs, many=True)
        return Response(serializer.data)
