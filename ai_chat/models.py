from django.db import models
from django.contrib.auth.models import User
import uuid

class ChatSession(models.Model):
    """Model to represent a chat session"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=255, blank=True)
    model_name = models.CharField(max_length=100, default='qwen3:8b')
    temperature = models.FloatField(default=0.7)
    max_tokens = models.IntegerField(default=2000, null=True, blank=True)
    enable_tools = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']
        db_table = 'ai_chat_session'

    def __str__(self):
        return f"{self.title or f'Chat {self.id.hex[:8]}'} - {self.user.username}"

    @property
    def message_count(self):
        return self.messages.count()

    @property
    def last_message_time(self):
        last_message = self.messages.order_by('-created_at').first()
        return last_message.created_at if last_message else self.created_at


class ChatMessage(models.Model):
    """Model to represent individual messages in a chat session"""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
        ('tool', 'Tool'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    tool_calls = models.JSONField(null=True, blank=True)  # Store tool call information
    tool_call_id = models.CharField(max_length=100, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)  # Store additional metadata
    created_at = models.DateTimeField(auto_now_add=True)
    token_count = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        db_table = 'ai_chat_message'

    def __str__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{self.role}: {content_preview}"


class LLMModel(models.Model):
    """Model to track available LLM models"""
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    size = models.BigIntegerField(null=True, blank=True)  # Model size in bytes
    parameter_count = models.CharField(max_length=50, blank=True)  # e.g., "8B", "70B"
    context_length = models.IntegerField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_name']
        db_table = 'ai_chat_llm_model'

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        # Ensure only one default model
        if self.is_default:
            LLMModel.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class ChatPreset(models.Model):
    """Model for chat presets/templates"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    system_prompt = models.TextField()
    model_name = models.CharField(max_length=100, default='qwen3:8b')
    temperature = models.FloatField(default=0.7)
    max_tokens = models.IntegerField(default=2000, null=True, blank=True)
    enable_tools = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_presets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        db_table = 'ai_chat_preset'
        unique_together = ['name', 'created_by']

    def __str__(self):
        return f"{self.name} by {self.created_by.username}"
