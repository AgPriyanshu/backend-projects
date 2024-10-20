from rest_framework.serializers import ModelSerializer
from ..todo_project.core.models import Task


class TaskSerializer(ModelSerializer):
    class Meta:
        model = Task
        fields = (
            "id",
            "description",
        )
        kwargs = {"id": "ready_only"}
