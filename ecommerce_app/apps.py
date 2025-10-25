from django.apps import AppConfig


class EcommerceAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ecommerce_app"

    def ready(self) -> None:
        from . import signals  # noqa: F401

        return super().ready()
