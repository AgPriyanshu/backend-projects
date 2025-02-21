from rest_framework.routers import DefaultRouter

from .views import UrlShortnerViewerSet

router = DefaultRouter()
router.register("", UrlShortnerViewerSet, basename="urls")

urlpatterns = []

urlpatterns += router.urls
