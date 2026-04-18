from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    CriterionEvaluation,
    Evaluation,
    EvaluationCriterion,
    RequirementEvaluation,
    RoundRequirement,
    Submission,
    Tournament,
    TournamentJury,
)
from ..serializers import (
    CriterionEvaluationSerializer,
    EvaluationSerializer,
    RequirementEvaluationSerializer,
)


class EvaluationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Деталі або створення оцінки", responses=EvaluationSerializer)
    def get(self, request, tournament_id, round_id, submission_id):
        is_jury = TournamentJury.objects.filter(tournament_id=tournament_id, user=request.user).exists()
        is_creator = Tournament.objects.filter(id=tournament_id, creator=request.user).exists()

        if not (is_jury or is_creator):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            sub = Submission.objects.get(id=submission_id, round_id=round_id)
        except Submission.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        evaluation = Evaluation.objects.filter(submission=sub, jury=request.user).first()

        if not evaluation and is_jury:
            evaluation = Evaluation.objects.create(submission=sub, jury=request.user, status=Evaluation.Status.DRAFT)

        if not evaluation:
            return Response({"error": "Оцінка не знайдена."}, status=status.HTTP_404_NOT_FOUND)

        if is_jury:
            existing_criterion_ids = set(evaluation.criterionevaluation_set.values_list("criterion_id", flat=True))
            for c in EvaluationCriterion.objects.filter(round=sub.round):
                if c.id not in existing_criterion_ids:
                    CriterionEvaluation.objects.create(evaluation=evaluation, criterion=c, score=0, comment="")

            existing_req_ids = set(evaluation.requirementevaluation_set.values_list("requirement_id", flat=True))
            for r in RoundRequirement.objects.filter(round=sub.round):
                if r.id not in existing_req_ids:
                    RequirementEvaluation.objects.create(
                        evaluation=evaluation, requirement=r, is_satisfied=False, comment=""
                    )

        serializer = EvaluationSerializer(evaluation)
        return Response(serializer.data)

    @extend_schema(
        summary="Оновлення оцінки",
        request=EvaluationSerializer,
        responses=EvaluationSerializer,
    )
    def patch(self, request, tournament_id, round_id, submission_id):
        evaluation = Evaluation.objects.filter(submission_id=submission_id, jury=request.user).first()
        if not evaluation:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if evaluation.status == Evaluation.Status.SUBMITTED and request.data.get("status") != Evaluation.Status.DRAFT:
            return Response(
                {"error": "Оцінка вже збережена. Скасуйте для редагування."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_status = request.data.get("status")
        if new_status == Evaluation.Status.SUBMITTED and evaluation.status == Evaluation.Status.DRAFT:
            evaluation.submitted_at = timezone.now()

        serializer = EvaluationSerializer(evaluation, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CriterionEvaluationDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CriterionEvaluationSerializer

    @extend_schema(
        summary="Оновлення балу за критерій",
        request=CriterionEvaluationSerializer,
        responses={200: CriterionEvaluationSerializer},
    )
    def patch(self, request, tournament_id, round_id, submission_id, crit_eval_id):
        try:
            ce = CriterionEvaluation.objects.get(
                id=crit_eval_id,
                evaluation__submission_id=submission_id,
                evaluation__jury=request.user,
            )
        except CriterionEvaluation.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if ce.evaluation.status == Evaluation.Status.SUBMITTED:
            return Response(
                {"error": "Робота вже оцінена і не є чернеткою."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CriterionEvaluationSerializer(ce, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RequirementEvaluationDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RequirementEvaluationSerializer

    @extend_schema(
        summary="Оновлення вимоги",
        request=RequirementEvaluationSerializer,
        responses={200: RequirementEvaluationSerializer},
    )
    def patch(self, request, tournament_id, round_id, submission_id, req_eval_id):
        try:
            re = RequirementEvaluation.objects.get(
                id=req_eval_id,
                evaluation__submission_id=submission_id,
                evaluation__jury=request.user,
            )
        except RequirementEvaluation.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if re.evaluation.status == Evaluation.Status.SUBMITTED:
            return Response({"error": "Робота вже оцінена."}, status=status.HTTP_403_FORBIDDEN)

        serializer = RequirementEvaluationSerializer(re, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EvaluationCriterionListView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CriterionEvaluationSerializer

    @extend_schema(
        summary="Список оцінених критеріїв",
        responses={200: CriterionEvaluationSerializer(many=True)},
    )
    def get(self, request, tournament_id, round_id, submission_id):
        criterions = CriterionEvaluation.objects.filter(evaluation__submission_id=submission_id)
        if not Tournament.objects.filter(id=tournament_id, creator=request.user).exists():
            criterions = criterions.filter(evaluation__jury=request.user)
        serializer = CriterionEvaluationSerializer(criterions, many=True)
        return Response(serializer.data)


class EvaluationRequirementListView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RequirementEvaluationSerializer

    @extend_schema(
        summary="Список перевірених вимог",
        responses={200: RequirementEvaluationSerializer(many=True)},
    )
    def get(self, request, tournament_id, round_id, submission_id):
        reqs = RequirementEvaluation.objects.filter(evaluation__submission_id=submission_id)
        if not Tournament.objects.filter(id=tournament_id, creator=request.user).exists():
            reqs = reqs.filter(evaluation__jury=request.user)
        serializer = RequirementEvaluationSerializer(reqs, many=True)
        return Response(serializer.data)


class TournamentJuryEvaluationsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Всі оцінки (роботи) журі турніру",
        description="Отримання всіх оцінок (Evaluations), виставлених поточним журі в рамках цього турніру.",
        responses={200: EvaluationSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="status",
                description="Фільтр по статусу (DR - Draft, SB - Submitted)",
                required=False,
                type=str,
            )
        ]
    )
    def get(self, request, tournament_id):
        if not TournamentJury.objects.filter(tournament_id=tournament_id, user=request.user).exists():
            return Response({"error": "Ви не є журі цього турніру."}, status=status.HTTP_403_FORBIDDEN)

        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response({"error": "Турнір не знайдено"}, status=status.HTTP_404_NOT_FOUND)

        evaluations = Evaluation.objects.filter(
            submission__round__tournament=tournament,
            jury=request.user
        )
        
        status_param = request.query_params.get("status")
        if status_param in [Evaluation.Status.DRAFT, Evaluation.Status.SUBMITTED]:
            evaluations = evaluations.filter(status=status_param)
            
        serializer = EvaluationSerializer(evaluations, many=True)
        return Response(serializer.data)


class TournamentJuryEvaluationsCountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Кількість оцінок (робіт) журі турніру",
        description="Отримання загальної кількості оцінок (Evaluations), виставлених поточним журі у турнірі.",
        responses={200: {"type": "object", "properties": {"count": {"type": "integer"}}}},
        parameters=[
            OpenApiParameter(
                name="status",
                description="Фільтр по статусу (DR - Draft, SB - Submitted)",
                required=False,
                type=str,
            )
        ]
    )
    def get(self, request, tournament_id):
        if not TournamentJury.objects.filter(tournament_id=tournament_id, user=request.user).exists():
            return Response({"error": "Ви не є журі цього турніру."}, status=status.HTTP_403_FORBIDDEN)

        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response({"error": "Турнір не знайдено"}, status=status.HTTP_404_NOT_FOUND)

        evaluations = Evaluation.objects.filter(
            submission__round__tournament=tournament,
            jury=request.user
        )
        
        status_param = request.query_params.get("status")
        if status_param in [Evaluation.Status.DRAFT, Evaluation.Status.SUBMITTED]:
            evaluations = evaluations.filter(status=status_param)
            
        count = evaluations.count()
        return Response({"count": count})
