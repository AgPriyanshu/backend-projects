"""ProcessingJob model tracking async geoprocessing tool executions."""

from django.db import models

from shared.models.base_models import BaseModel

from ..constants import ProcessingJobStatus, ProcessingTool
from .dataset_models import Dataset, DatasetNode


class ProcessingJob(BaseModel):
    """A single execution of a geoprocessing tool on one or more input datasets."""

    tool_name = models.CharField(
        max_length=50,
        choices=ProcessingTool.choices,
        help_text="Which processing tool is being run.",
    )

    status = models.CharField(
        max_length=20,
        choices=ProcessingJobStatus.choices,
        default=ProcessingJobStatus.PENDING,
        help_text="Current lifecycle state of the job.",
    )

    progress = models.IntegerField(
        default=0,
        help_text="Progress percentage 0-100.",
    )

    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tool-specific parameters.",
    )

    input_datasets = models.ManyToManyField(
        Dataset,
        related_name="processing_jobs_as_input",
        help_text="Datasets used as input for this job.",
    )

    output_dataset = models.ForeignKey(
        Dataset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processing_jobs_as_output",
        help_text="Dataset produced by this job (null until completed).",
    )

    output_node = models.ForeignKey(
        DatasetNode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processing_jobs_as_output_node",
        help_text="DatasetNode produced by this job.",
    )

    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error message if the job failed.",
    )

    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Celery task id for revocation.",
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the job began executing.",
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the job finished (success or failure).",
    )

    class Meta:
        db_table = "processing_job"
        verbose_name = "Processing Job"
        verbose_name_plural = "Processing Jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ProcessingJob({self.tool_name}, {self.status})"
