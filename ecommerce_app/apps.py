from django.apps import AppConfig


class EcommerceAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ecommerce_app"
    verbose_name = "E-Commerce App"

    def ready(self) -> None:
        from . import signals  # noqa: F401

        return super().ready()
