import asyncio
import contextlib

import redis.asyncio as redis
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.http import JsonResponse, StreamingHttpResponse
from rest_framework import status
from rest_framework.authtoken.models import Token

from ..utils.redis import get_notifications_channel

redis_conn = redis.from_url(
    settings.CACHES["default"]["LOCATION"],
    decode_responses=True,
)


async def redis_event_stream(channel_name: str):
    pubsub = redis_conn.pubsub()
    await pubsub.subscribe(channel_name)

    try:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )

            if message:
                data = message["data"]
                yield f"data: {data}\n\n"
                await asyncio.sleep(0)
            else:
                yield "\n\n"  # Heartbeat to keep the connection alive.
                await asyncio.sleep(1)

    except asyncio.CancelledError:
        raise
    finally:
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe(channel_name)

        with contextlib.suppress(Exception):
            await pubsub.close()


@sync_to_async
def get_user_from_token(token_key) -> User | AnonymousUser:
    try:
        token = Token.objects.select_related("user").get(key=token_key)
        return token.user
    except Token.DoesNotExist:
        return AnonymousUser()


async def sse_view(request):
    token = None
    auth_header = request.headers.get("Authorization")

    if auth_header:
        try:
            token = auth_header.split()[1]
        except IndexError:
            pass

    if not token:
        token = request.GET.get("token")

    if not token:
        return JsonResponse(
            {"error": "Token is missing"}, status=status.HTTP_400_BAD_REQUEST
        )

    user = await get_user_from_token(token)

    if not user or user.is_anonymous:
        return JsonResponse(
            {"error": "Invalid user"}, status=status.HTTP_400_BAD_REQUEST
        )

    return StreamingHttpResponse(
        redis_event_stream(get_notifications_channel(user)),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
        },
    )
