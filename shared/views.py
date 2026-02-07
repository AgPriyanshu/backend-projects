from rest_framework import viewsets


class BaseModelViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        queryset = super().get_queryset()
        assert queryset is not None
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Automatically assign the logged-in user to the user field."""
        serializer.save(user=self.request.user)
