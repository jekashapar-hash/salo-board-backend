from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from ..models import (
    Tournament,
    Round,
    EvaluationCriterion,
    RoundRequirement,
    RoundAttachment,
)
from ..serializers import (
    RoundSerializer,
    EvaluationCriterionSerializer,
    RoundRequirementSerializer,
    RoundAttachmentSerializer,
)
from ..utils import check_and_update_round_deadlines, check_tournament_deadlines


class RoundListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Список раундів турніру",
        description="Повертає раунди турніру. Чернетки бачить тільки творець турніру.",
        parameters=[
            OpenApiParameter(
                name="status",
                description="Фільтр по статусу (напр. AC, EV)",
                required=False,
                type=str,
            )
        ],
        responses=RoundSerializer(many=True),
    )
    def get(self, request, tournament_id):
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        check_tournament_deadlines(tournament)

        rounds = Round.objects.filter(tournament=tournament)

        status_param = request.query_params.get("status")
        if status_param:
            rounds = rounds.filter(status=status_param)

        if tournament.creator != request.user:
            rounds = rounds.exclude(status=Round.Status.DRAFT)

        serializer = RoundSerializer(rounds, many=True)
        return Response(serializer.data)


class RoundDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Деталі раунду", responses=RoundSerializer)
    def get(self, request, tournament_id, round_id):
        try:
            round_obj = Round.objects.get(id=round_id, tournament_id=tournament_id)
        except Round.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        check_and_update_round_deadlines(round_obj)

        if (
            round_obj.status == Round.Status.DRAFT
            and round_obj.tournament.creator != request.user
        ):
            return Response(
                {"error": "Чернетки недоступні"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = RoundSerializer(round_obj)
        return Response(serializer.data)


class CriterionListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Список критеріїв раунду",
        responses=EvaluationCriterionSerializer(many=True),
    )
    def get(self, request, tournament_id, round_id):
        try:
            round_obj = Round.objects.get(id=round_id, tournament_id=tournament_id)
        except Round.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        criterions = EvaluationCriterion.objects.filter(round=round_obj)
        serializer = EvaluationCriterionSerializer(criterions, many=True)
        return Response(serializer.data)


class RequirementListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Список вимог раунду", responses=RoundRequirementSerializer(many=True)
    )
    def get(self, request, tournament_id, round_id):
        try:
            round_obj = Round.objects.get(id=round_id, tournament_id=tournament_id)
        except Round.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        requirements = RoundRequirement.objects.filter(round=round_obj)
        serializer = RoundRequirementSerializer(requirements, many=True)
        return Response(serializer.data)


class AttachmentListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Список матеріалів раунду",
        responses=RoundAttachmentSerializer(many=True),
    )
    def get(self, request, tournament_id, round_id):
        try:
            round_obj = Round.objects.get(id=round_id, tournament_id=tournament_id)
        except Round.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        attachments = RoundAttachment.objects.filter(round=round_obj)
        serializer = RoundAttachmentSerializer(attachments, many=True)
        return Response(serializer.data)
