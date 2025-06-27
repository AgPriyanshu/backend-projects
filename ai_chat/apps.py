from django.apps import AppConfig


class AiChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ai_chat"
    verbose_name = "AI Chat"
    
    def ready(self):
        """Initialize app when Django starts"""
        pass
