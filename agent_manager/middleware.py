from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token


@database_sync_to_async
def get_user_from_token(token_key):
    try:
        token = Token.objects.select_related("user").get(key=token_key)
    except Token.DoesNotExist:
        return AnonymousUser()

    return token.user


class BearerTokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        token_key = None

        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)

        if "token" in query_params:
            token_key = query_params["token"][0]

        if not token_key:
            authorization_header = self.get_authorization_header(scope)
            if authorization_header:
                token_key = self.get_bearer_token(authorization_header)

        if token_key:
            scope["user"] = await get_user_from_token(token_key)

        return await self.inner(scope, receive, send)

    def get_authorization_header(self, scope):
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"authorization":
                return header_value.decode("utf-8")

        return None

    def get_bearer_token(self, authorization_header):
        scheme, _, token = authorization_header.partition(" ")

        if scheme.lower() != "bearer" or not token:
            return None

        return token
