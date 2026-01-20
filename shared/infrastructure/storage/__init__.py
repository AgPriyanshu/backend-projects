"""Storage implementations package."""

from .base import ObjectStorageAbstract
from .k8_object_storage import K8sObjectStorage

__all__ = ["ObjectStorageAbstract", "K8sObjectStorage"]
