from typing import Any, Literal

from pydantic import BaseModel

from agent_manager.agents.base import BaseExpert
from agent_manager.agents.registry import ExpertRegistry

# ---------------------------------------------------------------------------
# Action schemas
# ---------------------------------------------------------------------------

class NoteAction(BaseModel):
    action_type: Literal["create_note", "grammar_check", "list_notes", "none"]
    content: str | None = None
    note_id: str | None = None


class NoteActionPlan(BaseModel):
    actions: list[NoteAction]


# ---------------------------------------------------------------------------
# Expert
# ---------------------------------------------------------------------------

class NoteExpert(BaseExpert):
    """Expert for note-taking and grammar checking."""

    @property
    def name(self) -> str:
        return "notes"

    @property
    def description(self) -> str:
        return (
            "Handles note-taking requests, grammar fixes, rephrasing of user notes, "
            "and listing or managing markdown notes."
        )

    @property
    def system_prompt(self) -> str:
        return (
            "You are a note-taking expert. Help the user create, manage, and improve "
            "their notes. Fix grammar and rephrase when asked."
        )

    def get_action_schema(self) -> type[BaseModel]:
        return NoteActionPlan

    def _build_action_extraction_prompt(self) -> str:
        return (
            "You are a note-taking assistant. Analyze the user's request.\n\n"
            "Available actions:\n"
            "- create_note: User wants to create or save a new note. Extract the note content.\n"
            "- grammar_check: User wants grammar checking or rephrasing on a note. Extract the note_id if mentioned.\n"
            "- list_notes: User wants to see their notes.\n"
            "- none: The request is purely informational — no note action needed.\n\n"
            "Return all applicable actions. Use 'none' only when no note action is requested."
        )

    def _extract_actions(self, action_plan: BaseModel) -> list[dict[str, Any]]:
        if not isinstance(action_plan, NoteActionPlan):
            return []

        return [
            {
                "app": self.name,
                "action_type": action.action_type,
                "payload": {
                    "content": action.content,
                    "note_id": action.note_id,
                },
            }
            for action in action_plan.actions
            if action.action_type != "none"
        ]


# Auto-register on import.
ExpertRegistry.register(NoteExpert())
