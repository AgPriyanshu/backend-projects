from rest_framework import serializers

from shared.serializers import BaseModelSerializer

from .models import Url


class UrlSerializer(BaseModelSerializer):
    short_url = serializers.SerializerMethodField()

    def get_short_url(self, instance):
        request = self.context["request"]
        return f"{request.build_absolute_uri()}{instance.slug}"

    class Meta:
        model = Url
        fields = (
            "url",
            "short_url",
        )
        read_only = ("slug",)
