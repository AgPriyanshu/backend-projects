import asyncio

import redis.asyncio as redis
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.http import StreamingHttpResponse
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError

from ..utils.redis import get_notifications_channel

redis_conn = redis.from_url(
    settings.CACHES["default"]["LOCATION"],
    decode_responses=True,
)


async def redis_event_stream(channel_name: str):
    async with redis_conn.pubsub() as pubsub:
        await pubsub.subscribe(channel_name)

        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )

                if message:
                    data = message["data"]
                    yield f"data: {data}\n\n"
                else:
                    yield "\n\n"  # Heartbeat to keep the connection alive.
                    await asyncio.sleep(5)

        except asyncio.CancelledError:
            # Handle client disconnection gracefully
            raise


@sync_to_async
def get_user_from_token(token_key) -> User | AnonymousUser:
    try:
        token = Token.objects.select_related("user").get(key=token_key)
        return token.user
    except Token.DoesNotExist:
        return AnonymousUser()


async def sse_view(request):
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise ValidationError("Token is missing")

    try:
        token = auth_header.split()[1]
    except IndexError:
        raise ValidationError("Invalid Authorization header")

    user = await get_user_from_token(token)

    if not user or user.is_anonymous:
        raise ValidationError("Invalid token")

    return StreamingHttpResponse(
        redis_event_stream(get_notifications_channel(user)),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
        },
    )
