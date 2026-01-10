from rest_framework.permissions import IsAuthenticated
from rest_framework_extensions.cache.decorators import cache_response
from rest_framework_extensions.key_constructor.bits import (
    ListSqlQueryKeyBit,
    PaginationKeyBit,
    UserKeyBit,
)
from rest_framework_extensions.key_constructor.constructors import DefaultKeyConstructor

from shared.views import BaseModelViewSet

from .models import Task
from .serializers import TaskSerializer


class TaskListKeyConstructor(DefaultKeyConstructor):
    """Custom key constructor for task list caching per user."""

    user = UserKeyBit()
    list_sql = ListSqlQueryKeyBit()
    pagination = PaginationKeyBit()


class TaskViewSet(BaseModelViewSet):
    queryset = Task.objects.all().order_by("-created_at")
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    @cache_response(timeout=60 * 5, key_func=TaskListKeyConstructor())
    def list(self, request, *args, **kwargs):
        """List all tasks for the authenticated user with caching."""
        return super().list(request, *args, **kwargs)
