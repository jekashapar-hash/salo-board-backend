from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from django.utils import timezone
from ..models import TeamMember, Submission, Round
from ..serializers import SubmissionSerializer


class TeamSubmitListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Список сабмітів команди",
        description="Отримує всі створені сабміти для вказаної команди.",
        responses={
            200: SubmissionSerializer(many=True),
            403: OpenApiResponse(description="Користувач не є учасником цієї команди"),
        },
    )
    def get(self, request, team_id):
        if not TeamMember.objects.filter(team_id=team_id, user=request.user).exists():
            return Response(status=status.HTTP_403_FORBIDDEN)
        submissions = Submission.objects.filter(team_id=team_id)
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Створення сабміту",
        description="Керує подачею рішення (сабмітом) на раунд. Тіло запиту повинно обов'язково містити round (ID раунду).",
        request=SubmissionSerializer,
        responses={
            201: SubmissionSerializer,
            400: OpenApiResponse(
                description="Помилка валідації, дедлайн пройшов, або сабміт вже існує",
                response=dict,
                examples=[
                    OpenApiExample("Error", value={"error": "Термін здачі пройшов."})
                ],
            ),
            403: OpenApiResponse(description="Користувач не є учасником цієї команди"),
            404: OpenApiResponse(description="Раунд не знайдено"),
        },
    )
    def post(self, request, team_id):
        if not TeamMember.objects.filter(team_id=team_id, user=request.user).exists():
            return Response(status=status.HTTP_403_FORBIDDEN)
        round_id = request.data.get("round")
        if not round_id:
            return Response(
                {"error": "Вкажіть round"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            round_obj = Round.objects.get(id=round_id, tournament__team__id=team_id)
        except Round.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if timezone.now() > round_obj.deadline:
            return Response(
                {"error": "Термін здачі пройшов."}, status=status.HTTP_400_BAD_REQUEST
            )

        if Submission.objects.filter(round_id=round_id, team_id=team_id).exists():
            return Response(
                {"error": "Сабміт вже створений."}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SubmissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                round=round_obj, team_id=team_id, status=Submission.Status.DRAFT
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TeamSubmitDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Редагування сабміту",
        description="Часткове оновлення інформації про сабміт. Можна відправити сабміт (status=SU) або повернути до чернетки (status=DR).",
        request=SubmissionSerializer,
        responses={
            200: SubmissionSerializer,
            400: OpenApiResponse(
                description="Дедлайн пройшов, або некоректна зміна статусу"
            ),
            403: OpenApiResponse(description="Користувач не учасник команди"),
            404: OpenApiResponse(description="Сабміт не знайдено"),
        },
    )
    def patch(self, request, team_id, submit_id):
        if not TeamMember.objects.filter(team_id=team_id, user=request.user).exists():
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            sub = Submission.objects.get(id=submit_id, team_id=team_id)
        except Submission.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        round_passed = timezone.now() > sub.round.deadline
        new_status = request.data.get("status")

        if round_passed:
            return Response(
                {"error": "Термін здачі пройшов."}, status=status.HTTP_400_BAD_REQUEST
            )

        if (
            sub.status == Submission.Status.SUBMITTED
            and new_status != Submission.Status.DRAFT
        ):
            return Response(
                {"error": "Сабміт відправлено. Скасуйте (status=DR), щоб редагувати."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubmissionSerializer(sub, data=request.data, partial=True)
        if serializer.is_valid():
            if (
                new_status == Submission.Status.SUBMITTED
                and sub.status == Submission.Status.DRAFT
            ):
                sub.submitted_at = timezone.now()
                serializer.save(submitted_at=timezone.now())
            else:
                serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
