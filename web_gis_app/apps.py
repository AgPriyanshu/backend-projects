from django.apps import AppConfig


class WebGisAppConfig(AppConfig):
    name = 'web_gis_app'

    def ready(self):
        import web_gis_app.signals  # noqa
