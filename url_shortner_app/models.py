import base64
import uuid

from django.db import models

from shared.models.base_models import BaseModel


def generate_base62_slug():
    return (
        base64.urlsafe_b64encode(uuid.uuid4().bytes).decode("utf-8").rstrip("=\n")[:8]
    )


class Url(BaseModel):
    url = models.URLField(help_text="Enter a valid URL")
    slug = models.CharField(max_length=8, editable=False, unique=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            slug = generate_base62_slug()
            while Url.objects.filter(slug=slug).exists():
                slug = generate_base62_slug()
            self.slug = slug
        super().save(*args, **kwargs)
