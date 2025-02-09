from django.db.models import TextField

from shared.models import BaseModel


class Note(BaseModel):
    content = TextField()
