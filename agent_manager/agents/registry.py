from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_manager.agents.base import BaseExpert

logger = logging.getLogger(__name__)


class ExpertRegistry:
    """Singleton registry for all app experts.

    Experts register themselves at import time (typically via Django AppConfig.ready()).
    The orchestrator uses this registry to:
    - Build the routing prompt dynamically.
    - Look up experts by name for execution.
    """

    _experts: dict[str, BaseExpert] = {}

    @classmethod
    def register(cls, expert: BaseExpert) -> None:
        """Register an expert. Raises if the name is already taken."""
        if expert.name in cls._experts:
            logger.warning(
                "Expert '%s' is already registered — skipping duplicate.",
                expert.name,
            )
            return

        cls._experts[expert.name] = expert
        logger.info("Registered expert: %s", expert.name)

    @classmethod
    def get(cls, name: str) -> BaseExpert | None:
        """Look up an expert by name."""
        return cls._experts.get(name)

    @classmethod
    def all_experts(cls) -> list[BaseExpert]:
        """Return all registered experts in registration order."""
        return list(cls._experts.values())

    @classmethod
    def expert_names(cls) -> list[str]:
        """Return all registered expert names."""
        return list(cls._experts.keys())

    @classmethod
    def build_orchestrator_prompt(cls) -> str:
        """Auto-generate the orchestrator routing prompt from registered experts."""
        lines = [
            "You are an orchestrator that routes user queries to the correct expert agent.\n",
            "Available agents:",
        ]

        for expert in cls._experts.values():
            lines.append(f"- {expert.name}: {expert.description}")

        lines.append(
            "\nRespond with the name of the agent best suited to handle the user's query."
        )

        return "\n".join(lines)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered experts. Useful for testing."""
        cls._experts.clear()
