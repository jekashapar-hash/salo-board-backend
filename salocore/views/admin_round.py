from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    extend_schema,
)
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import EvaluationCriterion, Round, RoundRequirement, Tournament
from ..permissions import IsTournamentCreator, IsTournamentCreatorOrReadOnly
from ..serializers import (
    EvaluationCriterionSerializer,
    RoundAttachmentSerializer,
    RoundRequirementSerializer,
    RoundSerializer,
)


class AdminRoundListView(APIView):
    permission_classes = [IsAdminUser, IsTournamentCreatorOrReadOnly]

    @extend_schema(
        summary="Список раундів (Адмін)",
        description="Отримання списку раундів турніру.",
        responses={200: RoundSerializer(many=True)},
    )
    def get(self, request, tournament_id):
        rounds = Round.objects.filter(tournament_id=tournament_id)
        serializer = RoundSerializer(rounds, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Створити раунд (Адмін)",
        description="Створення нового раунду турніру.",
        request=RoundSerializer,
        responses={201: RoundSerializer},
    )
    def post(self, request, tournament_id):
        tournament = get_object_or_404(Tournament, id=tournament_id)
        self.check_object_permissions(request, tournament)

        serializer = RoundSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(tournament=tournament)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminRoundDetailView(APIView):
    permission_classes = [IsAdminUser, IsTournamentCreatorOrReadOnly]

    @extend_schema(
        summary="Деталі раунду (Адмін)",
        description="Отримання деталей конкретного раунду.",
        responses={200: RoundSerializer},
    )
    def get(self, request, tournament_id, round_id):
        round_inst = get_object_or_404(Round, id=round_id, tournament_id=tournament_id)
        serializer = RoundSerializer(round_inst)
        return Response(serializer.data)

    @extend_schema(
        summary="Редагувати раунд (Адмін)",
        description="Редагування можливе тільки для раундів у статусі Draft.",
        request=RoundSerializer,
        responses={200: RoundSerializer},
    )
    def patch(self, request, tournament_id, round_id):
        round_inst = get_object_or_404(Round, id=round_id, tournament_id=tournament_id)
        self.check_object_permissions(request, round_inst.tournament)

        if round_inst.status != Round.Status.DRAFT:
            return Response(
                {"error": "Редагувати можна лише раунди зі статусом Draft."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RoundSerializer(round_inst, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Видалити раунд (Адмін)",
        description="Видалення можливе тільки для раундів у статусі Draft.",
        responses={204: None},
    )
    def delete(self, request, tournament_id, round_id):
        round_inst = get_object_or_404(Round, id=round_id, tournament_id=tournament_id)
        self.check_object_permissions(request, round_inst.tournament)

        if round_inst.status != Round.Status.DRAFT:
            return Response(
                {"error": "Видаляти можна лише раунди зі статусом Draft."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        round_inst.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminRoundStartView(APIView):
    permission_classes = [IsAdminUser, IsTournamentCreator]

    @extend_schema(
        summary="Запустити раунд (Адмін)",
        description="Зміна статусу раунду з DRAFT на ACTIVE. Перевіряється наявність критеріїв і вимог.",
        request=None,
        responses={200: RoundSerializer},
    )
    def patch(self, request, tournament_id, round_id):
        round_inst = get_object_or_404(Round, id=round_id, tournament_id=tournament_id)
        self.check_object_permissions(request, round_inst.tournament)

        if round_inst.status != Round.Status.DRAFT:
            return Response(
                {"error": "Раунд вже запущений або оцінений."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        has_criterion = EvaluationCriterion.objects.filter(round=round_inst).exists()
        has_req = RoundRequirement.objects.filter(round=round_inst).exists()
        if not has_criterion or not has_req:
            return Response(
                {"error": "Раунд повинен мати принаймні один критерій та вимогу."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Перевірка попереднього раунду
        prev_round = (
            Round.objects.filter(tournament=round_inst.tournament, orderIndex__lt=round_inst.orderIndex)
            .order_by("-orderIndex")
            .first()
        )

        if prev_round and prev_round.status != Round.Status.EVALUATED:
            return Response(
                {"error": "Попередній раунд повинен бути оцінений."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        round_inst.status = Round.Status.ACTIVE
        round_inst.save()
        serializer = RoundSerializer(round_inst)
        return Response(serializer.data)


class AdminRoundAttachmentView(APIView):
    permission_classes = [IsAdminUser, IsTournamentCreator]

    @extend_schema(
        summary="Додати матеріали до раунду (Адмін)",
        description="Створення нового матеріалу (attachment).",
        request=RoundAttachmentSerializer,
        responses={201: RoundAttachmentSerializer},
    )
    def post(self, request, tournament_id, round_id):
        round_inst = get_object_or_404(Round, id=round_id, tournament_id=tournament_id)
        self.check_object_permissions(request, round_inst.tournament)

        serializer = RoundAttachmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(round=round_inst)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminRoundRequirementView(APIView):
    permission_classes = [IsAdminUser, IsTournamentCreator]

    @extend_schema(
        summary="Додати вимогу (Адмін)",
        description="Створення нової вимоги для сабміту в раунді.",
        request=RoundRequirementSerializer,
        responses={201: RoundRequirementSerializer},
    )
    def post(self, request, tournament_id, round_id):
        round_inst = get_object_or_404(Round, id=round_id, tournament_id=tournament_id)
        self.check_object_permissions(request, round_inst.tournament)

        serializer = RoundRequirementSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(round=round_inst)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminRoundCriterionView(APIView):
    permission_classes = [IsAdminUser, IsTournamentCreator]

    @extend_schema(
        summary="Додати критерій (Адмін)",
        description="Створення нового критерію оцінювання в раунді.",
        request=EvaluationCriterionSerializer,
        responses={201: EvaluationCriterionSerializer},
    )
    def post(self, request, tournament_id, round_id):
        round_inst = get_object_or_404(Round, id=round_id, tournament_id=tournament_id)
        self.check_object_permissions(request, round_inst.tournament)

        serializer = EvaluationCriterionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(round=round_inst)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
