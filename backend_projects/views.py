from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from shared.constants import AppName
from shared.notifications import send_notification


@api_view(["GET"])
@permission_classes([AllowAny])
def ping(request):
    user = User.objects.get(id=1)
    send_notification("Hello world", AppName.BACKEND_PROJECTS, user)
    return Response({"data": "pong"})
