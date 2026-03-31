from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from ..models import Evaluation
from ..serializers import EvaluationSerializer


class AdminEvaluationListView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Список оцінок (Адмін)",
        description="Отримання списку оцінок журі для раунду.",
        responses={200: EvaluationSerializer(many=True)},
    )
    def get(self, request, tournament_id, round_id):
        evaluations = Evaluation.objects.filter(
            submission__round_id=round_id,
            submission__round__tournament_id=tournament_id,
        ).order_by("submission__team__name")

        serializer = EvaluationSerializer(evaluations, many=True)
        return Response(serializer.data)


class AdminEvaluationDetailView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Деталі оцінки (Адмін)",
        description="Отримання детальної інформації про конкретну оцінку від члена журі.",
        responses={200: EvaluationSerializer},
    )
    def get(self, request, tournament_id, round_id, evaluation_id):
        evaluation = get_object_or_404(
            Evaluation,
            id=evaluation_id,
            submission__round_id=round_id,
            submission__round__tournament_id=tournament_id,
        )

        serializer = EvaluationSerializer(evaluation)
        return Response(serializer.data)
