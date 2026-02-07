from django.contrib.auth.models import User
from rest_framework import serializers

from .models import ChatMessage, ChatPreset, ChatSession, LLMModel


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'role', 'content', 'tool_calls', 'tool_call_id',
            'metadata', 'created_at', 'token_count'
        ]
        read_only_fields = ['id', 'created_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    messages = ChatMessageSerializer(many=True, read_only=True)
    message_count = serializers.ReadOnlyField()
    last_message_time = serializers.ReadOnlyField()

    class Meta:
        model = ChatSession
        fields = [
            'id', 'user', 'title', 'model_name', 'temperature',
            'max_tokens', 'enable_tools', 'created_at', 'updated_at',
            'is_active', 'messages', 'message_count', 'last_message_time'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class ChatSessionListSerializer(serializers.ModelSerializer):
    """Lighter serializer for session lists"""
    user = UserSerializer(read_only=True)
    message_count = serializers.ReadOnlyField()
    last_message_time = serializers.ReadOnlyField()

    class Meta:
        model = ChatSession
        fields = [
            'id', 'user', 'title', 'model_name', 'temperature',
            'max_tokens', 'enable_tools', 'created_at', 'updated_at',
            'is_active', 'message_count', 'last_message_time'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class CreateChatSessionSerializer(serializers.ModelSerializer):
    system_prompt = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = ChatSession
        fields = [
            'title', 'model_name', 'temperature', 'max_tokens',
            'enable_tools', 'system_prompt'
        ]

    def validate_temperature(self, value):
        if not 0 <= value <= 2:
            raise serializers.ValidationError("Temperature must be between 0 and 2")
        return value

    def validate_max_tokens(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Max tokens must be positive")
        return value


class SendMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=10000)
    stream = serializers.BooleanField(default=False)

    def validate_message(self, value):
        if not value.strip():
            raise serializers.ValidationError("Message cannot be empty")
        return value.strip()


class LLMModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMModel
        fields = [
            'id', 'name', 'display_name', 'description', 'size',
            'parameter_count', 'context_length', 'is_available',
            'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ChatPresetSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = ChatPreset
        fields = [
            'id', 'name', 'description', 'system_prompt', 'model_name',
            'temperature', 'max_tokens', 'enable_tools', 'is_public',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def validate_temperature(self, value):
        if not 0 <= value <= 2:
            raise serializers.ValidationError("Temperature must be between 0 and 2")
        return value

    def validate_max_tokens(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Max tokens must be positive")
        return value


class ChatPresetListSerializer(serializers.ModelSerializer):
    """Lighter serializer for preset lists"""
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = ChatPreset
        fields = [
            'id', 'name', 'description', 'model_name', 'is_public',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
