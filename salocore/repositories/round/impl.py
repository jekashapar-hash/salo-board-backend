from salocore.models.round import Round


class RoundRepositoryImpl:
    def get_by_status(self, status: Round.Status) -> list[Round]:
        return Round.objects.filter(status=status)

    def update_status(self, round_id: int, status: str) -> None:
        round = Round.objects.get(id=round_id)
        round.status = status
        round.save()
