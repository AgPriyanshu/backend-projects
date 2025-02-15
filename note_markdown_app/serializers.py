from rest_framework import serializers

from .models import Note


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        exclude = ["user"]

    def create(self, validated_data):
        file = validated_data.pop("content")
        note = Note.objects.create(**validated_data)
        file.name = str(note.id) + "." + file.name.split(".")[1]
        note.content = file
        note.save()
        return note
