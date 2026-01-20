"""
Shared infrastructure package for cloud-agnostic infrastructure management.

This package provides abstract base classes and concrete implementations for
managing infrastructure services across different cloud providers.

Service instances are created at module import time with clients initialized from
environment variables.

Usage:
    >>> from shared.infrastructure import InfraManager
    >>>
    >>> # Access service instances directly
    >>> InfraManager.object_storage.upload_object(file, 'my-bucket', 'path/to/file')
    >>> job_id = InfraManager.batch_compute.submit_job('my-job', 'my-image', ['python', 'script.py'])
    >>>
    >>> # Or use as a context manager for cleanup (if needed)
    >>> with InfraManager as manager:
    ...     manager.object_storage.upload_object(file, 'my-bucket', 'path/to/file')

Environment Variables:
    INFRA_PROVIDER: Provider to use ('k8s'). Defaults to 'k8s'
    K8S_NAMESPACE: Kubernetes namespace (default: 'default')
    MINIO_ENDPOINT: MinIO endpoint for object storage
    MINIO_ACCESS_KEY: MinIO access key
    MINIO_SECRET_KEY: MinIO secret key
"""

from .base import InfraManagerAbstract
from .batch.base import BatchComputeAbstract, JobStatus
from .factory import DEFAULT_PROVIDER, InfraManager, InfraManagerFactory
from .storage.base import ObjectStorageAbstract

__all__ = [
    # Abstract base classes
    "InfraManagerAbstract",
    "ObjectStorageAbstract",
    "BatchComputeAbstract",
    # Enums
    "JobStatus",
    # Factory and Manager
    "InfraManagerFactory",
    "InfraManager",
    "DEFAULT_PROVIDER",
]
