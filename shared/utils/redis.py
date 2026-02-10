from django.contrib.auth.models import AnonymousUser, User


def get_notifications_channel(user: User | AnonymousUser):
    return f"notifications_{user.pk}"
