"""Registry of geoprocessing tools exposed to the Web GIS processing toolbox.

Each tool is described by:
- Pydantic params model for validation.
- Workflow class that knows how to execute the tool.
- Metadata (label, description, category, compatible input types, output type,
  and a UI-friendly parameter schema used by the frontend to render the form).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from shared.workflows.schemas import StrictPayload

from .constants import DatasetType, ProcessingTool, ProcessingToolCategory

# -- Vector tool params --


class BufferParams(StrictPayload):
    distance: float = Field(..., description="Buffer distance.")
    units: Literal["meters", "kilometers", "degrees"] = "meters"
    segments: int = Field(8, ge=1, le=64)


class ClipVectorParams(StrictPayload):
    clip_dataset_id: str


class DissolveParams(StrictPayload):
    dissolve_field: Optional[str] = None


class CentroidParams(StrictPayload):
    pass


class SimplifyParams(StrictPayload):
    tolerance: float = Field(..., gt=0)


class ConvexHullParams(StrictPayload):
    per_feature: bool = False


# -- Raster tool params --


class HillshadeParams(StrictPayload):
    azimuth: float = Field(315.0, ge=0, le=360)
    altitude: float = Field(45.0, ge=0, le=90)
    z_factor: float = Field(1.0, gt=0)


class SlopeParams(StrictPayload):
    units: Literal["degrees", "percent"] = "degrees"
    z_factor: float = Field(1.0, gt=0)


class ContourParams(StrictPayload):
    interval: float = Field(..., gt=0)
    attribute_name: str = "elevation"


class ClipRasterParams(StrictPayload):
    clip_dataset_id: Optional[str] = None
    clip_geometry: Optional[dict] = None


class RasterCalcParams(StrictPayload):
    expression: str
    band_mapping: dict = Field(default_factory=dict)


# -- Tool definition --


class ToolDefinition:
    """Container for a processing tool's registry entry."""

    def __init__(
        self,
        *,
        tool: ProcessingTool,
        label: str,
        description: str,
        category: ProcessingToolCategory,
        params_model: type[StrictPayload],
        workflow_path: str,
        input_types: tuple[str, ...],
        output_type: str,
        param_schema: list[dict],
    ):
        self.tool = tool
        self.label = label
        self.description = description
        self.category = category
        self.params_model = params_model
        self.workflow_path = workflow_path
        self.input_types = input_types
        self.output_type = output_type
        self.param_schema = param_schema

    def to_frontend_dict(self) -> dict:
        return {
            "toolName": self.tool.value,
            "label": self.label,
            "description": self.description,
            "category": self.category.value,
            "inputTypes": list(self.input_types),
            "outputType": self.output_type,
            "parameters": self.param_schema,
        }


# Frontend-friendly parameter schemas.
# Each entry describes a form field the UI will render.

_BUFFER_SCHEMA = [
    {
        "name": "distance",
        "label": "Distance",
        "type": "number",
        "required": True,
        "default": 100,
        "min": 0,
    },
    {
        "name": "units",
        "label": "Units",
        "type": "select",
        "options": [
            {"value": "meters", "label": "Meters"},
            {"value": "kilometers", "label": "Kilometers"},
            {"value": "degrees", "label": "Degrees"},
        ],
        "default": "meters",
    },
    {
        "name": "segments",
        "label": "Segments",
        "type": "number",
        "default": 8,
        "min": 1,
        "max": 64,
    },
]

_CLIP_VECTOR_SCHEMA = [
    {
        "name": "clip_dataset_id",
        "label": "Clip layer",
        "type": "dataset",
        "datasetType": DatasetType.VECTOR.value,
        "required": True,
    },
]

_DISSOLVE_SCHEMA = [
    {
        "name": "dissolve_field",
        "label": "Dissolve field (optional)",
        "type": "string",
    },
]

_CENTROID_SCHEMA: list[dict] = []

_SIMPLIFY_SCHEMA = [
    {
        "name": "tolerance",
        "label": "Tolerance",
        "type": "number",
        "required": True,
        "default": 0.001,
        "min": 0,
    },
]

_CONVEX_HULL_SCHEMA = [
    {
        "name": "per_feature",
        "label": "Per feature",
        "type": "boolean",
        "default": False,
    },
]

