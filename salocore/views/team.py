from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.db.models import Q
from ..models import Team, TeamMember, Tournament
from ..serializers import TeamSerializer

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
