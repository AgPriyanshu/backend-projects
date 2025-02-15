from rest_framework import viewsets


class BaseModelViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Automatically assign the logged-in user to the user field."""
        serializer.save(user=self.request.user)
