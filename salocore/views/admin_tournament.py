from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    extend_schema,
)
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Tournament, TournamentAdmin, TournamentJury
from ..permissions import IsTournamentCreator, IsTournamentCreatorOrReadOnly
from ..serializers import (
    TournamentAdminSerializer,
    TournamentDetailSerializer,
    TournamentJurySerializer,
    TournamentSerializer,
)

User = get_user_model()


class AdminTournamentListView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Список турнірів (Адмін)",
        description="Отримання списку всіх турнірів. Доступно для адміністраторів.",
        responses={200: TournamentSerializer(many=True)},
    )
    def get(self, request):
        queryset = Tournament.objects.all()
        serializer = TournamentSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Створити турнір (Адмін)",
        description="Створення нового турніру. Автор турніру автоматично стає його творцем.",
        request=TournamentSerializer,
        responses={201: TournamentSerializer},
    )
    def post(self, request):
        serializer = TournamentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creator=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminTournamentDetailView(APIView):
    permission_classes = [IsAdminUser, IsTournamentCreatorOrReadOnly]

    @extend_schema(
        summary="Деталі турніру (Адмін)",
        description="Отримання детальної інформації про турнір.",
        responses={200: TournamentDetailSerializer},
    )
    def get(self, request, tournament_id):
        tournament = get_object_or_404(Tournament, id=tournament_id)
        serializer = TournamentDetailSerializer(tournament)
        return Response(serializer.data)

    @extend_schema(
        summary="Редагувати турнір (Адмін)",
        description="Редагування турніру. Успішно тільки якщо статус DRAFT.",
        request=TournamentDetailSerializer,
        responses={200: TournamentDetailSerializer},
    )
    def patch(self, request, tournament_id):
        tournament = get_object_or_404(Tournament, id=tournament_id)
        self.check_object_permissions(request, tournament)

        if tournament.status != Tournament.Status.DRAFT:
            return Response(
                {"error": "Редагувати можна тільки турніри зі статусом Draft."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TournamentDetailSerializer(tournament, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Видалити турнір (Адмін)",
        description="Видалення турніру. Тільки для статусів DRAFT.",
        responses={204: None},
    )
    def delete(self, request, tournament_id):
        tournament = get_object_or_404(Tournament, id=tournament_id)
        self.check_object_permissions(request, tournament)

        if tournament.status != Tournament.Status.DRAFT:
            return Response(
                {"error": "Видаляти можна тільки турніри зі статусом Draft."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tournament.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminTournamentStartView(APIView):
    permission_classes = [IsAdminUser, IsTournamentCreator]

    @extend_schema(
        summary="Запустити турнір (Адмін)",
        description="Переведення турніру зі статусу DRAFT в стан REGISTRATION.",
        request=None,
        responses={200: TournamentSerializer},
    )
    def patch(self, request, tournament_id):
        tournament = get_object_or_404(Tournament, id=tournament_id)
        self.check_object_permissions(request, tournament)

        if tournament.status != Tournament.Status.DRAFT:
            return Response(
                {"error": "Турнір вже запущений або знаходиться не в статусі Draft."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        has_jury = TournamentJury.objects.filter(tournament=tournament).exists()
        if not has_jury:
            return Response(
                {"error": "Турнір повинен мати хоча б одного члена журі."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tournament.status = Tournament.Status.REGISTRATION
        tournament.save()
        serializer = TournamentSerializer(tournament)
        return Response(serializer.data)


class AdminTournamentJuryDetailView(APIView):
    permission_classes = [IsAdminUser, IsTournamentCreator]

    @extend_schema(
        summary="Видалити журі з турніру (Адмін)",
        description="Видалення члена журі за його user_id.",
        responses={204: None},
    )
    def delete(self, request, tournament_id, user_id):
        tournament = get_object_or_404(Tournament, id=tournament_id)
        self.check_object_permissions(request, tournament)

        jury = get_object_or_404(TournamentJury, tournament=tournament, user_id=user_id)
        jury.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminTournamentJuryView(APIView):
    permission_classes = [IsAdminUser, IsTournamentCreatorOrReadOnly]

    @extend_schema(
        summary="Список журі турніру (Адмін)",
        description="Отримання списку членів журі.",
        responses={200: TournamentJurySerializer(many=True)},
    )
    def get(self, request, tournament_id):
        jury_list = TournamentJury.objects.filter(tournament_id=tournament_id)
        serializer = TournamentJurySerializer(jury_list, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Запросити журі (Адмін)",
        description="Додавання журі за invite_code.",
        request={"application/json": {"type": "object", "properties": {"invite_code": {"type": "string"}}}},
        responses={201: TournamentJurySerializer},
    )
    def post(self, request, tournament_id):
        tournament = get_object_or_404(Tournament, id=tournament_id)
        self.check_object_permissions(request, tournament)

        invite_code = request.data.get("invite_code")
        if not invite_code:
            return Response({"error": "Обов'язкове поле invite_code."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(invite_code=invite_code)
        except User.DoesNotExist:
            return Response({"error": "Користувач не знайдений."}, status=status.HTTP_404_NOT_FOUND)

        if TournamentJury.objects.filter(tournament=tournament, user=user).exists():
            return Response({"error": "Користувач вже є журі."}, status=status.HTTP_400_BAD_REQUEST)

        jury = TournamentJury.objects.create(tournament=tournament, user=user)
        serializer = TournamentJurySerializer(jury)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminTournamentAdminDetailView(APIView):
    permission_classes = [IsAdminUser, IsTournamentCreator]

    @extend_schema(
        summary="Видалити адміністратора турніру",
        description="Видалення адміністратора за його user_id.",
        responses={204: None},
    )
    def delete(self, request, tournament_id, user_id):
        tournament = get_object_or_404(Tournament, id=tournament_id)
        self.check_object_permissions(request, tournament)

        admin = get_object_or_404(TournamentAdmin, tournament=tournament, user_id=user_id)
        admin.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminTournamentAdminsView(APIView):
    permission_classes = [IsAdminUser, IsTournamentCreatorOrReadOnly]

    @extend_schema(
        summary="Список адміністраторів турніру",
        description="Отримання списку адміністраторів конкретного турніру.",
        responses={200: TournamentAdminSerializer(many=True)},
    )
    def get(self, request, tournament_id):
        admin_list = TournamentAdmin.objects.filter(tournament_id=tournament_id)
        serializer = TournamentAdminSerializer(admin_list, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Запросити адміністратора турніру",
        description="Додавання адміністратора за invite_code.",
        request={"application/json": {"type": "object", "properties": {"invite_code": {"type": "string"}}}},
        responses={201: TournamentAdminSerializer},
    )
    def post(self, request, tournament_id):
        tournament = get_object_or_404(Tournament, id=tournament_id)
        self.check_object_permissions(request, tournament)

        invite_code = request.data.get("invite_code")
        if not invite_code:
            return Response({"error": "Обов'язкове поле invite_code."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(invite_code=invite_code)
        except User.DoesNotExist:
            return Response({"error": "Користувач не знайдений."}, status=status.HTTP_404_NOT_FOUND)

        if TournamentAdmin.objects.filter(tournament=tournament, user=user).exists():
            return Response({"error": "Користувач вже є адміністратором."}, status=status.HTTP_400_BAD_REQUEST)

        admin = TournamentAdmin.objects.create(tournament=tournament, user=user)
        serializer = TournamentAdminSerializer(admin)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
