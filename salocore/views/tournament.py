from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Team, Tournament, TournamentAdmin, TournamentJury
from ..serializers import (
    LeaderboardItemSerializer,
    LeaderboardTeamRoundSerializer,
    TeamSerializer,
    TournamentAdminSerializer,
    TournamentDetailSerializer,
    TournamentJurySerializer,
    TournamentSerializer,
)
from ..use_cases.leaderboard.deps import get_leaderboard_use_case


class TournamentListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Список турнірів",
        description="Отримання списку всіх турнірів. Можна фільтрувати за назвою або статусом.",
        parameters=[
            OpenApiParameter(name="name", description="Пошук по назві", required=False, type=str),
            OpenApiParameter(
                name="status",
                description="Фільтр по статусу (напр. DR, RG)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="role",
                description="Фільтр по ролі (participant, jury, admin, all)",
                required=False,
                type=str,
            ),
        ],
        responses={200: TournamentSerializer(many=True)},
    )
    def get(self, request):
        queryset = Tournament.objects.exclude(status=Tournament.Status.ARCHIVED)

        name = request.query_params.get("name")
        if name:
            queryset = queryset.filter(title__icontains=name)

        status_param = request.query_params.get("status")
        if status_param and status_param != "all":
            queryset = queryset.filter(status=status_param)

        role = request.query_params.get("role")
        if role and role != "all":
            if not request.user.is_authenticated:
                queryset = queryset.none()
            elif role == "participant":
                queryset = queryset.filter(team__teammember__user=request.user).distinct()
            elif role == "jury":
                queryset = queryset.filter(tournamentjury__user=request.user).distinct()
            elif role == "admin":
                queryset = queryset.filter(tournamentadmin__user=request.user).distinct()

        serializer = TournamentSerializer(queryset, many=True)
        return Response(serializer.data)


class ArchivedTournamentListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Список архівних турнірів",
        description="Отримання списку всіх архівних турнірів. Можна фільтрувати за назвою та роллю.",
        parameters=[
            OpenApiParameter(name="name", description="Пошук по назві", required=False, type=str),
            OpenApiParameter(
                name="role",
                description="Фільтр по ролі (participant, jury, admin, all)",
                required=False,
                type=str,
            ),
        ],
        responses={200: TournamentSerializer(many=True)},
    )
    def get(self, request):
        queryset = Tournament.objects.filter(status=Tournament.Status.ARCHIVED)

        name = request.query_params.get("name")
        if name:
            queryset = queryset.filter(title__icontains=name)

        role = request.query_params.get("role")
        if role and role != "all":
            if not request.user.is_authenticated:
                queryset = queryset.none()
            elif role == "participant":
                queryset = queryset.filter(team__teammember__user=request.user).distinct()
            elif role == "jury":
                queryset = queryset.filter(tournamentjury__user=request.user).distinct()
            elif role == "admin":
                queryset = queryset.filter(tournamentadmin__user=request.user).distinct()

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
                examples=[OpenApiExample("Not Found", value={"error": "Турнір не найден"})],
            ),
        },
    )
    def get(self, request, tournament_id):
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response({"error": "Турнір не знайдено"}, status=status.HTTP_404_NOT_FOUND)

        serializer = TournamentDetailSerializer(tournament)
        return Response(serializer.data)


class TournamentTeamsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Команди турніру",
        description="Отримання списку команд цього турніру, якщо is_team_visible = True.",
        responses={
            200: TeamSerializer(many=True),
            403: OpenApiResponse(description="Перегляд команд заборонено (is_team_visible=False)"),
            404: OpenApiResponse(description="Турнір не знайдено"),
        },
    )
    def get(self, request, tournament_id):
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response({"error": "Турнір не знайдено"}, status=status.HTTP_404_NOT_FOUND)

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
        description="Отримання відсортованого списку команд і їх агрегованих балів за раундами.",
        responses={200: LeaderboardItemSerializer(many=True)},
        operation_id="tournament_leaderboard_list",
    )
    def get(self, request, tournament_id):
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response({"error": "Турнір не знайдено"}, status=status.HTTP_404_NOT_FOUND)

        if not tournament.is_team_visible:
            return Response(
                {"error": "Перегляд команд заборонено"},
                status=status.HTTP_403_FORBIDDEN,
            )

        use_case = get_leaderboard_use_case()
        leaderboard_data = use_case.get_leaderboard(tournament)
        serializer = LeaderboardItemSerializer(leaderboard_data, many=True)
        return Response(serializer.data)


class TournamentJuryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Журі турніру",
        description="Отримання списку журі для вказаного турніру.",
        responses={
            200: TournamentJurySerializer(many=True),
            404: OpenApiResponse(
                description="Турнір не знайдено",
                response=dict,
                examples=[OpenApiExample("Not Found", value={"error": "Турнір не знайдено"})],
            ),
        },
    )
    def get(self, request, tournament_id):
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response({"error": "Турнір не знайдено"}, status=status.HTTP_404_NOT_FOUND)

        jury_members = TournamentJury.objects.filter(tournament=tournament)
        serializer = TournamentJurySerializer(jury_members, many=True)
        return Response(serializer.data)


class TournamentAdminView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Адміністратори турніру",
        description="Отримання списку адміністраторів для вказаного турніру.",
        responses={
            200: TournamentAdminSerializer(many=True),
            404: OpenApiResponse(
                description="Турнір не знайдено",
                response=dict,
                examples=[OpenApiExample("Not Found", value={"error": "Турнір не знайдено"})],
            ),
        },
    )
    def get(self, request, tournament_id):
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response({"error": "Турнір не знайдено"}, status=status.HTTP_404_NOT_FOUND)

        admins = TournamentAdmin.objects.filter(tournament=tournament)
        serializer = TournamentAdminSerializer(admins, many=True)
        return Response(serializer.data)


class TournamentTeamLeaderboardDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Деталі лідерборду команди",
        description="Отримання детальної інформації про бали команди за всі оцінені раунди.",
        responses={200: LeaderboardTeamRoundSerializer(many=True)},
        operation_id="tournament_team_leaderboard_detail",
    )
    def get(self, request, tournament_id, team_id):
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response({"error": "Турнір не знайдено"}, status=status.HTTP_404_NOT_FOUND)

        if not tournament.is_team_visible:
            return Response(
                {"error": "Перегляд команд заборонено"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            team = Team.objects.get(id=team_id, tournament=tournament)
        except Team.DoesNotExist:
            return Response({"error": "Команду не знайдено"}, status=status.HTTP_404_NOT_FOUND)

        use_case = get_leaderboard_use_case()
        rounds_data = use_case.get_team_round_details(tournament, team)
        serializer = LeaderboardTeamRoundSerializer(rounds_data, many=True)
        return Response(serializer.data)


class TournamentTeamRankView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Місце команди в лідерборді",
        description="Отримання поточного місця конкретної команди в загальному заліку турніру.",
        responses={
            200: OpenApiResponse(
                description="Ранг команди",
                response=dict,
                examples=[OpenApiExample("Rank Info", value={"rank": 1, "total_teams": 10})],
            ),
            404: OpenApiResponse(description="Турнір або команду не знайдено"),
        },
        operation_id="tournament_team_rank",
    )
    def get(self, request, tournament_id, team_id):
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response({"error": "Турнір не знайдено"}, status=status.HTTP_404_NOT_FOUND)

        if not tournament.is_team_visible:
            return Response(
                {"error": "Перегляд команд заборонено"},
                status=status.HTTP_403_FORBIDDEN,
            )

        use_case = get_leaderboard_use_case()
        leaderboard_data = use_case.get_leaderboard(tournament)

        team_rank = None
        for index, item in enumerate(leaderboard_data):
            if item["team_id"] == team_id:
                team_rank = index + 1
                break

        if team_rank is None:
            return Response({"error": "Команду не знайдено в лідерборді"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"rank": team_rank, "total_teams": len(leaderboard_data)})
