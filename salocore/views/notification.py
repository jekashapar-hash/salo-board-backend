from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Notification, Team, TeamMember, Tournament
from ..serializers import NotificationSerializer


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Список поточних сповіщень",
        description="Повертає список всіх актуальних сповіщень користувача. Може бути відфільтровано за статусом (наприклад, UR - Unread, RD - Read).",
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Кома-розділені статуси: UR, RD, AR",
            )
        ],
        responses={200: NotificationSerializer(many=True)},
    )
    def get(self, request):
        status_param = request.query_params.get("status")
        nots = Notification.objects.filter(user=request.user)
        if status_param:
            statuses = status_param.split(",")
            nots = nots.filter(status__in=statuses)
        serializer = NotificationSerializer(nots, many=True)
        return Response(serializer.data)


class NotificationArchiveListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Архів сповіщень",
        description="Повертає всі сповіщення користувача, які мають статус ARCHIVED (AR).",
        responses={200: NotificationSerializer(many=True)},
    )
    def get(self, request):
        nots = Notification.objects.filter(user=request.user, status=Notification.Status.ARCHIVED)
        serializer = NotificationSerializer(nots, many=True)
        return Response(serializer.data)


class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Дії зі сповіщеннями (read, archive, accept, reject)",
        description="Єдиний ендпоінт для взаємодії зі сповіщеннями через action: 'read', 'archive', 'accept', 'reject'. Якщо це TEAM_INVITE, 'accept' автоматично додасть учасника в команду.",
        request=dict,
        responses={
            200: OpenApiResponse(
                description="Успішно оновлено",
                response=dict,
                examples=[OpenApiExample("Success", value={"status": "AR"})],
            ),
            400: OpenApiResponse(
                description="Логічна помилка (запрошення минуло, команда повна, юзер вже в турнірі)",
                response=dict,
                examples=[OpenApiExample("Error", value={"error": "Запрошення минуло."})],
            ),
            404: OpenApiResponse(description="Сповіщення не знайдене"),
        },
    )
    def patch(self, request, notification_id):
        try:
            notif = Notification.objects.get(id=notification_id, user=request.user)
        except Notification.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action")
        if action == "read":
            notif.status = Notification.Status.READ
            notif.save(update_fields=["status"])
        elif action == "archive":
            notif.status = Notification.Status.ARCHIVED
            notif.save(update_fields=["status"])
        elif action == "accept" and notif.type == Notification.Type.TEAM_INVITE:
            if timezone.now() > notif.how_long_active:
                notif.status = Notification.Status.ARCHIVED
                notif.save(update_fields=["status"])
                return Response({"error": "Запрошення минуло."}, status=status.HTTP_400_BAD_REQUEST)

            import urllib.parse as urlparse

            parsed = urlparse.urlparse(notif.action_url)
            query = urlparse.parse_qs(parsed.query)
            team_id = query.get("team_id", [None])[0]

            if not team_id:
                return Response(
                    {"error": "Пошкоджене запрошення (немає team_id)"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                team = Team.objects.get(id=team_id)
            except Team.DoesNotExist:
                return Response({"error": "Команда не існує."}, status=status.HTTP_400_BAD_REQUEST)

            if team.teammember_set.count() >= team.tournament.max_team_size:
                return Response({"error": "Команда вже повна."}, status=status.HTTP_400_BAD_REQUEST)

            if team.tournament.status != Tournament.Status.REGISTRATION:
                return Response({"error": "Реєстрація закрита."}, status=status.HTTP_400_BAD_REQUEST)

            if (
                TeamMember.objects.filter(team__tournament=team.tournament, user=request.user)
                .exclude(team__status=Team.Status.DISQUALIFIED)
                .exists()
            ):
                return Response(
                    {"error": "Ви вже є в цьому турнірі."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            TeamMember.objects.create(team=team, user=request.user)
            notif.status = Notification.Status.ARCHIVED
            notif.save(update_fields=["status"])
        elif action == "reject":
            notif.status = Notification.Status.ARCHIVED
            notif.save(update_fields=["status"])

        return Response({"status": getattr(notif, "status", None)})
