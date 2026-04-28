from salocore.models import TournamentJury, UserProfile


class UserRepositoryImpl:
    def get_profile(self, user_id: int) -> UserProfile:
        return UserProfile.objects.get(user_id=user_id)

    def get_tournament_participants(self, tournament_id: int) -> list[UserProfile]:
        return list(UserProfile.objects.filter(user__teammember__team__tournament_id=tournament_id).distinct())

    def get_juries_ids(self, tournament_id: int) -> list[int]:
        return list(
            TournamentJury.objects.filter(tournament_id=tournament_id).values_list("user_id", flat=True).distinct()
        )
