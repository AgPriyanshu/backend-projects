from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from shared.views import BaseModelViewSet

from .cache import CACHE_TIMEOUT, task_list_cache_key
from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(BaseModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        """List tasks with caching support using incrementing version."""
        # Generate cache key
        cache_key = task_list_cache_key(request)

        # Try to get cached response
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        # Cache miss - get fresh data
        queryset = self.get_queryset()
        queryset = queryset.order_by("-created_at")
        response = super().list(request, *args, **kwargs)

        # Cache the response data
        cache.set(cache_key, response.data, CACHE_TIMEOUT)

        return response
