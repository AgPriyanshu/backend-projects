from django.db import transaction
from django.db.models import Count, Avg, Min, Max, Q
from typing import Dict, List, Any, Optional
import json
from datetime import datetime
from .models import (
    Layer,
    Feature,
    FeatureAttribute,
)


class AttributeManager:
    """Helper class for managing feature attributes and analysis"""

    @staticmethod
    def create_feature_attributes(feature: Feature, attributes_dict: Dict[str, Any]):
        """Create attributes for a feature from a dictionary"""
        for key, value in attributes_dict.items():
            FeatureAttribute.objects.update_or_create(
                feature=feature, key=key, defaults={"value": str(value)}
            )

    @staticmethod
    def get_attribute_statistics(layer: Layer, attribute_key: str) -> Dict[str, Any]:
        """Get statistical analysis of an attribute"""
        attributes = FeatureAttribute.objects.filter(
            feature__layer=layer, key=attribute_key
        )

        if not attributes.exists():
            return {}

        # Get the data type from the first attribute
        sample_attr = attributes.first()
        data_type = sample_attr.data_type

        stats = {"data_type": data_type, "total_count": attributes.count()}

        if data_type in ["integer", "float"]:
            numeric_attrs = attributes.exclude(numeric_value__isnull=True)
            if numeric_attrs.exists():
                agg = numeric_attrs.aggregate(
                    min=Min("numeric_value"),
                    max=Max("numeric_value"),
                    avg=Avg("numeric_value"),
                    count=Count("id"),
                )
                stats.update(agg)

        elif data_type == "string":
            # Get frequency distribution
            value_counts = {}
            for attr in attributes:
                value = attr.value
                value_counts[value] = value_counts.get(value, 0) + 1

            stats["frequency"] = value_counts
            stats["unique_count"] = len(value_counts)

        return stats

    @staticmethod
    def get_features_by_attribute_filter(
        layer: Layer, filters: Dict[str, Any]
    ) -> List[Feature]:
        """Filter features by attribute values"""
        feature_ids = set()

        for key, value in filters.items():
            if isinstance(value, dict):
                # Handle range queries: {'min': 10, 'max': 100}
                q = Q()
                if "min" in value:
                    q &= Q(numeric_value__gte=value["min"])
                if "max" in value:
                    q &= Q(numeric_value__lte=value["max"])

                attrs = FeatureAttribute.objects.filter(
                    feature__layer=layer, key=key
                ).filter(q)
            else:
                # Exact match
                attrs = FeatureAttribute.objects.filter(
                    feature__layer=layer, key=key, value=str(value)
                )

            current_feature_ids = set(attrs.values_list("feature_id", flat=True))

            if not feature_ids:
                feature_ids = current_feature_ids
            else:
                feature_ids &= current_feature_ids  # Intersection (AND logic)

        return Feature.objects.filter(id__in=feature_ids)

    @staticmethod
    def export_attributes_table(layer: Layer) -> List[Dict[str, Any]]:
        """Export attributes as a table format suitable for analysis"""
        features = layer.features.prefetch_related("attributes")

        table_data = []

        for feature in features:
            row = {
                "feature_id": feature.id,
                "geometry": feature.geometry.wkt if feature.geometry else None,
                "created_at": feature.created_at,
            }

            # Add attributes
            for attr in feature.attributes.all():
                row[attr.key] = attr.get_typed_value()

            table_data.append(row)

        return table_data

    @staticmethod
    def get_layer_attribute_summary(layer: Layer) -> Dict[str, Any]:
        """Get summary of all attributes in a layer"""
        attributes = FeatureAttribute.objects.filter(feature__layer=layer)

        # Group by key
        attribute_keys = attributes.values("key").distinct()

        summary = {}
        for key_info in attribute_keys:
            key = key_info["key"]
            key_attrs = attributes.filter(key=key)

            if key_attrs.exists():
                sample_attr = key_attrs.first()
                summary[key] = {
                    "data_type": sample_attr.data_type,
                    "count": key_attrs.count(),
                    "sample_values": list(
                        key_attrs.values_list("value", flat=True)[:5]
                    ),
                }

        return summary


def setup_sample_layer_with_attributes():
    """Create a sample layer with attributes for testing"""
    from django.contrib.gis.geos import Point

    layer, created = Layer.objects.get_or_create(
        name="Sample Points",
        defaults={"description": "Sample point layer for testing attributes"},
    )

    # Create sample features with attributes
    sample_data = [
        {
            "geometry": Point(0, 0),
            "attributes": {
                "name": "Point A",
                "population": "1000",
                "elevation": "100.5",
                "is_active": "true",
                "last_updated": "2024-01-01",
            },
        },
        {
            "geometry": Point(1, 1),
            "attributes": {
                "name": "Point B",
                "population": "2000",
                "elevation": "200.0",
                "is_active": "false",
                "last_updated": "2024-01-02",
            },
        },
    ]

    for data in sample_data:
        feature = Feature.objects.create(layer=layer, geometry=data["geometry"])
        AttributeManager.create_feature_attributes(feature, data["attributes"])

    return layer
