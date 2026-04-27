import re

from rest_framework import serializers

# Indian mobile: starts with 6-9 followed by 9 digits, prefixed with +91.
PHONE_REGEX = re.compile(r"^\+91[6-9]\d{9}$")


def _validate_phone(value: str) -> str:
    value = (value or "").strip()
    if not PHONE_REGEX.match(value):
        raise serializers.ValidationError(
            "Phone must be a valid Indian mobile, e.g. +919876543210."
        )
    return value


class OTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField()

    def validate_phone(self, value):
        return _validate_phone(value)


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField()
    otp = serializers.RegexField(regex=r"^\d{6}$")

    def validate_phone(self, value):
        return _validate_phone(value)


class RefreshTokenSerializer(serializers.Serializer):
    token = serializers.CharField()
