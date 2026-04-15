import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web_gis_app", "0011_remove_geojson_file_format"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProcessingJob",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "tool_name",
                    models.CharField(
                        choices=[
                            ("hillshade", "Hillshade"),
                            ("slope", "Slope"),
                            ("contour", "Contour"),
                            ("clip_raster", "Clip Raster"),
                            ("raster_calculator", "Raster Calculator"),
                            ("buffer", "Buffer"),
                            ("clip_vector", "Clip Vector"),
                            ("dissolve", "Dissolve"),
                            ("centroid", "Centroid"),
                            ("simplify", "Simplify"),
                            ("convex_hull", "Convex Hull"),
                        ],
                        help_text="Which processing tool is being run.",
                        max_length=50,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        help_text="Current lifecycle state of the job.",
                        max_length=20,
                    ),
                ),
                (
                    "progress",
                    models.IntegerField(
                        default=0, help_text="Progress percentage 0-100."
                    ),
                ),
                (
                    "parameters",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Tool-specific parameters.",
                    ),
                ),
                (
                    "error_message",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Error message if the job failed.",
                    ),
                ),
                (
                    "celery_task_id",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Celery task id for revocation.",
                        max_length=255,
                    ),
                ),
                (
                    "started_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        help_text="When the job began executing.",
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        help_text="When the job finished (success or failure).",
                    ),
                ),
                (
                    "input_datasets",
                    models.ManyToManyField(
                        help_text="Datasets used as input for this job.",
                        related_name="processing_jobs_as_input",
                        to="web_gis_app.dataset",
                    ),
                ),
                (
                    "output_dataset",
                    models.ForeignKey(
                        blank=True,
                        help_text="Dataset produced by this job (null until completed).",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="processing_jobs_as_output",
                        to="web_gis_app.dataset",
                    ),
                ),
                (
                    "output_node",
                    models.ForeignKey(
                        blank=True,
                        help_text="DatasetNode produced by this job.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="processing_jobs_as_output_node",
                        to="web_gis_app.datasetnode",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Processing Job",
                "verbose_name_plural": "Processing Jobs",
                "db_table": "processing_job",
                "ordering": ["-created_at"],
            },
        ),
    ]
