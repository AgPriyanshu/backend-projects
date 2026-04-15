"""Celery tasks for the web_gis_app module."""

import logging
import tempfile

from celery import shared_task
from django.utils import timezone

from shared.infrastructure import InfraManager

from .constants import DatasetType, FileFormat, ProcessingJobStatus, TileSetStatus
from .models import Dataset, ProcessingJob, TileSet
from .progress import ProgressReporter
from .tool_registry import get_tool, load_workflow_class
from .workflows.cog_workflow import COGWorkflow

logger = logging.getLogger(__name__)




@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_cog_task(self, dataset_id: str):
    """
    Background task to generate a tile-ready COG from an uploaded orthomosaic.

    Creates a TileSet record, runs the COGWorkflow, and marks the tileset
    as READY or FAILED depending on the outcome.
    """
    logger.info(f"Starting COG generation task for dataset_id: {dataset_id}")

    try:
        dataset = Dataset.objects.get(id=dataset_id)
        logger.info(f"Found dataset: {dataset.id}, type: {dataset.type}, path: {dataset.cloud_storage_path}")
    except Dataset.DoesNotExist:
        logger.error(f"Dataset {dataset_id} not found. Aborting COG generation.")
        return

    # Get or create the TileSet in PROCESSING state.
    tileset, created = TileSet.objects.update_or_create(
        dataset=dataset,
        defaults={"status": TileSetStatus.PROCESSING, "error_message": ""},
    )
    logger.info(f"TileSet {'created' if created else 'updated'} for processing: {tileset.id}")

    try:
        with tempfile.TemporaryDirectory(prefix="cog_") as work_dir:
            bucket = InfraManager.object_storage.default_bucket
            upload_key = f"tilesets/{tileset.id}/processed.tif"

            # Construct S3 URIs
            download_url = f"s3://{bucket}/{dataset.cloud_storage_path}"
            upload_url = f"s3://{bucket}/{upload_key}"

            logger.info(f"Preparing COG workflow. Download: {download_url}, Upload: {upload_url}")

            source_path = f"{work_dir}/source.tif"

            workflow = COGWorkflow(
                payload={
                    # Shared Download operation payload.
                    "download": {
                        "download_url": download_url,
                        "download_to_path": source_path,
                    },
                    # GenerateCOG uses the download output automatically.
                    "generate_cog": {
                        "input_path": source_path,
                        "work_dir": work_dir,
                    },
                    # Shared Upload operation payload.
                    "upload": {
                        "upload_url": upload_url,
                        "upload_from_path": f"{work_dir}/output.tif",
                    },
                    "update_tileset": {
                        "tileset_id": str(tileset.id),
                        "storage_path": upload_key,
                    },
                }
            )
            workflow.execute()

        logger.info(f"COG generation complete for dataset {dataset_id}.")

    except Exception as exc:
        logger.exception(f"COG generation failed for dataset {dataset_id}: {exc}")
        tileset.status = TileSetStatus.FAILED
        tileset.error_message = str(exc)[:2000]
        tileset.save(update_fields=["status", "error_message"])

        # Retry on transient errors.
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=1, default_retry_delay=120)
def run_processing_tool(self, job_id: str):
    """Run a geoprocessing tool configured by a ProcessingJob.

    Loads the job, dispatches the matching workflow, and keeps the job
    lifecycle + SSE progress stream in sync.
    """

    logger.info("Starting processing job %s", job_id)

    try:
        job = ProcessingJob.objects.select_related("user").get(pk=job_id)
    except ProcessingJob.DoesNotExist:
        logger.error("ProcessingJob %s not found.", job_id)
        return

    job.status = ProcessingJobStatus.PROCESSING
    job.started_at = timezone.now()
    job.celery_task_id = self.request.id or ""
    job.save(update_fields=["status", "started_at", "celery_task_id", "updated_at"])

    reporter = ProgressReporter(job=job, user=job.user)
    reporter.report(0, "Starting...")

    try:
        tool = get_tool(job.tool_name)
        workflow_cls = load_workflow_class(job.tool_name)
        payload = _build_workflow_payload(job, tool)

        workflow = workflow_cls(payload=payload)
        workflow.ctx["progress_reporter"] = reporter
        workflow.execute()

        job.status = ProcessingJobStatus.COMPLETED
        job.completed_at = timezone.now()
        job.progress = 100
        job.save(update_fields=["status", "completed_at", "progress", "updated_at"])

        output_id = str(job.output_dataset_id) if job.output_dataset_id else None
        reporter.complete(output_dataset_id=output_id)

        logger.info("Processing job %s completed.", job_id)

    except Exception as exc:
        logger.exception("Processing job %s failed: %s", job_id, exc)
        job.status = ProcessingJobStatus.FAILED
        job.completed_at = timezone.now()
        job.error_message = str(exc)[:2000]
        job.save(update_fields=["status", "completed_at", "error_message", "updated_at"])

        reporter.fail(job.error_message)


