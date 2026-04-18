from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


@dataclass
class ExpertResult:
    """Result returned by an expert after processing a query."""

    response: str
    ui_actions: list[dict[str, Any]] = field(default_factory=list)


class BaseExpert(ABC):
    """Abstract base class that every app expert must implement.

    Each expert encapsulates:
    - Its identity (name, description) used by the orchestrator for routing.
    - A system prompt for the conversational LLM call.
    - An action schema (Pydantic model) for structured action extraction.
    - An execute method that runs action extraction + conversational response.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the expert, e.g. 'web_gis', 'todo'."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description used by the orchestrator for routing decisions."""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt used when generating the conversational response."""
        ...

    @abstractmethod
    def get_action_schema(self) -> type[BaseModel] | None:
        """Return the Pydantic model for structured action extraction.

        Return None if the expert does not produce UI actions.
        """
        ...

    async def execute(self, query: str, llm: Any) -> ExpertResult:
        """Run action extraction and generate a conversational response.

        The default implementation:
        1. Extracts actions via structured output (if schema exists).
        2. Streams a conversational response using the expert's system prompt.

        Subclasses may override for custom behaviour.
        """
        from langchain.messages import HumanMessage, SystemMessage

        ui_actions: list[dict[str, Any]] = []
        action_schema = self.get_action_schema()

        if action_schema is not None:
            action_plan = llm.with_structured_output(action_schema).invoke(
                [
                    SystemMessage(content=self._build_action_extraction_prompt()),
                    HumanMessage(content=query),
                ]
            )
            ui_actions = self._extract_actions(action_plan)

        response = ""

        async for chunk in llm.astream(
            [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=query),
            ]
        ):
            response += chunk.content or ""

        return ExpertResult(response=response, ui_actions=ui_actions)

    def _build_action_extraction_prompt(self) -> str:
        """Build the prompt used for structured action extraction.

        Subclasses can override to customise the action-extraction prompt.
        """
        return (
            f"You are a {self.description}. "
            "Analyze the user's request and identify any actions to perform. "
            "Return all applicable actions."
        )

    def _extract_actions(self, action_plan: BaseModel) -> list[dict[str, Any]]:
        """Convert a Pydantic action plan into the list of UI action dicts.

        Subclasses must override this if they define an action schema.
        """
        return []
