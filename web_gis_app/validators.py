from django.core.exceptions import ValidationError

LAYER_TYPES = {
    "background",
    "fill",
    "line",
    "symbol",
    "circle",
    "heatmap",
    "fill-extrusion",
    "raster",
    "hillshade",
    "sky",
}

def validate_style_spec(style):
    if not isinstance(style, dict):
        raise ValidationError("Style must be a JSON object.")

    if style.get("version") != 8:
        raise ValidationError("Style version must be 8.")

    sources = style.get("sources")

    if not isinstance(sources, dict):
        raise ValidationError("Style must include a valid 'sources' object.")

    for source_name, source_config in sources.items():
        if not isinstance(source_name, str) or not source_name.strip():
            raise ValidationError("Source names must be non-empty strings.")

        if not isinstance(source_config, dict):
            raise ValidationError(f"Source '{source_name}' must be an object.")

        if "type" not in source_config:
            raise ValidationError(f"Source '{source_name}' must include 'type'.")

    layers = style.get("layers")

    if not isinstance(layers, list):
        raise ValidationError("Style must include a valid 'layers' array.")

    layer_ids = set()

    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise ValidationError(f"Layer at index {index} must be an object.")

        layer_id = layer.get("id")

        if not isinstance(layer_id, str) or not layer_id.strip():
            raise ValidationError(
                f"Layer at index {index} must include a non-empty 'id'."
            )

        if layer_id in layer_ids:
            raise ValidationError(f"Layer id '{layer_id}' is duplicated.")

        layer_ids.add(layer_id)

        ref = layer.get("ref")

        if ref is not None and not isinstance(ref, str):
            raise ValidationError(f"Layer '{layer_id}' has an invalid 'ref'.")

        if ref:
            continue

        layer_type = layer.get("type")

        if layer_type not in LAYER_TYPES:
            raise ValidationError(f"Layer '{layer_id}' has an invalid 'type'.")

        source_name = layer.get("source")

        if layer_type not in {"background", "sky"}:
            if not isinstance(source_name, str) or not source_name.strip():
                raise ValidationError(
                    f"Layer '{layer_id}' must include a non-empty 'source'."
                )

            if source_name not in sources:
                raise ValidationError(
                    f"Layer '{layer_id}' references unknown source '{source_name}'."
                )

        if source_name is not None and source_name not in sources:
            raise ValidationError(
                f"Layer '{layer_id}' references unknown source '{source_name}'."
            )
