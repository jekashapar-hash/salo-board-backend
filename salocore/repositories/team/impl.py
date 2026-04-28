from salocore.models import Team


class TeamRepositoryImpl:
    def disqualify_team(self, team_id: int) -> None:
        team = Team.objects.get(id=team_id)
        team.status = Team.Status.DISQUALIFIED
        team.save()

    def get_teams_without_submission_for_round(self, round_id: int) -> list[Team]:
        from salocore.models.round import Round

        round_instance = Round.objects.get(id=round_id)
        return list(Team.objects.filter(tournament=round_instance.tournament).exclude(submission__round=round_instance))