_HILLSHADE_SCHEMA = [
    {
        "name": "azimuth",
        "label": "Azimuth",
        "type": "number",
        "default": 315,
        "min": 0,
        "max": 360,
    },
    {
        "name": "altitude",
        "label": "Altitude",
        "type": "number",
        "default": 45,
        "min": 0,
        "max": 90,
    },
    {
        "name": "z_factor",
        "label": "Z factor",
        "type": "number",
        "default": 1,
        "min": 0.01,
    },
]

_SLOPE_SCHEMA = [
    {
        "name": "units",
        "label": "Units",
        "type": "select",
        "options": [
            {"value": "degrees", "label": "Degrees"},
            {"value": "percent", "label": "Percent"},
        ],
        "default": "degrees",
    },
    {
        "name": "z_factor",
        "label": "Z factor",
        "type": "number",
        "default": 1,
        "min": 0.01,
    },
]

_CONTOUR_SCHEMA = [
    {
        "name": "interval",
        "label": "Interval",
        "type": "number",
        "required": True,
        "default": 10,
        "min": 0,
    },
    {
        "name": "attribute_name",
        "label": "Attribute name",
        "type": "string",
        "default": "elevation",
    },
]

_CLIP_RASTER_SCHEMA = [
    {
        "name": "clip_dataset_id",
        "label": "Clip layer",
        "type": "dataset",
        "datasetType": DatasetType.VECTOR.value,
    },
]

_RASTER_CALC_SCHEMA = [
    {
        "name": "expression",
        "label": "Expression",
        "type": "expression",
        "required": True,
        "placeholder": "(A - B) / (A + B)",
    },
]


