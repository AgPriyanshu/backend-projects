import logging
import secrets

import requests
from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import PermissionDenied, ValidationError

logger = logging.getLogger(__name__)

OTP_TTL_SECONDS = 300
OTP_MAX_ATTEMPTS = 3
PHONE_RATE_TTL_SECONDS = 60
IP_RATE_TTL_SECONDS = 3600
IP_RATE_MAX = 10


def _otp_key(phone: str) -> str:
    return f"ds:otp:{phone}"


def _phone_rate_key(phone: str) -> str:
    return f"ds:otp:rate:phone:{phone}"


def _ip_rate_key(ip: str) -> str:
    return f"ds:otp:rate:ip:{ip}"


def _check_rate_limits(phone: str, ip: str | None) -> None:
    if cache.get(_phone_rate_key(phone)):
        raise PermissionDenied("Please wait before requesting another OTP.")

    if ip:
        key = _ip_rate_key(ip)
        # cache.add is a no-op if the key exists; sets the TTL on first write.
        cache.add(key, 0, IP_RATE_TTL_SECONDS)
        try:
            count = cache.incr(key)
        except ValueError:
            # Window expired between add and incr — treat as fresh.
            cache.set(key, 1, IP_RATE_TTL_SECONDS)
            count = 1

        if count > IP_RATE_MAX:
            raise PermissionDenied("Too many OTP requests from this IP.")


def _send_via_msg91(phone: str, otp: str) -> None:
    """Send OTP via MSG91. In dev (no key) just log so the flow is testable."""

    if not settings.MSG91_AUTH_KEY:
        logger.warning("MSG91 not configured — OTP for %s is %s", phone, otp)
        return

    payload = {
        "template_id": settings.MSG91_TEMPLATE_ID,
        "sender": settings.MSG91_SENDER_ID,
        "short_url": "0",
        "mobiles": phone.lstrip("+"),
        "otp": otp,
    }
    headers = {"authkey": settings.MSG91_AUTH_KEY}
    try:
        r = requests.post(
            "https://control.msg91.com/api/v5/otp",
            json=payload,
            headers=headers,
            timeout=5,
        )
        r.raise_for_status()
    except requests.RequestException as exc:
        logger.exception("MSG91 send failed for %s: %s", phone, exc)
        raise ValidationError("Could not send OTP, please retry.") from exc


def request_otp(phone: str, ip: str | None = None) -> None:
    _check_rate_limits(phone, ip)

    otp = f"{secrets.randbelow(1_000_000):06d}"
    cache.set(_otp_key(phone), {"otp": otp, "attempts": 0}, OTP_TTL_SECONDS)
    cache.set(_phone_rate_key(phone), 1, PHONE_RATE_TTL_SECONDS)

    _send_via_msg91(phone, otp)


def verify_otp(phone: str, submitted: str) -> bool:
    record = cache.get(_otp_key(phone))
    if not record:
        raise ValidationError("OTP expired or not requested.")

    attempts = record.get("attempts", 0) + 1
    if attempts > OTP_MAX_ATTEMPTS:
        cache.delete(_otp_key(phone))
        raise PermissionDenied("Too many incorrect attempts. Request a new OTP.")

    if record.get("otp") != submitted:
        cache.set(
            _otp_key(phone),
            {"otp": record["otp"], "attempts": attempts},
            OTP_TTL_SECONDS,
        )
        raise ValidationError("Incorrect OTP.")

    cache.delete(_otp_key(phone))
    return True
