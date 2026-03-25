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
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        summary="Логін",
        description="Отримання JWT: access і refresh токенів через JSON body.",
        responses={
            200: TokenResponseSerializer,
            400: OpenApiResponse(
                description="Не передані обов'язкові поля (email або password)",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Validation Error",
                        value={
                            "email": ["This field is required."],
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
        responses={
            200: OpenApiResponse(
                description="Успішне оновлення токена",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Success",
                        value={"access": "eyJhbGciOiJIUzI1NiIsInR5c..."},
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Не передано refresh токен",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Validation Error",
                        value={"refresh": ["This field is required."]},
                    )
                ],
            ),
            401: OpenApiResponse(
                description="Недійсний або прострочений refresh токен",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Unauthorized",
                        value={
                            "detail": "Token is invalid or expired",
                            "code": "token_not_valid",
                        },
                    )
                ],
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RegisterView(APIView):
    permission_classes = [AllowAny]  # <-- доступ без авторизації

    @extend_schema(
        summary="Реєстрація",
        description="Реєстрація нового користувача і отримання JWT токенів",
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(
                description="Успішна реєстрація",
                response=TokenResponseSerializer,
            ),
            400: OpenApiResponse(
                description="Помилка валідації або такий користувач вже існує",
                response=dict,
                examples=[
                    OpenApiExample(
                        "User Exists",
                        value={"error": "Користувач вже існує"},
                    ),
                    OpenApiExample(
                        "Validation Error",
                        value={
                            "email": ["This field is required."],
                            "password": ["This field is required."],
                        },
                    ),
                ],
            ),
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        if User.objects.filter(email=email).exists():
            return Response({"error": "Користувач з таким email вже існує"}, status=400)

        import uuid
        import string
        import random

        username = str(uuid.uuid4())

        invite_code = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=8)
        )
        while User.objects.filter(invite_code=invite_code).exists():
            invite_code = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=8)
            )

        user = User.objects.create_user(
            username=username, email=email, password=password, invite_code=invite_code
        )

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
        summary="Логаут",
        description="Видаляє refresh токен поточного користувача (додає в blacklist)",
        request=LogoutRequestSerializer,
        responses={
            200: OpenApiResponse(
                description="Успішний вихід",
                response=LogoutResponseSerializer,
            ),
            400: OpenApiResponse(
                description="Невалідний токен, відсутній токен або користувач не авторизовані",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Missing Token",
                        value={"error": "Refresh токен обов'язковий"},
                    ),
                    OpenApiExample(
                        "Invalid Token / Error",
                        value={"error": "Невалідний токен або ви не авторизовані"},
                    ),
                ],
            ),
            401: OpenApiResponse(
                description="Користувач не авторизований",
                response=dict,
                examples=[
                    OpenApiExample(
                        "Unauthorized",
                        value={
                            "detail": "Authentication credentials were not provided."
                        },
                    )
                ],
            ),
        },
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
