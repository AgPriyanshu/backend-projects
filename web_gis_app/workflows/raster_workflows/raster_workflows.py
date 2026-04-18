from shared.workflows import Download, Upload, Workflow

from ..shared_operations import CreateOutputDataset
from .raster_operations import (
    ClipRasterOp,
    ContourOp,
    ExtractRasterMetadata,
    HillshadeOp,
    RasterCalcOp,
    SlopeOp,
)


class HillshadeWorkflow(Workflow):
    name = "hillshade_workflow"
    operations = (
        Download,
        HillshadeOp,
        ExtractRasterMetadata,
        Upload,
        CreateOutputDataset,
    )


class SlopeWorkflow(Workflow):
    name = "slope_workflow"
    operations = (Download, SlopeOp, ExtractRasterMetadata, Upload, CreateOutputDataset)


class ContourWorkflow(Workflow):
    name = "contour_workflow"
    operations = (Download, ContourOp, CreateOutputDataset)


class ClipRasterWorkflow(Workflow):
    name = "clip_raster_workflow"
    operations = (
        Download,
        ClipRasterOp,
        ExtractRasterMetadata,
        Upload,
        CreateOutputDataset,
    )


class RasterCalcWorkflow(Workflow):
    name = "raster_calc_workflow"
    operations = (
        Download,
        RasterCalcOp,
        ExtractRasterMetadata,
        Upload,
        CreateOutputDataset,
    )
