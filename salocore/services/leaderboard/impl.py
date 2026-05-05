from salocore.repositories.leaderboard.protocol import LeaderboardRepositoryProtocol


class LeaderboardService:
    def __init__(self, leaderboard_repository: LeaderboardRepositoryProtocol) -> None:
        self._repo = leaderboard_repository

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_leaderboard(self, tournament) -> list[dict]:
        """
        Calculates the leaderboard data for a given tournament.
        Returns a sorted list of team stats.
        """
        evaluated_rounds = self._repo.get_evaluated_rounds(tournament)
        teams = self._repo.get_active_teams(tournament)
        eval_round_ids = [r.id for r in evaluated_rounds]
        submissions = self._repo.get_submissions_for_rounds(eval_round_ids, teams)

        team_stats: dict[int, dict] = {}
        for team in teams:
            team_stats[team.id] = {
                "team_id": team.id,
                "team_name": team.name,
                "total_score": 0.0,
                "rounds": [],
            }
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

            crit_evals = self._aggregate_criterion_scores(sub)

            for _c_id, c_data in crit_evals.items():
                if not c_data["scores"]:
                    continue
                avg_score = sum(c_data["scores"]) / len(c_data["scores"])
                r_data["teamRoundScore"] += avg_score * c_data["weight"]

            r_data["teamRoundScore"] = round(r_data["teamRoundScore"], 2)
            team_stats[t_id]["total_score"] += r_data["teamRoundScore"]
            team_stats[t_id]["total_score"] = round(team_stats[t_id]["total_score"], 2)

        leaderboard_data = list(team_stats.values())
        leaderboard_data.sort(key=lambda x: x["total_score"], reverse=True)
        return leaderboard_data

    def get_team_round_details(self, tournament, team) -> list[dict]:
        """
        Returns per-round criterion breakdown for a single team.
        """
        evaluated_rounds = self._repo.get_evaluated_rounds(tournament)
        eval_round_ids = [r.id for r in evaluated_rounds]
        submissions = self._repo.get_team_submissions_for_rounds(eval_round_ids, team)

        rounds_data: list[dict] = [
            {"round_id": r.id, "round_title": r.title, "criterions": []} for r in evaluated_rounds
        ]

        for sub in submissions:
            r_id = sub.round_id
            r_data = next((r for r in rounds_data if r["round_id"] == r_id), None)
            if not r_data:
                continue

            crit_evals = self._aggregate_criterion_scores_detailed(sub)

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

        return rounds_data

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _aggregate_criterion_scores(sub) -> dict:
        """Collects weight+scores per criterion for leaderboard calculation."""
        crit_evals: dict = {}
        for eval_obj in sub.evaluation_set.all():
            if eval_obj.status == "SB":
                for ce in eval_obj.criterionevaluation_set.all():
                    crit = ce.criterion
                    if crit.id not in crit_evals:
                        crit_evals[crit.id] = {"weight": crit.weight, "scores": []}
                    crit_evals[crit.id]["scores"].append(ce.score)
        return crit_evals

    @staticmethod
    def _aggregate_criterion_scores_detailed(sub) -> dict:
        """Collects full criterion info + scores for team detail view."""
        crit_evals: dict = {}
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
        return crit_evals
