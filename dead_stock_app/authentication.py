import jwt
from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .services.jwt_tokens import decode_token, looks_like_jwt


class JWTBearerAuthentication(BaseAuthentication):
    """
    Authenticates "Authorization: Bearer <jwt>" requests issued by the
    dead-stock OTP flow. Returns None for non-JWT bearer tokens so the
    next configured auth class (DRF Token) can try.
    """

    keyword = "bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header:
            return None

        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != self.keyword:
            return None

        raw = parts[1]
        if not looks_like_jwt(raw):
            # Likely a DRF token — let the next auth class handle it.
            return None

        try:
            payload = decode_token(raw)
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationFailed("Token expired.") from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationFailed("Invalid token.") from exc

        try:
            user = User.objects.get(pk=int(payload["sub"]))
        except (User.DoesNotExist, KeyError, ValueError) as exc:
            raise AuthenticationFailed("User not found.") from exc

        return (user, raw)

    def authenticate_header(self, request):
        return "Bearer"
