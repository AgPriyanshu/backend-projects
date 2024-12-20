from django.contrib.auth.password_validation import validate_password
from rest_framework.serializers import CharField, Serializer


class AuthSerializer(Serializer):
    username = CharField(max_length=50, required=True, write_only=True)
    password = CharField(max_length=20, required=True, write_only=True)

    def validate(self, attrs):
        validate_password(attrs.get("password"))
        return super().validate(attrs)
