from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from .serializers import AuthSerializer


class AuthViewSet(ViewSet):
    queryset = User.objects.all()

    @action(detail=False, methods=["POST"], url_name="login")
    def login(self, request):
        request_body = request.data.copy()
        serializer = AuthSerializer(data=request_body)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )

        if user:
            user_token = Token.objects.get_or_create(user=user)
            return Response(
                {
                    "message": "User login successful",
                    "data": {"token": user_token[0].key},
                }
            )
        else:
            return Response(
                {"message": "Invalid credentials"},
                status=status.HTTP_403_FORBIDDEN,
            )

    @action(
        detail=False,
        methods=["POST"],
        url_name="register",
    )
    def register(self, request):
        request_body = request.data.copy()
        serializer = AuthSerializer(data=request_body)
        serializer.is_valid(raise_exception=True)
        # Check if user already exists.
        if user := User.objects.filter(username=serializer.validated_data["username"]):
            raise Exception("User already exists")
        else:
            user = User.objects.create_user(
                username=serializer.validated_data["username"],
                password=serializer.validated_data["password"],
            )

        return Response({"data": serializer.validated_data})
