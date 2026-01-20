from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional


class JobStatus(Enum):
    """Enum for batch job statuses."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchComputeAbstract(ABC):
    """Abstract base class for batch compute implementations across different cloud providers."""

    @abstractmethod
    def __init__(self):
        """Initialize the batch compute client. Subclasses should set up their client here."""

    @abstractmethod
    def submit_job(
        self,
        job_name: str,
        image: str,
        command: List[str],
        environment: Optional[Dict[str, str]] = None,
        resources: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """
        Submit a batch job for execution.

        Args:
            job_name: Name of the job
            image: Container image to use
            command: Command to execute
            environment: Environment variables
            resources: Resource requirements (CPU, memory, etc.)
            **kwargs: Additional provider-specific parameters

        Returns:
            Job ID
        """
        raise NotImplementedError

    @abstractmethod
    def get_job_status(self, job_id: str) -> JobStatus:
        """
        Get the current status of a job.

        Args:
            job_id: Job identifier

        Returns:
            Current job status
        """
        raise NotImplementedError

    @abstractmethod
    def get_job_details(self, job_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a job.

        Args:
            job_id: Job identifier

        Returns:
            Dict containing job details
        """
        raise NotImplementedError

    @abstractmethod
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running or pending job.

        Args:
            job_id: Job identifier

        Returns:
            True if cancellation was successful
        """
        raise NotImplementedError

    @abstractmethod
    def list_jobs(
        self, status: Optional[JobStatus] = None, max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List batch jobs.

        Args:
            status: Optional status filter
            max_results: Maximum number of results to return

        Returns:
            List of job information dictionaries
        """
        raise NotImplementedError

    @abstractmethod
    def get_job_logs(self, job_id: str) -> str:
        """
        Retrieve logs for a job.

        Args:
            job_id: Job identifier

        Returns:
            Job logs as string
        """
        raise NotImplementedError
