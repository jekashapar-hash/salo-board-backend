from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from ..models import Team, TeamMember
from ..serializers import TeamSerializer, TeamMemberSerializer


class AdminTeamListView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Команди турніру (Адмін)",
        description="Отримання списку всіх команд турніру. Доступно для адміністраторів.",
        responses={200: TeamSerializer(many=True)},
    )
    def get(self, request, tournament_id):
        teams = Team.objects.filter(tournament_id=tournament_id)
        serializer = TeamSerializer(teams, many=True)
        return Response(serializer.data)


class AdminTeamDisqualifyView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Дискваліфікувати команду (Адмін)",
        description="Зміна статусу команди на DISQUALIFIED. Доступно для адміністраторів.",
        request=None,
        responses={200: TeamSerializer},
    )
    def patch(self, request, tournament_id, team_id):
        team = get_object_or_404(Team, id=team_id, tournament_id=tournament_id)

        team.status = Team.Status.DISQUALIFIED
        team.save()

        serializer = TeamSerializer(team)
        return Response(serializer.data)


class AdminParticipantListView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Список учасників команди (Адмін)",
        description="Отримання списку учасників команди.",
        responses={200: TeamMemberSerializer(many=True)},
    )
    def get(self, request, tournament_id, team_id):
        members = TeamMember.objects.filter(
            team_id=team_id,
            team__tournament_id=tournament_id
        )
        serializer = TeamMemberSerializer(members, many=True)
        return Response(serializer.data)


class AdminParticipantDetailView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Передати статус командира (Адмін)",
        description="Встановлює вказаного учасника командиром команди.",
        request=None,
        responses={200: TeamMemberSerializer},
    )
    def patch(self, request, tournament_id, team_id, user_id):
        member = get_object_or_404(
            TeamMember,
            team_id=team_id,
            team__tournament_id=tournament_id,
            user_id=user_id,
        )

        TeamMember.objects.filter(team=member.team, is_captain=True).update(is_captain=False)

        member.is_captain = True
        member.save()

        serializer = TeamMemberSerializer(member)
        return Response(serializer.data)

    @extend_schema(
        summary="Видалити учасника (Адмін)",
        description="Видалення учасника з команди.",
        responses={204: None},
    )
    def delete(self, request, tournament_id, team_id, user_id):
        member = get_object_or_404(
            TeamMember,
            team_id=team_id,
            team__tournament_id=tournament_id,
            user_id=user_id,
        )

        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
