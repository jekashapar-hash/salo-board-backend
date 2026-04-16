from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Round, Submission, Team, Tournament
from ..serializers import (
    LeaderboardItemSerializer,
    TeamSerializer,
    TournamentDetailSerializer,
    TournamentSerializer,
)


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
                examples=[OpenApiExample("Not Found", value={"error": "Турнір не найден"})],
            ),
        },
    )
    def get(self, request, tournament_id):
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response({"error": "Турнир не найден"}, status=status.HTTP_404_NOT_FOUND)

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
            return Response({"error": "Турнір не знайдено"}, status=status.HTTP_404_NOT_FOUND)

        evaluated_rounds = Round.objects.filter(tournament=tournament, status=Round.Status.EVALUATED).order_by(
            "orderIndex"
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
            # Ініціалізуємо раунди в правильному порядку
            for round_obj in evaluated_rounds:
                team_stats[team.id]["rounds"].append(
                    {"round_id": round_obj.id, "round_title": round_obj.title, "round_score": 0.0, "criterions": []}
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
                if eval_obj.status == "SB":  # Враховуємо тільки SUBMITTED оцінки
                    for ce in eval_obj.criterionevaluation_set.all():
                        crit = ce.criterion
                        if crit.id not in crit_evals:
                            crit_evals[crit.id] = {
                                "criterion_id": crit.id,
                                "category": crit.category,
                                "title": crit.title,
                                "weight": crit.weight,
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
                        "weight": c_data["weight"],
                        "raw_score": round(avg_score, 2),
                        "final_score": round(final_score, 2),
                    }
                )
                r_data["round_score"] += final_score

            team_stats[t_id]["total_score"] += r_data["round_score"]
            team_stats[t_id]["total_score"] = round(team_stats[t_id]["total_score"], 2)

        leaderboard_data = list(team_stats.values())
        leaderboard_data.sort(key=lambda x: x["total_score"], reverse=True)

        serializer = LeaderboardItemSerializer(leaderboard_data, many=True)
        return Response(serializer.data)
