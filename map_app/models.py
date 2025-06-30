from django.db import models
from django.contrib.gis.db import models as gis_models


# Create your models here.
class Layer(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    file_name = models.CharField(max_length=255, default="")
    file_size = models.BigIntegerField(default=0)  # File size in bytes
    geometry_type = models.CharField(max_length=50, default="")  # e.g., "Polygon", "Point", "LineString"
    srid = models.IntegerField(default=4326)  # Spatial Reference System ID
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Feature(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, related_name="features")
    geometry = gis_models.GeometryField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.layer.name} - {self.get_name()}"

    def get_name(self):
        """Get feature name from attributes"""
        name_attr = self.attributes.filter(key="name").first()
        if name_attr:
            return name_attr.value
        return "Unnamed"


class FeatureAttribute(models.Model):
    """Store attributes for features with auto-detected types"""

    DATA_TYPES = [
        ("string", "String"),
        ("integer", "Integer"),
        ("float", "Float"),
        ("boolean", "Boolean"),
        ("date", "Date"),
        ("datetime", "DateTime"),
    ]

    feature = models.ForeignKey(
        Feature, on_delete=models.CASCADE, related_name="attributes"
    )
    key = models.CharField(max_length=255)
    value = models.TextField()  # Store all values as text
    data_type = models.CharField(max_length=20, choices=DATA_TYPES, default="string")
    numeric_value = models.FloatField(null=True, blank=True)  # For numeric analysis
    date_value = models.DateTimeField(null=True, blank=True)  # For temporal analysis
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["feature", "key"]
        indexes = [
            models.Index(fields=["key", "value"]),
            models.Index(fields=["key", "numeric_value"]),
            models.Index(fields=["key", "date_value"]),
            models.Index(fields=["feature", "key"]),
        ]

    def __str__(self):
        return f"{self.feature} - {self.key}: {self.value}"

    def get_typed_value(self):
        """Return the value in the correct data type"""
        if self.data_type == "integer":
            try:
                return int(self.value)
            except (ValueError, TypeError):
                return None
        elif self.data_type == "float":
            return self.numeric_value
        elif self.data_type == "boolean":
            return self.value.lower() in ("true", "1", "yes", "on")
        elif self.data_type == "date":
            return self.date_value.date() if self.date_value else None
        elif self.data_type == "datetime":
            return self.date_value
        else:
            return self.value

    def save(self, *args, **kwargs):
        """Auto-detect data type and set typed values on save"""
        self.data_type = self._detect_data_type()

        # Set typed values for analysis
        if self.data_type in ["integer", "float"]:
            try:
                self.numeric_value = float(self.value)
            except (ValueError, TypeError):
                self.numeric_value = None

        if self.data_type in ["date", "datetime"]:
            self.date_value = self._parse_date()

        super().save(*args, **kwargs)

    def _detect_data_type(self):
        """Auto-detect data type from value"""
        if not self.value:
            return "string"

        # Check boolean
        if self.value.lower() in ("true", "false", "1", "0", "yes", "no"):
            return "boolean"

        # Check integer
        if self.value.isdigit() or (
            self.value.startswith("-") and self.value[1:].isdigit()
        ):
            return "integer"

        # Check float
        try:
            float(self.value)
            if "." in self.value:
                return "float"
        except ValueError:
            pass

        # Check datetime
        if self._parse_date():
            return "datetime"

        return "string"

    def _parse_date(self):
        """Parse various date formats"""
        if not self.value:
            return None

        from datetime import datetime

        date_formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
        ]

        for date_format in date_formats:
            try:
                return datetime.strptime(self.value, date_format)
            except ValueError:
                continue

        return None
