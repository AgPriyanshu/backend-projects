from django.contrib import admin

from agent_manager.models import LLM, ChatSession, Message


@admin.register(LLM)
class LLMAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "model_name", "url", "created_at", "updated_at")
    search_fields = ("name", "model_name", "url", "user__username", "user__email")
    list_filter = ("created_at", "updated_at")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "created_at", "updated_at")
    search_fields = ("name", "user__username", "user__email")
    list_filter = ("created_at", "updated_at")
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("user",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "user", "created_at", "updated_at")
    search_fields = ("content", "session__name", "user__username", "user__email")
    list_filter = ("created_at", "updated_at")
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("session", "user")
