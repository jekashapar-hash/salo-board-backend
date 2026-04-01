from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
)
from ..models import Chat, Message
from ..serializers import ChatSerializer, MessageSerializer


class ChatListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Список чатів (Користувач)",
        description="Отримання списку тільки своїх чатів. Підтримує фільтрацію ?is_solved=true/false",
        parameters=[
            OpenApiParameter(
                name="is_solved",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Фільтрація по статусу",
                required=False,
            )
        ],
        responses={200: ChatSerializer(many=True)},
    )
    def get(self, request):
        queryset = Chat.objects.filter(user=request.user).order_by("-created_at")
        
        is_solved_param = request.query_params.get("is_solved")
        if is_solved_param is not None:
            is_solved = is_solved_param.lower() == "true"
            queryset = queryset.filter(is_solved=is_solved)
            
        serializer = ChatSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Створити чат (Користувач)",
        description="Створення нового чату. Автор автоматично стає власником.",
        responses={201: ChatSerializer},
    )
    def post(self, request):
        serializer = ChatSerializer(data={})
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChatDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Закрити/відкрити чат (Користувач)",
        description="Зміна статусу is_solved для свого чату.",
        request=ChatSerializer,
        responses={200: ChatSerializer},
    )
    def patch(self, request, chat_id):
        chat = get_object_or_404(Chat, id=chat_id, user=request.user)
        
        if "is_solved" in request.data:
            chat.is_solved = request.data["is_solved"]
            chat.save(update_fields=["is_solved"])
            
        serializer = ChatSerializer(chat)
        return Response(serializer.data)


class ChatMessageListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Історія повідомлень (Користувач)",
        description="Отримання 50 останніх повідомлень свого чату.",
        responses={200: MessageSerializer(many=True)},
    )
    def get(self, request, chat_id):
        chat = get_object_or_404(Chat, id=chat_id, user=request.user)
        messages = Message.objects.filter(chat=chat).order_by("-created_at")[:50]
        
        # Reverse to show chronological order if needed, but normally frontend handles it
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

# ----------------- ADMIN VIEWS -------------------

class AdminChatListView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Список чатів (Адмін)",
        description="Отримання списку всіх чатів усіх юзерів. За замовчуванням повертаються відкриті чати, якщо не вказано is_solved=true",
        parameters=[
            OpenApiParameter(
                name="is_solved",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Фільтрація по статусу (за замовчуванням: false)",
                required=False,
            )
        ],
        responses={200: ChatSerializer(many=True)},
    )
    def get(self, request):
        is_solved_param = request.query_params.get("is_solved")
        
        # By default show unsolved chats to admin unless specified otherwise
        is_solved = False
        if is_solved_param is not None:
            is_solved = is_solved_param.lower() == "true"
            
        queryset = Chat.objects.filter(is_solved=is_solved).order_by("-created_at")
        serializer = ChatSerializer(queryset, many=True)
        return Response(serializer.data)


class AdminChatDetailView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Закрити/відкрити чат (Адмін)",
        description="Зміна статусу is_solved для будь-якого чату.",
        request=ChatSerializer,
        responses={200: ChatSerializer},
    )
    def patch(self, request, chat_id):
        chat = get_object_or_404(Chat, id=chat_id)
        
        if "is_solved" in request.data:
            chat.is_solved = request.data["is_solved"]
            chat.save(update_fields=["is_solved"])
            
        serializer = ChatSerializer(chat)
        return Response(serializer.data)


class AdminChatMessageListView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Історія повідомлень (Адмін)",
        description="Отримання 50 останніх повідомлень будь-якого чату.",
        responses={200: MessageSerializer(many=True)},
    )
    def get(self, request, chat_id):
        chat = get_object_or_404(Chat, id=chat_id)
        messages = Message.objects.filter(chat=chat).order_by("-created_at")[:50]
        
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
