"""Progress reporter for processing jobs.

Publishes throttled progress updates via the existing SSE notification pipeline
and keeps the ProcessingJob.progress field in sync with the stream.
"""

import json
from typing import Optional

from django.contrib.auth.models import User

from .models import ProcessingJob
from .notifications import send_notification

PROGRESS_STEP = 5


class ProgressReporter:
    """Throttled progress reporter for a single ProcessingJob."""

    def __init__(self, job: ProcessingJob, user: User):
        self._job = job
        self._user = user
        self._last_reported = -PROGRESS_STEP

    def report(self, progress: int, message: str = "") -> None:
        """Report progress 0-100; updates throttled to every PROGRESS_STEP percent."""

        progress = max(0, min(100, int(progress)))

        if progress - self._last_reported < PROGRESS_STEP and progress != 100:
            return

        self._last_reported = progress

        ProcessingJob.objects.filter(pk=self._job.pk).update(progress=progress)

        payload = {
            "type": "processing_progress",
            "jobId": str(self._job.pk),
            "toolName": self._job.tool_name,
            "progress": progress,
            "message": message,
        }
        send_notification(content=json.dumps(payload), user=self._user)

    def complete(self, output_dataset_id: Optional[str] = None) -> None:
        """Publish terminal completion event."""

        ProcessingJob.objects.filter(pk=self._job.pk).update(progress=100)

        payload = {
            "type": "processing_complete",
            "jobId": str(self._job.pk),
            "toolName": self._job.tool_name,
            "outputDatasetId": output_dataset_id,
        }
        send_notification(content=json.dumps(payload), user=self._user)

    def fail(self, error_message: str) -> None:
        """Publish terminal failure event."""

        payload = {
            "type": "processing_failed",
            "jobId": str(self._job.pk),
            "toolName": self._job.tool_name,
            "error": error_message,
        }
        send_notification(content=json.dumps(payload), user=self._user)
