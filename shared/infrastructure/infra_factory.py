"""
Infrastructure factory for creating provider-specific infrastructure managers.
"""

from typing import Literal

from backend_projects.env_variables import EnvVariable

from .base import InfraManagerAbstract

ProviderType = Literal["k8s"]


class InfraManagerFactory:
    """Factory for creating infrastructure managers for different providers."""

    @staticmethod
    def create(
        provider: ProviderType = EnvVariable.INFRA_PROVIDER,
    ) -> InfraManagerAbstract:
        """
        Get the infrastructure manager instance for the specified provider.

        Args:
            provider: Cloud provider name ('k8s')

        Returns:
            Infrastructure manager instance

        Raises:
            ValueError: If provider is not supported
        """
        if provider == "k8s":
            from .k8s_infra_manager import K8sInfraManager

            return K8sInfraManager()

        else:
            raise ValueError(
                f"Unsupported provider: {provider}. " f"Supported providers: k8s"
            )


# Singleton instance of the infrastructure manager
InfraManager = InfraManagerFactory.create()
