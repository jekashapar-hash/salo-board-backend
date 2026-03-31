from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample,
    OpenApiParameter,
)
from ..models import Tournament, Team, Round, Submission
from ..serializers import (
    TournamentSerializer,
    TournamentDetailSerializer,
    TeamSerializer,
    LeaderboardItemSerializer,
)

# -------------------------- Tournament ------------------------------------


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
