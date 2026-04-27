from django.apps import AppConfig


class DeadStockAppConfig(AppConfig):
    name = "dead_stock_app"

    def ready(self):
        from . import signals  # noqa: F401
