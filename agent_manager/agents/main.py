import operator
from typing import Annotated, TypedDict

from langchain.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

import agent_manager.agents.experts.notes  # noqa: F401
import agent_manager.agents.experts.todo  # noqa: F401
import agent_manager.agents.experts.url_shortener  # noqa: F401

# ---------------------------------------------------------------------------
# Import all experts so they auto-register with ExpertRegistry.
# ---------------------------------------------------------------------------
import agent_manager.agents.experts.web_gis  # noqa: F401
from agent_manager.agents.registry import ExpertRegistry

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

llm = ChatOllama(
    model="qwen3:4b-instruct",
    base_url="http://100.64.122.97:11434",
)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class GlobalMessageState(TypedDict):
    session_id: str
    messages: Annotated[list[AnyMessage], operator.add]
    active_node: str
    next_node: str | None
    final_response: str
    ui_actions: list[dict]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_latest_human_message(messages: list[AnyMessage]) -> HumanMessage:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message

    raise ValueError("A human message is required.")


# ---------------------------------------------------------------------------
# Orchestrator node
# ---------------------------------------------------------------------------

class OrchestratorOutput(TypedDict):
    next_node: str


def orchestrator_node(state: GlobalMessageState):
    question = get_latest_human_message(state["messages"]).content

    if not isinstance(question, str):
        question = str(question)

    prompt = ExpertRegistry.build_orchestrator_prompt()

    response = llm.with_structured_output(OrchestratorOutput).invoke(
        [
            SystemMessage(content=prompt),
            question,
        ]
    )

    return response


# ---------------------------------------------------------------------------
# Generic expert entry node factory
# ---------------------------------------------------------------------------

def make_expert_entry_node(expert_name: str):
    """Create a LangGraph node function for a registered expert."""

    async def expert_entry_node(state: GlobalMessageState) -> dict:
        expert = ExpertRegistry.get(expert_name)

        if expert is None:
            return {
                "active_node": expert_name,
                "next_node": None,
                "final_response": "I could not find the right expert for your request.",
                "ui_actions": [],
                "messages": [
                    AIMessage(
                        content="I could not find the right expert for your request."
                    )
                ],
            }

        question = get_latest_human_message(state["messages"]).content

        if not isinstance(question, str):
            question = str(question)

        result = await expert.execute(query=question, llm=llm)

        return {
            "active_node": expert_name,
            "next_node": None,
            "final_response": result.response,
            "ui_actions": result.ui_actions,
            "messages": [AIMessage(content=result.response)],
        }

    return expert_entry_node


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def graph_router(state: GlobalMessageState) -> str:
    next_node = state.get("next_node")

    if next_node and ExpertRegistry.get(next_node) is not None:
        return next_node

    return END


# ---------------------------------------------------------------------------
# Build the graph dynamically from the registry
# ---------------------------------------------------------------------------

ORCHESTRATOR_NODE = "orchestrator"

graph = StateGraph(GlobalMessageState)
graph.add_node(ORCHESTRATOR_NODE, orchestrator_node)

# Add an edge from START → orchestrator.
graph.add_edge(START, ORCHESTRATOR_NODE)

# Dynamically add expert nodes and conditional edges.
conditional_map: dict[str, str] = {END: END}

for expert in ExpertRegistry.all_experts():
    node_fn = make_expert_entry_node(expert.name)
    graph.add_node(expert.name, node_fn)
    graph.add_edge(expert.name, END)
    conditional_map[expert.name] = expert.name

graph.add_conditional_edges(ORCHESTRATOR_NODE, graph_router, conditional_map)

agent = graph.compile()


# ---------------------------------------------------------------------------
# For backwards compatibility, expose the Node names used by consumers.py.
# ---------------------------------------------------------------------------

# The orchestrator node name (used in consumers.py for initial state).
Node = type("Node", (), {"ORCHESTRATOR": ORCHESTRATOR_NODE})


if __name__ == "__main__":
    import asyncio

    print(
        asyncio.run(
            agent.ainvoke(
                {
                    "session_id": "12312312312",
                    "messages": [
                        HumanMessage(content="hello tell me about note taking")
                    ],
                    "active_node": ORCHESTRATOR_NODE,
                    "next_node": None,
                    "final_response": "",
                    "ui_actions": [],
                }
            )
        )
    )
