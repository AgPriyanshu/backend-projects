from django.db.models import FileField

from shared.models.base_models import BaseModel


class Note(BaseModel):
    content = FileField(upload_to="notes/", null=True)

    class Meta:
        verbose_name_plural = "notes"
