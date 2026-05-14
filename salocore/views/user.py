import os

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Submission, TeamMember, Tournament, TournamentAdmin, TournamentJury, UserTelegramProfile
from ..serializers import (
    UserNameSerializer,
    UserProfileSerializer,
    UserRolesSerializer,
    UserSubmissionSerializer,
    UserTournamentHistoryItemSerializer,
)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Отримати профіль користувача",
        responses={200: UserProfileSerializer},
    )
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Частково оновити поточний профіль користувача",
        request=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(description="Помилка валідації"),
        },
    )
    def patch(self, request):
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.update(request.user, serializer.validated_data)
        # Return fresh representation
        out = UserProfileSerializer(request.user)
        return Response(out.data, status=status.HTTP_200_OK)


class UserNameView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Отримати ім'я та прізвище користувача",
        description="Повертає скорочену версію профілю: тільки ім'я та прізвище поточного користувача.",
        responses={
            200: UserNameSerializer,
            401: OpenApiResponse(description="Потрібна авторизація (JWT)"),
        },
        examples=[
            OpenApiExample(
                "Приклад відповіді",
                value={"firstName": "Іван", "lastName": "Богун"},
                response_only=True,
            )
        ],
        tags=["User"],
    )
    def get(self, request):
        serializer = UserNameSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserRolesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Ролі користувача",
        description="Повертає булеві значення для ролей (participant, jury, admin) стосовно АКТИВНИХ (Registration, Running) турнірів.",
        responses={200: UserRolesSerializer},
        tags=["User"],
    )
    def get(self, request):
        user = request.user

        is_admin = user.is_staff

        active_statuses = [Tournament.Status.REGISTRATION, Tournament.Status.RUNNING]

        is_jury = TournamentJury.objects.filter(user=user, tournament__status__in=active_statuses).exists()

        is_participant = TeamMember.objects.filter(user=user, team__tournament__status__in=active_statuses).exists()

        data = {"participant": is_participant, "jury": is_jury, "admin": is_admin}

        serializer = UserRolesSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserTournamentHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Історія участі у турнірах",
        description=(
            "Повертає список усіх турнірів, у яких поточний користувач брав участь "
            "як учасник (participant), журі (jury) або адміністратор (admin). "
            "Якщо в одному турнірі користувач мав кілька ролей — кожна роль "
            "повертається окремим записом."
        ),
        responses={200: UserTournamentHistoryItemSerializer(many=True)},
        tags=["User"],
    )
    def get(self, request):
        user = request.user
        history = []

        # ── учасник (через TeamMember) ─────────────────────────────────────
        member_qs = TeamMember.objects.filter(user=user).select_related("team", "team__tournament")
        for member in member_qs:
            t = member.team.tournament
            history.append(
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "start_date": t.start_date,
                    "ended_at": t.ended_at,
                    "role": "participant",
                    "team_id": member.team.id,
                    "team_name": member.team.name,
                }
            )

        # ── журі ───────────────────────────────────────────────────────────
        jury_qs = TournamentJury.objects.filter(user=user).select_related("tournament")
        for jury in jury_qs:
            t = jury.tournament
            history.append(
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "start_date": t.start_date,
                    "ended_at": t.ended_at,
                    "role": "jury",
                    "team_id": None,
                    "team_name": None,
                }
            )

        # ── адмін ──────────────────────────────────────────────────────────
        admin_qs = TournamentAdmin.objects.filter(user=user).select_related("tournament")
        for adm in admin_qs:
            t = adm.tournament
            history.append(
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "start_date": t.start_date,
                    "ended_at": t.ended_at,
                    "role": "admin",
                    "team_id": None,
                    "team_name": None,
                }
            )

        # Сортуємо: спочатку активні (Registration/Running), потім решта — за start_date desc
        history.sort(
            key=lambda x: (
                x["status"] not in (Tournament.Status.REGISTRATION, Tournament.Status.RUNNING),
                -(x["start_date"].timestamp() if x["start_date"] else 0),
            )
        )

        serializer = UserTournamentHistoryItemSerializer(history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserSubmissionsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Сабміти команд користувача",
        description=(
            "Повертає всі сабміти (чернетки та подані) команд, у яких поточний "
            "користувач є або був учасником. Кожен запис містить повний контекст: "
            "назву команди, раунд та турнір."
        ),
        responses={200: UserSubmissionSerializer(many=True)},
        tags=["User"],
    )
    def get(self, request):
        # ID команд, у яких є поточний юзер
        team_ids = TeamMember.objects.filter(user=request.user).values_list("team_id", flat=True)

        submissions = (
            Submission.objects.filter(team_id__in=team_ids)
            .select_related("team", "round", "round__tournament")
            .order_by("-created_at")
        )

        data = [
            {
                "id": s.id,
                "status": s.status,
                "github_url": s.github_url,
                "video_url": s.video_url,
                "demo_url": s.demo_url,
                "description": s.description,
                "created_at": s.created_at,
                "submitted_at": s.submitted_at,
                # команда
                "team_id": s.team.id,
                "team_name": s.team.name,
                # раунд
                "round_id": s.round.id,
                "round_title": s.round.title,
                "round_deadline": s.round.deadline,
                # турнір
                "tournament_id": s.round.tournament.id,
                "tournament_title": s.round.tournament.title,
                "tournament_status": s.round.tournament.status,
            }
            for s in submissions
        ]

        serializer = UserSubmissionSerializer(data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TelegramLinkView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Посилання для підключення Telegram",
        description=(
            "Повертає deep link на бота з параметром `start=<user_pk>`. "
            "Користувач переходить за посиланням, пише боту /start — "
            "бот автоматично зберігає його chat_id для розсилки сповіщень."
        ),
        responses={200: {"type": "object", "properties": {"link": {"type": "string"}}}},
        tags=["User"],
    )
    def get(self, request):
        bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "")
        link = f"https://t.me/{bot_username}?start={request.user.pk}"
        return Response({"link": link}, status=status.HTTP_200_OK)


class UserTelegramStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Статус підключення Telegram",
        description="Повертає булеве значення, чи підключив користувач Telegram-бота.",
        responses={200: {"type": "object", "properties": {"connected": {"type": "boolean"}}}},
        tags=["User"],
    )
    def get(self, request):
        connected = UserTelegramProfile.objects.filter(user=request.user).exists()
        return Response({"connected": connected}, status=status.HTTP_200_OK)
