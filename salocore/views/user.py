from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers import UserNameSerializer, UserProfileSerializer


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Отримати профіль користувача",
        responses={200: UserProfileSerializer},
    )
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Частково оновити поточний профіль користувача",
        request=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(description="Помилка валідації"),
        },
    )
    def patch(self, request):
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.update(request.user, serializer.validated_data)
        # Return fresh representation
        out = UserProfileSerializer(request.user)
        return Response(out.data, status=status.HTTP_200_OK)


class UserNameView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Отримати ім'я та прізвище користувача",
        description="Повертає скорочену версію профілю: тільки ім'я та прізвище поточного користувача.",
        responses={
            200: UserNameSerializer,
            401: OpenApiResponse(description="Потрібна авторизація (JWT)"),
        },
        examples=[
            OpenApiExample(
                "Приклад відповіді",
                value={"firstName": "Іван", "lastName": "Богун"},
                response_only=True,
            )
        ],
        tags=["User"],
    )
    def get(self, request):
        serializer = UserNameSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
