from rest_framework import permissions

from .models import Team, TeamMember, Tournament, TournamentJury


class IsTournamentCreator(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        tournament_id = view.kwargs.get("tournament_id")
        if not tournament_id:
            return False

        try:
            tournament = Tournament.objects.get(id=tournament_id)
            return tournament.creator == request.user
        except Tournament.DoesNotExist:
            return False


class IsTournamentCreatorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow creator of a tournament to edit it.
    Assumes the model instance has an `creator` attribute.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        tournament_id = view.kwargs.get("tournament_id")
        if not tournament_id:
            return False

        try:
            tournament = Tournament.objects.get(id=tournament_id)
            return tournament.creator == request.user
        except Tournament.DoesNotExist:
            return False

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        tournament = obj if isinstance(obj, Tournament) else getattr(obj, "tournament", None)
        if tournament is None:
            return False
        return tournament.creator == request.user


class IsTournamentJury(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        tournament_id = view.kwargs.get("tournament_id")
        if not tournament_id:
            return False

        return TournamentJury.objects.filter(tournament_id=tournament_id, user=request.user).exists()


class IsTournamentParticipant(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        tournament_id = view.kwargs.get("tournament_id")
        if not tournament_id:
            return False

        return TeamMember.objects.filter(team__tournament_id=tournament_id, user=request.user).exists()


class IsTournamentParticipantNotDisqualified(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        tournament_id = view.kwargs.get("tournament_id")
        if not tournament_id:
            return False

        return (
            TeamMember.objects.filter(
                team__tournament_id=tournament_id,
                user=request.user,
            )
            .exclude(team__status=Team.Status.DISQUALIFIED)
            .exists()
        )
