"""API views for the geoprocessing toolbox."""

from __future__ import annotations

from celery.result import AsyncResult
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from ..constants import ProcessingJobStatus
from ..models import ProcessingJob
from ..serializers.processing_serializers import (
    ProcessingJobCreateSerializer,
    ProcessingJobSerializer,
)
from ..tasks import run_processing_tool
from ..tool_registry import list_tools


class ProcessingJobViewSet(ModelViewSet):
    """Submit, list, and cancel geoprocessing jobs."""

    serializer_class = ProcessingJobSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return (
            ProcessingJob.objects.filter(user=self.request.user)
            .prefetch_related("input_datasets")
            .order_by("-created_at")
        )

    def create(self, request, *args, **kwargs):
        serializer = ProcessingJobCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        job_parameters = dict(validated["_validated_params"])
        job_parameters["__output_name"] = (
            validated.get("output_name")
            or f"{validated['_tool'].label} - {validated['_datasets'][0].file_name}"
        )

        if validated.get("output_parent_id"):
            job_parameters["__output_parent_id"] = str(validated["output_parent_id"])

        job = ProcessingJob.objects.create(
            user=request.user,
            tool_name=validated["tool_name"],
            parameters=job_parameters,
            status=ProcessingJobStatus.PENDING,
        )
        job.input_datasets.set(validated["_datasets"])

        async_result = run_processing_tool.delay(str(job.id))
        job.celery_task_id = async_result.id
        job.save(update_fields=["celery_task_id", "updated_at"])

        output = ProcessingJobSerializer(job).data

        return Response(output, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        job = self.get_object()

        if job.status in (ProcessingJobStatus.COMPLETED, ProcessingJobStatus.FAILED):
            return Response(
                {"detail": "Job already finished."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if job.celery_task_id:
            AsyncResult(job.celery_task_id).revoke(terminate=True)

        job.status = ProcessingJobStatus.FAILED
        job.error_message = "Cancelled by user."
        job.save(update_fields=["status", "error_message", "updated_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="tools")
    def tools(self, request):
        """Return the set of tools available to the frontend."""

        return Response({"tools": list_tools()})
