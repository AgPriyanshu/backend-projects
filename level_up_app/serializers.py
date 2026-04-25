from rest_framework import serializers

from .models import Character, Stat


class StatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stat
        fields = ["id", "name", "value", "max", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        value = attrs.get("value", self.instance.value if self.instance else 0)
        max_val = attrs.get("max", self.instance.max if self.instance else 5)

        if value > max_val:
            raise serializers.ValidationError({"value": "Value cannot exceed max."})

        return super().validate(attrs)


class InitialStatSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    value = serializers.IntegerField(default=0, min_value=0)
    max = serializers.IntegerField(default=5, min_value=1)


class CharacterSerializer(serializers.ModelSerializer):
    stats = StatSerializer(many=True, read_only=True)

    class Meta:
        model = Character
        fields = [
            "id",
            "name",
            "avatar",
            "class_name",
            "level",
            "stats",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CharacterCreateSerializer(serializers.ModelSerializer):
    stats = InitialStatSerializer(many=True, required=False, default=list)

    class Meta:
        model = Character
        fields = ["name", "avatar", "class_name", "level", "stats"]

    def create(self, validated_data):
        stats_data = validated_data.pop("stats", [])
        character = Character.objects.create(**validated_data)

        for stat_data in stats_data:
            Stat.objects.create(character=character, user=character.user, **stat_data)

        return character