def _build_workflow_payload(job: ProcessingJob, tool) -> dict:
    """Compose the dict payload each workflow expects, keyed by operation name."""

    input_datasets = list(job.input_datasets.all())

    if not input_datasets:
        raise ValueError("ProcessingJob requires at least one input dataset.")

    primary_input = input_datasets[0]
    params = dict(job.parameters or {})

    output_parent_id = params.pop("__output_parent_id", None)
    output_name = params.pop("__output_name", None) or f"{tool.label}"

    category = tool.category.value
    output_type = tool.output_type
    output_format = (
        FileFormat.COG.value
        if output_type == DatasetType.RASTER.value
        else FileFormat.GEOPACKAGE.value
    )

    create_output_payload = {
        "job_id": str(job.pk),
        "output_name": output_name,
        "output_parent_id": output_parent_id,
        "output_type": output_type,
        "output_format": output_format,
    }

    if category == "vector":
        # Vector workflows: first op is the vector op, then CreateOutputDataset.
        first_op_name = tool.workflow_path.rsplit(".", 1)[-1].replace("Workflow", "Op")
        first_op_key = _camel_to_snake(first_op_name)
        first_op_payload = {
            "job_id": str(job.pk),
            "input_dataset_id": str(primary_input.id),
            **params,
        }

        return {
            first_op_key: first_op_payload,
            "create_output_dataset": create_output_payload,
        }

    # Raster workflows: Download -> <op> -> (ExtractRasterMetadata) -> (Upload) -> CreateOutputDataset.
    bucket = InfraManager.object_storage.default_bucket
    download_url = f"s3://{bucket}/{primary_input.cloud_storage_path}"
    work_dir = tempfile.mkdtemp(prefix=f"job_{job.pk}_")
    source_path = f"{work_dir}/source.tif"
    output_path = f"{work_dir}/output.tif"

    first_op_name = tool.workflow_path.rsplit(".", 1)[-1].replace("Workflow", "Op")
    first_op_key = _camel_to_snake(first_op_name)
    first_op_payload = {
        "job_id": str(job.pk),
        "input_path": source_path,
        "work_dir": work_dir,
        **params,
    }

    payload = {
        "download": {
            "download_url": download_url,
            "download_to_path": source_path,
        },
        first_op_key: first_op_payload,
        "create_output_dataset": create_output_payload,
    }

    if output_type == DatasetType.RASTER.value:
        upload_key = f"processing/{job.pk}/output.tif"
        upload_url = f"s3://{bucket}/{upload_key}"

        payload["extract_raster_metadata"] = {"path": output_path}
        payload["upload"] = {
            "upload_url": upload_url,
            "upload_from_path": output_path,
        }
        create_output_payload["storage_path"] = upload_key

    return payload


def _camel_to_snake(name: str) -> str:
    import re

    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)

    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
