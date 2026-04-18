from typing import Any, Literal

from pydantic import BaseModel

from agent_manager.agents.base import BaseExpert
from agent_manager.agents.registry import ExpertRegistry

# ---------------------------------------------------------------------------
# Action schemas
# ---------------------------------------------------------------------------

class TodoAction(BaseModel):
    action_type: Literal[
        "create_task", "complete_task", "delete_task", "list_tasks", "none"
    ]
    description: str | None = None
    task_id: str | None = None


class TodoActionPlan(BaseModel):
    actions: list[TodoAction]


# ---------------------------------------------------------------------------
# Expert
# ---------------------------------------------------------------------------

class TodoExpert(BaseExpert):
    """Expert for task / todo management."""

    @property
    def name(self) -> str:
        return "todo"

    @property
    def description(self) -> str:
        return (
            "Handles task and todo management — creating, completing, deleting, "
            "and listing tasks or to-do items."
        )

    @property
    def system_prompt(self) -> str:
        return (
            "You are a helpful task management assistant. "
            "Help the user manage their to-do list with concise, friendly responses."
        )

    def get_action_schema(self) -> type[BaseModel]:
        return TodoActionPlan

    def _build_action_extraction_prompt(self) -> str:
        return (
            "You are a task management assistant. Analyze the user's request and identify any task actions.\n\n"
            "Available actions:\n"
            "- create_task: User wants to add a new task. Extract the task description.\n"
            "- complete_task: User wants to mark a task as done. Extract the task description or identifier.\n"
            "- delete_task: User wants to remove a task. Extract the task description or identifier.\n"
            "- list_tasks: User wants to see their tasks.\n"
            "- none: The request is purely informational — no task action needed.\n\n"
            "Return all applicable actions. Use 'none' only when no task action is requested."
        )

    def _extract_actions(self, action_plan: BaseModel) -> list[dict[str, Any]]:
        if not isinstance(action_plan, TodoActionPlan):
            return []

        return [
            {
                "app": self.name,
                "action_type": action.action_type,
                "payload": {
                    "description": action.description,
                    "task_id": action.task_id,
                },
            }
            for action in action_plan.actions
            if action.action_type != "none"
        ]


# Auto-register on import.
ExpertRegistry.register(TodoExpert())
