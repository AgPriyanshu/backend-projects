from rest_framework import serializers

from shared.serializers.base_serializer import BaseModelSerializer

from .models import LLM, ChatSession


class ChatSessionSerializer(BaseModelSerializer):
    llm = serializers.PrimaryKeyRelatedField(
        queryset=LLM.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ChatSession
        fields = "__all__"
        read_only_fields = ("user",)


class LLMSerializer(BaseModelSerializer):
    class Meta:
        model = LLM
        fields = "__all__"
