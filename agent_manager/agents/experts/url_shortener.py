from typing import Any, Literal

from pydantic import BaseModel

from agent_manager.agents.base import BaseExpert
from agent_manager.agents.registry import ExpertRegistry

# ---------------------------------------------------------------------------
# Action schemas
# ---------------------------------------------------------------------------

class URLShortenerAction(BaseModel):
    action_type: Literal["shorten_url", "list_urls", "none"]
    url: str | None = None


class URLShortenerActionPlan(BaseModel):
    actions: list[URLShortenerAction]


# ---------------------------------------------------------------------------
# Expert
# ---------------------------------------------------------------------------

class URLShortenerExpert(BaseExpert):
    """Expert for URL shortening operations."""

    @property
    def name(self) -> str:
        return "url_shortener"

    @property
    def description(self) -> str:
        return (
            "Handles URL shortening — creating short URLs from long URLs "
            "and listing previously shortened URLs."
        )

    @property
    def system_prompt(self) -> str:
        return (
            "You are a URL shortening assistant. "
            "Help the user shorten URLs and manage their short links with concise responses."
        )

    def get_action_schema(self) -> type[BaseModel]:
        return URLShortenerActionPlan

    def _build_action_extraction_prompt(self) -> str:
        return (
            "You are a URL shortening assistant. Analyze the user's request.\n\n"
            "Available actions:\n"
            "- shorten_url: User wants to shorten a URL. Extract the full URL.\n"
            "- list_urls: User wants to see their shortened URLs.\n"
            "- none: The request is purely informational — no URL action needed.\n\n"
            "Return all applicable actions. Use 'none' only when no URL action is requested."
        )

    def _extract_actions(self, action_plan: BaseModel) -> list[dict[str, Any]]:
        if not isinstance(action_plan, URLShortenerActionPlan):
            return []

        return [
            {
                "app": self.name,
                "action_type": action.action_type,
                "payload": {"url": action.url},
            }
            for action in action_plan.actions
            if action.action_type != "none"
        ]


# Auto-register on import.
ExpertRegistry.register(URLShortenerExpert())
