from shared.workflows.base import Workflow

from ..shared_operations import CreateOutputDataset
from .vector_operations import (
    BufferOp,
    CentroidOp,
    ClipVectorOp,
    ConvexHullOp,
    DissolveOp,
    SimplifyOp,
)


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
