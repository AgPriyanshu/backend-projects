from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class BaseSerializer(serializers.ModelSerializer):
    """
    Features of this serializer:
        - A base serializer that raises a 400 error if any read-only fields are attempted to be updated.
    """

    def validate(self, attrs):
        # Check if any read-only fields are being updated.
        if hasattr(self.Meta, "read_only_fields") and self.Meta.read_only_fields:
            for field in self.Meta.read_only_fields:
                if field in self.initial_data:
                    raise ValidationError(
                        {field: f"{field} is a read-only field and cannot be updated."}
                    )

        return super().validate(attrs)
