from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterResponseSerializer, RegisterSerializer, WhoamiSerializer


@extend_schema(responses=WhoamiSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def whoami(request):
    return Response(
        {"user_id": request.user.id, "username": request.user.username},
        status.HTTP_200_OK,
    )


@extend_schema(request=RegisterSerializer, responses={201: RegisterResponseSerializer})
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = serializer.save()
    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "message": "User created successfully",
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
        },
        status=status.HTTP_201_CREATED,
    )
