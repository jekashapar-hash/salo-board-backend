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

from ..models import Round, Submission, Team, Tournament, TournamentAdmin, TournamentJury
from ..serializers import (
    LeaderboardItemSerializer,
    LeaderboardTeamRoundSerializer,
    TeamSerializer,
    TournamentAdminSerializer,
    TournamentDetailSerializer,
    TournamentJurySerializer,
    TournamentSerializer,
)


def get_tournament_leaderboard_data(tournament):
    """
    Calculates the leaderboard data for a given tournament.
    Returns a sorted list of team stats.
    """
    evaluated_rounds = (
        Round.objects.filter(tournament=tournament, status=Round.Status.EVALUATED)
        .prefetch_related("evaluationcriterion_set")
        .order_by("orderIndex")
    )

    teams = Team.objects.filter(
        tournament=tournament,
    ).exclude(status__in=[Team.Status.DISQUALIFIED, Team.Status.ARCHIVED])

    eval_round_ids = [r.id for r in evaluated_rounds]

    submissions = Submission.objects.filter(round_id__in=eval_round_ids, team__in=teams).prefetch_related(
        "evaluation_set",
        "evaluation_set__criterionevaluation_set",
        "evaluation_set__criterionevaluation_set__criterion",
    )

    team_stats = {}
    for team in teams:
        team_stats[team.id] = {"team_id": team.id, "team_name": team.name, "total_score": 0.0, "rounds": []}
        for round_obj in evaluated_rounds:
            max_score = sum(c.max_score * c.weight for c in round_obj.evaluationcriterion_set.all())
            team_stats[team.id]["rounds"].append(
                {
                    "round_id": round_obj.id,
                    "round_title": round_obj.title,
                    "teamRoundScore": 0.0,
                    "roundMaxScore": max_score,
                }
            )

    for sub in submissions:
        t_id = sub.team_id
        r_id = sub.round_id

        if t_id not in team_stats:
            continue

        r_data = next((r for r in team_stats[t_id]["rounds"] if r["round_id"] == r_id), None)
        if not r_data:
            continue

        crit_evals = {}
        for eval_obj in sub.evaluation_set.all():
            if eval_obj.status == "SB":
                for ce in eval_obj.criterionevaluation_set.all():
                    crit = ce.criterion
                    if crit.id not in crit_evals:
                        crit_evals[crit.id] = {"weight": crit.weight, "scores": []}
                    crit_evals[crit.id]["scores"].append(ce.score)

        for _c_id, c_data in crit_evals.items():
            if not c_data["scores"]:
                continue

            avg_score = sum(c_data["scores"]) / len(c_data["scores"])
            final_score = avg_score * c_data["weight"]
            r_data["teamRoundScore"] += final_score

        r_data["teamRoundScore"] = round(r_data["teamRoundScore"], 2)
        team_stats[t_id]["total_score"] += r_data["teamRoundScore"]
        team_stats[t_id]["total_score"] = round(team_stats[t_id]["total_score"], 2)

    leaderboard_data = list(team_stats.values())
    leaderboard_data.sort(key=lambda x: x["total_score"], reverse=True)
    return leaderboard_data


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

        leaderboard_data = get_tournament_leaderboard_data(tournament)
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

        evaluated_rounds = Round.objects.filter(tournament=tournament, status=Round.Status.EVALUATED).order_by(
            "orderIndex"
        )

        try:
            team = Team.objects.get(id=team_id, tournament=tournament)
        except Team.DoesNotExist:
            return Response({"error": "Команду не знайдено"}, status=status.HTTP_404_NOT_FOUND)

        eval_round_ids = [r.id for r in evaluated_rounds]

        submissions = Submission.objects.filter(round_id__in=eval_round_ids, team=team).prefetch_related(
            "evaluation_set",
            "evaluation_set__criterionevaluation_set",
            "evaluation_set__criterionevaluation_set__criterion",
        )

        rounds_data = []
        for round_obj in evaluated_rounds:
            rounds_data.append({"round_id": round_obj.id, "round_title": round_obj.title, "criterions": []})

        for sub in submissions:
            r_id = sub.round_id
            r_data = next((r for r in rounds_data if r["round_id"] == r_id), None)
            if not r_data:
                continue

            crit_evals = {}
            for eval_obj in sub.evaluation_set.all():
                if eval_obj.status == "SB":
                    for ce in eval_obj.criterionevaluation_set.all():
                        crit = ce.criterion
                        if crit.id not in crit_evals:
                            crit_evals[crit.id] = {
                                "criterion_id": crit.id,
                                "category": crit.category,
                                "title": crit.title,
                                "weight": crit.weight,
                                "max_score": crit.max_score,
                                "scores": [],
                            }
                        crit_evals[crit.id]["scores"].append(ce.score)

            for c_id, c_data in crit_evals.items():
                if not c_data["scores"]:
                    continue

                avg_score = sum(c_data["scores"]) / len(c_data["scores"])
                final_score = avg_score * c_data["weight"]

                r_data["criterions"].append(
                    {
                        "criterion_id": c_id,
                        "category": c_data["category"],
                        "title": c_data["title"],
                        "score": round(final_score, 2),
                        "max_score": c_data["max_score"],
                        "weight": c_data["weight"],
                    }
                )

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

        leaderboard_data = get_tournament_leaderboard_data(tournament)

        team_rank = None
        for index, item in enumerate(leaderboard_data):
            if item["team_id"] == team_id:
                team_rank = index + 1
                break

        if team_rank is None:
            return Response({"error": "Команду не знайдено в лідерборді"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"rank": team_rank, "total_teams": len(leaderboard_data)})
