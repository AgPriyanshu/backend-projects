from django.contrib import admin
from django.utils.html import format_html
from .models import ChatSession, ChatMessage, LLMModel, ChatPreset


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'model_name', 'message_count', 'created_at', 'updated_at', 'is_active']
    list_filter = ['model_name', 'is_active', 'enable_tools', 'created_at']
    search_fields = ['title', 'user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'message_count']
    ordering = ['-updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'title', 'is_active')
        }),
        ('Model Configuration', {
            'fields': ('model_name', 'temperature', 'max_tokens', 'enable_tools')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'message_count'),
            'classes': ('collapse',)
        }),
    )
    
    def message_count(self, obj):
        return obj.message_count
    message_count.short_description = 'Messages'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session_title', 'role', 'content_preview', 'created_at', 'token_count']
    list_filter = ['role', 'created_at', 'session__model_name']
    search_fields = ['content', 'session__title', 'session__user__username']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Message Information', {
            'fields': ('id', 'session', 'role', 'content')
        }),
        ('Tool Information', {
            'fields': ('tool_calls', 'tool_call_id'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata', 'token_count', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def session_title(self, obj):
        return obj.session.title or f"Chat {obj.session.id.hex[:8]}"
    session_title.short_description = 'Session'
    
    def content_preview(self, obj):
        if len(obj.content) > 100:
            return obj.content[:100] + "..."
        return obj.content
    content_preview.short_description = 'Content'


@admin.register(LLMModel)
class LLMModelAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'parameter_count', 'is_available', 'is_default', 'updated_at']
    list_filter = ['is_available', 'is_default', 'updated_at']
    search_fields = ['name', 'display_name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['display_name']
    
    fieldsets = (
        ('Model Information', {
            'fields': ('name', 'display_name', 'description', 'parameter_count')
        }),
        ('Configuration', {
            'fields': ('size', 'context_length', 'is_available', 'is_default')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        # Make name readonly for existing objects
        if obj:
            return self.readonly_fields + ['name']
        return self.readonly_fields


@admin.register(ChatPreset)
class ChatPresetAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'model_name', 'is_public', 'created_at']
    list_filter = ['is_public', 'model_name', 'enable_tools', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']
    
    fieldsets = (
        ('Preset Information', {
            'fields': ('name', 'description', 'created_by', 'is_public')
        }),
        ('System Configuration', {
            'fields': ('system_prompt', 'model_name', 'temperature', 'max_tokens', 'enable_tools')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj and obj.created_by != request.user and not request.user.is_superuser:
            # Non-superusers can only edit their own presets
            readonly_fields.extend(['created_by', 'is_public'])
        return readonly_fields
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(created_by=request.user)
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
