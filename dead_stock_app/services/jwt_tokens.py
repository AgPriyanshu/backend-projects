import time
from typing import Any

import jwt
from django.conf import settings
from django.contrib.auth.models import User

ALGORITHM = "HS256"


def issue_token(user: User) -> dict[str, Any]:
    now = int(time.time())
    exp = now + settings.DS_JWT_TTL_SECONDS
    payload = {
        "sub": str(user.id),
        "phone": user.username,
        "iat": now,
        "exp": exp,
    }
    token = jwt.encode(payload, settings.DS_JWT_SECRET, algorithm=ALGORITHM)

    return {"token": token, "expires_at": exp}


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.DS_JWT_SECRET, algorithms=[ALGORITHM])


def looks_like_jwt(value: str) -> bool:
    return value.count(".") == 2
