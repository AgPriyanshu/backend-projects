from django.shortcuts import redirect
from rest_framework.permissions import AllowAny, IsAuthenticated

from shared.views import BaseModelViewSet
from url_shortner_app.models import Url

from .serializers import UrlSerializer


class UrlShortnerViewerSet(BaseModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Url.objects.all()
    serializer_class = UrlSerializer
    lookup_field = "slug"

    def get_queryset(self):
        if self.request.user:
            return Url.objects.filter(user=self.request.user)
        return super().get_queryset()

    def get_permissions(self):
        if self.action == "retrieve":
            self.permission_classes = [AllowAny]
        return super().get_permissions()

    def retrieve(self, request, slug=None, *args, **kwargs):
        url = Url.objects.get(slug=slug)
        return redirect(to=url.url)
