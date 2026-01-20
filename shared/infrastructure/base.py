from abc import ABC
from typing import ClassVar

from .batch.base import BatchComputeAbstract
from .storage.base import ObjectStorageAbstract


class InfraManagerAbstract(ABC):
    """
    Abstract base class for infrastructure management across different cloud providers.

    This class provides a unified interface for managing cloud infrastructure services
    including object storage and batch compute. Concrete implementations must define
    object_storage and batch_compute as class variables with service instances.

    Subclasses should define:
        object_storage: ObjectStorageAbstract - Storage service instance
        batch_compute: BatchComputeAbstract - Batch compute service instance
    """

    # Class variables that must be overridden by subclasses
    object_storage: ClassVar[ObjectStorageAbstract]
    batch_compute: ClassVar[BatchComputeAbstract]

    def __init_subclass__(cls, **kwargs):
        """
        Validate that subclasses define required class variables.
        This is called automatically when a subclass is created.
        """
        super().__init_subclass__(**kwargs)

        # Check if the subclass has defined the required class variables
        if not hasattr(cls, "object_storage"):
            raise TypeError(
                f"{cls.__name__} must define 'object_storage' as a class variable"
            )
        if not hasattr(cls, "batch_compute"):
            raise TypeError(
                f"{cls.__name__} must define 'batch_compute' as a class variable"
            )
