"""Workflows that chain operations for each processing tool.

Vector workflows: <VectorOp> -> CreateOutputDataset
Raster workflows: Download -> <RasterOp> -> ExtractRasterMetadata -> Upload -> CreateOutputDataset
Contour: Download -> ContourOp -> CreateOutputDataset (vector output)
"""

from shared.workflows.base.base_workflow import Workflow
from shared.workflows.operations.download import Download
from shared.workflows.operations.upload import Upload

from .processing_operations import (
    BufferOp,
    CentroidOp,
    ClipRasterOp,
    ClipVectorOp,
    ContourOp,
    ConvexHullOp,
    CreateOutputDataset,
    DissolveOp,
    ExtractRasterMetadata,
    HillshadeOp,
    RasterCalcOp,
    SimplifyOp,
    SlopeOp,
)

# -- Vector workflows --


class BufferWorkflow(Workflow):
    name = "buffer_workflow"
    operations = (BufferOp, CreateOutputDataset)


class ClipVectorWorkflow(Workflow):
    name = "clip_vector_workflow"
    operations = (ClipVectorOp, CreateOutputDataset)


class DissolveWorkflow(Workflow):
    name = "dissolve_workflow"
    operations = (DissolveOp, CreateOutputDataset)


class CentroidWorkflow(Workflow):
    name = "centroid_workflow"
    operations = (CentroidOp, CreateOutputDataset)


class SimplifyWorkflow(Workflow):
    name = "simplify_workflow"
    operations = (SimplifyOp, CreateOutputDataset)


class ConvexHullWorkflow(Workflow):
    name = "convex_hull_workflow"
    operations = (ConvexHullOp, CreateOutputDataset)


# -- Raster workflows --


class HillshadeWorkflow(Workflow):
    name = "hillshade_workflow"
    operations = (Download, HillshadeOp, ExtractRasterMetadata, Upload, CreateOutputDataset)


class SlopeWorkflow(Workflow):
    name = "slope_workflow"
    operations = (Download, SlopeOp, ExtractRasterMetadata, Upload, CreateOutputDataset)


class ContourWorkflow(Workflow):
    """Contour outputs vector features, so no upload step."""

    name = "contour_workflow"
    operations = (Download, ContourOp, CreateOutputDataset)


class ClipRasterWorkflow(Workflow):
    name = "clip_raster_workflow"
    operations = (Download, ClipRasterOp, ExtractRasterMetadata, Upload, CreateOutputDataset)


class RasterCalcWorkflow(Workflow):
    name = "raster_calc_workflow"
    operations = (Download, RasterCalcOp, ExtractRasterMetadata, Upload, CreateOutputDataset)
