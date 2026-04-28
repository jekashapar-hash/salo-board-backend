from salocore.models.tournament import Tournament


class TournamentRepositoryImpl:
    def get_by_status(self, status: Tournament.Status) -> list[Tournament]:
        return Tournament.objects.filter(status=status)

    def update_status(self, tournament_id: int, status: str) -> None:
        tournament = Tournament.objects.get(id=tournament_id)
        tournament.status = status
        tournament.save()
