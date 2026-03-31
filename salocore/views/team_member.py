from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample,
    OpenApiParameter,
)
from django.utils import timezone
from datetime import timedelta
from ..models import Team, TeamMember, Tournament, User, Notification
from ..serializers import TeamMemberSerializer
from ..utils import check_tournament_deadlines


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
