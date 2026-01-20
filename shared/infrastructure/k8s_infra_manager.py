"""
Kubernetes Infrastructure Manager Implementation.

This module provides Kubernetes-specific implementation.
Service instances are created at class definition time, initializing their clients
from environment variables.
"""

from .base import InfraManagerAbstract
from .batch.k8s_batch_compute import K8sBatchCompute
from .storage.k8_object_storage import K8sObjectStorage


class K8sInfraManager(InfraManagerAbstract):
    """
    Kubernetes implementation of the infrastructure manager.

    Configuration is loaded from environment variables:
    - K8S_NAMESPACE: Kubernetes namespace (default: 'default')
    - MINIO_ENDPOINT: MinIO endpoint for object storage
    - MINIO_ACCESS_KEY: MinIO access key
    - MINIO_SECRET_KEY: MinIO secret key
    """

    # Service instances are created here, __init__ is called automatically
    object_storage = K8sObjectStorage()
    batch_compute = K8sBatchCompute()

    def cleanup(self):
        """Clean up Kubernetes resources."""
        # Add any cleanup logic if needed
