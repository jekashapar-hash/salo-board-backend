from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User
from .serializers import *
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# -------------------------- Auth ------------------------------------------


class CustomTokenObtainPairView(TokenObtainPairView):
    @extend_schema(
        summary="Логін",
        description="Отримання JWT: access і refresh токенів через JSON body.",
        responses={
            200: TokenResponseSerializer,
            400: OpenApiResponse(
                description="Не передані обов'язкові поля (username або password)",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Validation Error",
                        value={
                            "username": ["This field is required."],
                            "password": ["This field is required."],
                        },
                    )
                ],
            ),
            401: OpenApiResponse(
                description="Невірний логін або пароль (No active account found with the given credentials)",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Unauthorized",
                        value={
                            "detail": "No active account found with the given credentials"
                        },
                    )
                ],
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenRefreshView(TokenRefreshView):
    @extend_schema(
        summary="Оновлення токена",
        description="Отримання нового access токена по refresh токену.",
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RegisterView(APIView):
    permission_classes = [AllowAny]  # <-- доступ без авторизації

    @extend_schema(
        request=RegisterSerializer,
        responses={201: TokenResponseSerializer},
        description="Реєстрація нового користувача і отримання JWT токенів",
        summary="Реєстрація",
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        if User.objects.filter(username=username).exists():
            return Response({"error": "Користувач вже існує"}, status=400)

        user = User.objects.create_user(username=username, password=password)

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutRequestSerializer,
        responses={200: LogoutResponseSerializer, 400: dict},
        description="Видаляє refresh токен поточного користувача (додає в blacklist)",
        summary="Логаут",
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"error": "Refresh токен обов'язковий"}, status=400)

            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Вихід успішний"}, status=200)
        except Exception:
            return Response(
                {"error": "Невалідний токен або ви не авторизовані"}, status=400
            )


# --------------------------------------------------------------
