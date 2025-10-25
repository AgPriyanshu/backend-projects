from django.contrib.auth.password_validation import validate_password
from rest_framework.serializers import BooleanField, CharField, Serializer


class AuthSerializer(Serializer):
    username = CharField(
        max_length=50,
        required=True,
    )
    password = CharField(max_length=20, required=True, write_only=True)
    is_staff = BooleanField(required=False)

    def validate(self, attrs):
        validate_password(attrs.get("password"))
        return super().validate(attrs)
