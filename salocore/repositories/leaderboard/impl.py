from salocore.models import Round, Submission, Team


class LeaderboardRepositoryImpl:
    def get_evaluated_rounds(self, tournament) -> list[Round]:
        return list(
            Round.objects.filter(tournament=tournament, status=Round.Status.EVALUATED)
            .prefetch_related("evaluationcriterion_set")
            .order_by("orderIndex")
        )

    def get_active_teams(self, tournament) -> list[Team]:
        return list(
            Team.objects.filter(tournament=tournament).exclude(
                status__in=[Team.Status.DISQUALIFIED, Team.Status.ARCHIVED]
            )
        )

    def get_submissions_for_rounds(self, round_ids: list[int], teams: list[Team]) -> list[Submission]:
        return list(
            Submission.objects.filter(round_id__in=round_ids, team__in=teams).prefetch_related(
                "evaluation_set",
                "evaluation_set__criterionevaluation_set",
                "evaluation_set__criterionevaluation_set__criterion",
            )
        )

    def get_team_submissions_for_rounds(self, round_ids: list[int], team: Team) -> list[Submission]:
        return list(
            Submission.objects.filter(round_id__in=round_ids, team=team).prefetch_related(
                "evaluation_set",
                "evaluation_set__criterionevaluation_set",
                "evaluation_set__criterionevaluation_set__criterion",
            )
        )
