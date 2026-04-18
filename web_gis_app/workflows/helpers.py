from ..constants import DatasetNodeType, DatasetStatus, DatasetType, FileFormat
from ..models import Dataset, DatasetNode


def report_progress(ctx: dict, progress: int, message: str = "") -> None:
    reporter = ctx.get("progress_reporter")

    if reporter is not None:
        reporter.report(progress, message)


def create_staging_dataset(user) -> Dataset:
    node = DatasetNode.objects.create(
        name="__processing_staging__",
        type=DatasetNodeType.DATASET.value,
        user=user,
    )

    return Dataset.objects.create(
        dataset_node=node,
        type=DatasetType.VECTOR,
        format=FileFormat.GEOPACKAGE,
        file_name="staging.gpkg",
        file_size=0,
        cloud_storage_path="",
        status=DatasetStatus.PENDING,
    )
