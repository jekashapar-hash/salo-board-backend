from django.db.models import Q
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Team, TeamMember, Tournament
from ..serializers import TeamSerializer


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
            tournament = serializer.validated_data["tournament"]
            name = serializer.validated_data["name"]

            if Team.objects.filter(tournament=tournament, name=name).exists():
                return Response(
                    {"detail": f"Команда з назвою '{name}' вже існує в цьому турнірі."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if tournament.status != Tournament.Status.REGISTRATION:
                return Response(
                    {"detail": "Реєстрація команд в цей турнір зараз закрита."}, status=status.HTTP_400_BAD_REQUEST
                )
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
        teams = (
            Team.objects.filter(teammember__user=request.user)
            .filter(Q(status=Team.Status.ARCHIVED) | Q(tournament__status=Tournament.Status.FINISHED))
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

        if not team.tournament.is_team_visible:
            is_member = TeamMember.objects.filter(team=team, user=request.user).exists()
            if not is_member:
                return Response(
                    {"error": "Перегляд команди заборонено"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = TeamSerializer(team)
        return Response(serializer.data)
