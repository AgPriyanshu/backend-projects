from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from shared.views import BaseModelViewSet

from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(BaseModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def mark_done(self, request, pk=None):
        task = self.get_object()
        task.mark_done()
        return Response({"status": "task marked as done"})

    @action(detail=True, methods=["post"])
    def mark_undone(self, request, pk=None):
        task = self.get_object()
        task.mark_undone()
        return Response({"status": "task marked as undone"})
