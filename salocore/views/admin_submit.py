from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Submission
from ..serializers import SubmissionSerializer


class AdminSubmissionListView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Список сабмітів раунду (Адмін)",
        description="Отримання списку робіт (сабмітів) команд для конкретного раунду.",
        responses={200: SubmissionSerializer(many=True)},
    )
    def get(self, request, tournament_id, round_id):
        submissions = Submission.objects.filter(round_id=round_id, round__tournament_id=tournament_id).order_by(
            "team__name"
        )

        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)


class AdminSubmissionDetailView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Деталі сабміту (Адмін)",
        description="Отримання детальної інформації про конкретний сабміт.",
        responses={200: SubmissionSerializer},
    )
    def get(self, request, tournament_id, round_id, submission_id):
        submission = get_object_or_404(
            Submission, id=submission_id, round_id=round_id, round__tournament_id=tournament_id
        )
        serializer = SubmissionSerializer(submission)
        return Response(serializer.data)
