from rest_framework import permissions
from .models import Tournament, TournamentJury, TeamMember, Team

class IsTournamentCreator(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        tournament_id = view.kwargs.get('tournament_id')
        if not tournament_id:
            return False
            
        try:
            tournament = Tournament.objects.get(id=tournament_id)
            return tournament.creator == request.user
        except Tournament.DoesNotExist:
            return False

class IsTournamentJury(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        tournament_id = view.kwargs.get('tournament_id')
        if not tournament_id:
            return False
            
        return TournamentJury.objects.filter(tournament_id=tournament_id, user=request.user).exists()

class IsTournamentParticipant(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        tournament_id = view.kwargs.get('tournament_id')
        if not tournament_id:
            return False
            
        return TeamMember.objects.filter(team__tournament_id=tournament_id, user=request.user).exists()

class IsTournamentParticipantNotDisqualified(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        tournament_id = view.kwargs.get('tournament_id')
        if not tournament_id:
            return False
            
        return TeamMember.objects.filter(
            team__tournament_id=tournament_id, 
            user=request.user,
        ).exclude(team__status=Team.Status.DISQUALIFIED).exists()
