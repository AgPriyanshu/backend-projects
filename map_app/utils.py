from django.db import transaction
from django.db.models import Count, Avg, Min, Max, Sum, StdDev, Q
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
        """Get comprehensive statistical analysis of an attribute"""
        attributes = FeatureAttribute.objects.filter(
            feature__layer=layer, key=attribute_key
        )

        if not attributes.exists():
            return {}

        # Get the data type from the first attribute
        sample_attr = attributes.first()
        data_type = sample_attr.data_type

        stats = {
            "data_type": data_type, 
            "count": attributes.count(),
            "attribute_key": attribute_key
        }

        if data_type in ["integer", "float"]:
            numeric_attrs = attributes.exclude(numeric_value__isnull=True)
            if numeric_attrs.exists():
                agg = numeric_attrs.aggregate(
                    min=Min("numeric_value"),
                    max=Max("numeric_value"),
                    avg=Avg("numeric_value"),
                    sum=Sum("numeric_value"),
                    std=StdDev("numeric_value"),
                    count=Count("id"),
                )
                stats.update(agg)
                
                # Add percentiles (approximated)
                values = list(numeric_attrs.values_list("numeric_value", flat=True))
                values.sort()
                n = len(values)
                if n > 0:
                    stats["median"] = values[n // 2] if n % 2 == 1 else (values[n // 2 - 1] + values[n // 2]) / 2
                    stats["q1"] = values[n // 4] if n >= 4 else values[0]
                    stats["q3"] = values[3 * n // 4] if n >= 4 else values[-1]
                    stats["percentile_90"] = values[int(0.9 * n)] if n >= 10 else values[-1]
                    stats["percentile_10"] = values[int(0.1 * n)] if n >= 10 else values[0]

        elif data_type == "string":
            # Get frequency distribution and unique values
            value_counts = {}
            unique_values = []
            
            for attr in attributes:
                value = attr.value
                if value not in value_counts:
                    value_counts[value] = 0
                    unique_values.append(value)
                value_counts[value] += 1

            # Sort by frequency
            sorted_values = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)
            
            stats.update({
                "unique_values": unique_values[:50],  # Limit to first 50 unique values
                "unique_count": len(unique_values),
                "frequency_distribution": dict(sorted_values[:20]),  # Top 20 most frequent
                "most_common": sorted_values[0] if sorted_values else None,
                "least_common": sorted_values[-1] if sorted_values else None
            })

        elif data_type == "boolean":
            # Count true/false values
            true_count = attributes.filter(value__in=["true", "True", "1", "yes", "Yes"]).count()
            false_count = attributes.count() - true_count
            
            stats.update({
                "true_count": true_count,
                "false_count": false_count,
                "true_percentage": (true_count / attributes.count() * 100) if attributes.count() > 0 else 0
            })

        return stats

    @staticmethod
    def get_features_by_attribute_filter(
        layer: Layer, filters: Dict[str, Any]
    ) -> List[Feature]:
        """Filter features by attribute values with enhanced filtering support"""
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
            elif isinstance(value, list):
                # Handle list of filter objects: [{"field": "pop", "operator": "gt", "value": 1000}]
                q = Q()
                for filter_item in value:
                    if isinstance(filter_item, dict):
                        operator = filter_item.get("operator")
                        filter_value = filter_item.get("value")
                        
                        if operator == "gt":
                            q &= Q(numeric_value__gt=float(filter_value))
                        elif operator == "lt":
                            q &= Q(numeric_value__lt=float(filter_value))
                        elif operator == "gte":
                            q &= Q(numeric_value__gte=float(filter_value))
                        elif operator == "lte":
                            q &= Q(numeric_value__lte=float(filter_value))
                        elif operator == "eq":
                            q &= Q(value=str(filter_value))
                        elif operator == "contains":
                            q &= Q(value__icontains=str(filter_value))
                        elif operator == "in":
                            if isinstance(filter_value, list):
                                q &= Q(value__in=[str(v) for v in filter_value])
                            else:
                                q &= Q(value=str(filter_value))
                
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