TOOL_REGISTRY: dict[str, ToolDefinition] = {
    ProcessingTool.BUFFER.value: ToolDefinition(
        tool=ProcessingTool.BUFFER,
        label="Buffer",
        description="Create a buffer polygon around each input feature.",
        category=ProcessingToolCategory.VECTOR,
        params_model=BufferParams,
        workflow_path="web_gis_app.workflows.processing_workflows.BufferWorkflow",
        input_types=(DatasetType.VECTOR.value,),
        output_type=DatasetType.VECTOR.value,
        param_schema=_BUFFER_SCHEMA,
    ),
    ProcessingTool.CLIP_VECTOR.value: ToolDefinition(
        tool=ProcessingTool.CLIP_VECTOR,
        label="Clip (Vector)",
        description="Clip input features by the geometry of another vector layer.",
        category=ProcessingToolCategory.VECTOR,
        params_model=ClipVectorParams,
        workflow_path="web_gis_app.workflows.processing_workflows.ClipVectorWorkflow",
        input_types=(DatasetType.VECTOR.value,),
        output_type=DatasetType.VECTOR.value,
        param_schema=_CLIP_VECTOR_SCHEMA,
    ),
    ProcessingTool.DISSOLVE.value: ToolDefinition(
        tool=ProcessingTool.DISSOLVE,
        label="Dissolve",
        description="Merge features into a single geometry, optionally grouped by a field.",
        category=ProcessingToolCategory.VECTOR,
        params_model=DissolveParams,
        workflow_path="web_gis_app.workflows.processing_workflows.DissolveWorkflow",
        input_types=(DatasetType.VECTOR.value,),
        output_type=DatasetType.VECTOR.value,
        param_schema=_DISSOLVE_SCHEMA,
    ),
    ProcessingTool.CENTROID.value: ToolDefinition(
        tool=ProcessingTool.CENTROID,
        label="Centroid",
        description="Compute the centroid of each input feature.",
        category=ProcessingToolCategory.VECTOR,
        params_model=CentroidParams,
        workflow_path="web_gis_app.workflows.processing_workflows.CentroidWorkflow",
        input_types=(DatasetType.VECTOR.value,),
        output_type=DatasetType.VECTOR.value,
        param_schema=_CENTROID_SCHEMA,
    ),
    ProcessingTool.SIMPLIFY.value: ToolDefinition(
        tool=ProcessingTool.SIMPLIFY,
        label="Simplify",
        description="Simplify feature geometries using a tolerance.",
        category=ProcessingToolCategory.VECTOR,
        params_model=SimplifyParams,
        workflow_path="web_gis_app.workflows.processing_workflows.SimplifyWorkflow",
        input_types=(DatasetType.VECTOR.value,),
        output_type=DatasetType.VECTOR.value,
        param_schema=_SIMPLIFY_SCHEMA,
    ),
    ProcessingTool.CONVEX_HULL.value: ToolDefinition(
        tool=ProcessingTool.CONVEX_HULL,
        label="Convex Hull",
        description="Compute the convex hull of features.",
        category=ProcessingToolCategory.VECTOR,
        params_model=ConvexHullParams,
        workflow_path="web_gis_app.workflows.processing_workflows.ConvexHullWorkflow",
        input_types=(DatasetType.VECTOR.value,),
        output_type=DatasetType.VECTOR.value,
        param_schema=_CONVEX_HULL_SCHEMA,
    ),
    ProcessingTool.HILLSHADE.value: ToolDefinition(
        tool=ProcessingTool.HILLSHADE,
        label="Hillshade",
        description="Generate a hillshade raster from a DEM.",
        category=ProcessingToolCategory.RASTER,
        params_model=HillshadeParams,
        workflow_path="web_gis_app.workflows.processing_workflows.HillshadeWorkflow",
        input_types=(DatasetType.RASTER.value,),
        output_type=DatasetType.RASTER.value,
        param_schema=_HILLSHADE_SCHEMA,
    ),
    ProcessingTool.SLOPE.value: ToolDefinition(
        tool=ProcessingTool.SLOPE,
        label="Slope",
        description="Compute slope from a DEM.",
        category=ProcessingToolCategory.RASTER,
        params_model=SlopeParams,
        workflow_path="web_gis_app.workflows.processing_workflows.SlopeWorkflow",
        input_types=(DatasetType.RASTER.value,),
        output_type=DatasetType.RASTER.value,
        param_schema=_SLOPE_SCHEMA,
    ),
    ProcessingTool.CONTOUR.value: ToolDefinition(
        tool=ProcessingTool.CONTOUR,
        label="Contour",
        description="Extract contour lines from a DEM at a given interval.",
        category=ProcessingToolCategory.RASTER,
        params_model=ContourParams,
        workflow_path="web_gis_app.workflows.processing_workflows.ContourWorkflow",
        input_types=(DatasetType.RASTER.value,),
        output_type=DatasetType.VECTOR.value,
        param_schema=_CONTOUR_SCHEMA,
    ),
    ProcessingTool.CLIP_RASTER.value: ToolDefinition(
        tool=ProcessingTool.CLIP_RASTER,
        label="Clip (Raster)",
        description="Clip a raster by a polygon or vector layer.",
        category=ProcessingToolCategory.RASTER,
        params_model=ClipRasterParams,
        workflow_path="web_gis_app.workflows.processing_workflows.ClipRasterWorkflow",
        input_types=(DatasetType.RASTER.value,),
        output_type=DatasetType.RASTER.value,
        param_schema=_CLIP_RASTER_SCHEMA,
    ),
    ProcessingTool.RASTER_CALCULATOR.value: ToolDefinition(
        tool=ProcessingTool.RASTER_CALCULATOR,
        label="Raster Calculator",
        description="Apply a math expression across one or more raster bands.",
        category=ProcessingToolCategory.RASTER,
        params_model=RasterCalcParams,
        workflow_path="web_gis_app.workflows.processing_workflows.RasterCalcWorkflow",
        input_types=(DatasetType.RASTER.value,),
        output_type=DatasetType.RASTER.value,
        param_schema=_RASTER_CALC_SCHEMA,
    ),
}


def get_tool(tool_name: str) -> ToolDefinition:
    """Return the registered tool definition or raise ValueError if unknown."""

    try:
        return TOOL_REGISTRY[tool_name]
    except KeyError as exc:
        raise ValueError(f"Unknown processing tool: {tool_name}.") from exc


def list_tools() -> list[dict]:
    """Return a list of tool definitions for the frontend."""

    return [definition.to_frontend_dict() for definition in TOOL_REGISTRY.values()]


def load_workflow_class(tool_name: str) -> type:
    """Lazy-import the workflow class for a tool."""

    import importlib

    definition = get_tool(tool_name)
    module_path, _, class_name = definition.workflow_path.rpartition(".")
    module = importlib.import_module(module_path)

    return getattr(module, class_name)
