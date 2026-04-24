import asyncio
from typing import Any, cast

from django.conf import settings
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import SecretStr, ValidationError

from .prompts import orchestrator_prompt, verifier_prompt, web_gis_prompt
from .schemas import GlobalMessageState, Node, RoutingDecision, UIActionType
from .tools import (
    geocode,
    list_loaded_vector_layers,
    list_processing_tools,
    open_processing_tool,
)

MAX_CONTEXT_MESSAGES = 20
MAX_TOOL_ITERATIONS = 5


def _build_llm() -> ChatOpenAI:
    config = settings.LLM_SERVER_CONFIG

    return ChatOpenAI(
        model=config["DEFAULT_MODEL"],
        base_url=config["BASE_URL"],
        api_key=SecretStr("not-needed"),
        timeout=config["TIMEOUT"],
        temperature=config["TEMPERATURE"],
        max_tokens=config["MAX_TOKENS"],
    )


def _build_pg_conn_string() -> str:
    db = settings.DATABASES["default"]

    return (
        f"postgresql://{db['USER']}:{db['PASSWORD']}"
        f"@{db['HOST']}:{db['PORT']}/{db['NAME']}"
    )


def _trim(messages: list) -> list:
    """Keep only the last MAX_CONTEXT_MESSAGES to avoid context window overflow."""
    return messages[-MAX_CONTEXT_MESSAGES:]


llm = _build_llm()

_TOOLS = [
    geocode,
    list_loaded_vector_layers,
    list_processing_tools,
    open_processing_tool,
]
_TOOLS_BY_NAME = {t.name: t for t in _TOOLS}

llm_with_tools = llm.bind_tools(_TOOLS)


def graph_router(state: GlobalMessageState) -> str:
    next_node = state.get("next_node")

    if next_node:
        return next_node

    return END


async def orchestrator_node(state: GlobalMessageState):
    messages = _trim(state["messages"])

    if state.get("prev_node") in (
        Node.WEB_GIS_EXPERT,
        Node.UI_EXPERT,
        Node.MAP_ZOOM_TO,
        Node.OPEN_PROCESSING_TOOL,
    ):
        verifier_chain = verifier_prompt | llm
        verified = await verifier_chain.ainvoke({"messages": messages})
        assert isinstance(verified.content, str)

        return {
            "prev_node": Node.ORCHESTRATOR,
            "next_node": None,
            "final_response": verified.content,
        }

    orchestrator_chain = orchestrator_prompt | llm.with_structured_output(
        RoutingDecision
    )

    try:
        decision = cast(
            RoutingDecision,
            await orchestrator_chain.ainvoke({"messages": messages}),
        )
    except (ValidationError, OutputParserException, Exception):
        fallback = await (orchestrator_prompt | llm).ainvoke({"messages": messages})
        fallback_content = fallback.content if isinstance(fallback.content, str) else ""

        return {
            "prev_node": Node.ORCHESTRATOR,
            "next_node": None,
            "final_response": fallback_content or "I could not process your request.",
        }

    return {
        "prev_node": Node.ORCHESTRATOR,
        "next_node": decision.next_node,
        "final_response": decision.response,
    }


async def _invoke_tool(tool_call: dict, state: GlobalMessageState) -> Any:
    """Invoke a registered tool, injecting state where needed."""
    tool_name = tool_call["name"]
    tool = _TOOLS_BY_NAME.get(tool_name)

    if tool is None:
        return {"error": f"Unknown tool: {tool_name}"}

    args = dict(tool_call.get("args") or {})

    # list_loaded_vector_layers reads from InjectedState; LangGraph injects it
    # automatically when we pass the state via ToolNode, but we invoke manually
    # here, so merge the state dict ourselves for tools that declare it.
    if tool_name == list_loaded_vector_layers.name:
        args["state"] = dict(state)

    return await asyncio.to_thread(tool.invoke, args)


async def web_gis_expert(state: GlobalMessageState):
    messages = list(_trim(state["messages"]))
    last_geocode_result: dict | None = None
    pending_processing_tool: dict | None = None
    iterations = 0

    while iterations < MAX_TOOL_ITERATIONS:
        iterations += 1
        response = await (web_gis_prompt | llm_with_tools).ainvoke(
            {"messages": messages}
        )
        messages.append(response)

        if not response.tool_calls:
            break

        for tool_call in response.tool_calls:
            result = await _invoke_tool(tool_call, state)

            if tool_call["name"] == geocode.name and isinstance(result, dict):
                last_geocode_result = result

            if tool_call["name"] == open_processing_tool.name and isinstance(
                result, dict
            ):
                pending_processing_tool = result

            messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_call["id"])
            )

    return {
        "prev_node": Node.WEB_GIS_EXPERT,
        "messages": [messages[-1]],
        "geocode_result": last_geocode_result,
        "pending_processing_tool": pending_processing_tool,
    }


def ui_expert(state: GlobalMessageState):
    if state.get("pending_processing_tool"):
        return {
            "prev_node": Node.UI_EXPERT,
            "next_node": Node.OPEN_PROCESSING_TOOL,
        }

    geocode_result = state.get("geocode_result")

    if geocode_result and "latitude" in geocode_result:
        return {"prev_node": Node.UI_EXPERT, "next_node": Node.MAP_ZOOM_TO}

    return {"prev_node": Node.UI_EXPERT, "next_node": Node.ORCHESTRATOR}


def map_zoom_to_node(state: GlobalMessageState):
    result = state["geocode_result"]
    assert result is not None

    return {
        "prev_node": Node.MAP_ZOOM_TO,
        "next_node": Node.ORCHESTRATOR,
        "ui_action": {
            "app": "web_gis",
            "type": UIActionType.MAP_ZOOM_TO,
            "payload": {
                "latitude": result["latitude"],
                "longitude": result["longitude"],
            },
        },
    }


def open_processing_tool_node(state: GlobalMessageState):
    pending = state.get("pending_processing_tool")
    assert pending is not None

    payload: dict[str, Any] = {
        "tool_name": pending["tool_name"],
        "defaults": pending.get("defaults") or {},
    }

    if pending.get("output_name"):
        payload["output_name"] = pending["output_name"]

    return {
        "prev_node": Node.OPEN_PROCESSING_TOOL,
        "next_node": Node.ORCHESTRATOR,
        "ui_action": {
            "app": "web_gis",
            "type": UIActionType.OPEN_PROCESSING_TOOL,
            "payload": payload,
        },
    }


graph_builder = StateGraph(GlobalMessageState)

graph_builder.add_node(Node.ORCHESTRATOR, orchestrator_node)
graph_builder.add_node(Node.WEB_GIS_EXPERT, web_gis_expert)
graph_builder.add_node(Node.UI_EXPERT, ui_expert)
graph_builder.add_node(Node.MAP_ZOOM_TO, map_zoom_to_node)
graph_builder.add_node(Node.OPEN_PROCESSING_TOOL, open_processing_tool_node)

graph_builder.add_edge(START, Node.ORCHESTRATOR)
graph_builder.add_conditional_edges(
    Node.ORCHESTRATOR,
    graph_router,
    {Node.WEB_GIS_EXPERT: Node.WEB_GIS_EXPERT, END: END},
)
graph_builder.add_edge(Node.WEB_GIS_EXPERT, Node.UI_EXPERT)
graph_builder.add_conditional_edges(
    Node.UI_EXPERT,
    graph_router,
    {
        Node.MAP_ZOOM_TO: Node.MAP_ZOOM_TO,
        Node.OPEN_PROCESSING_TOOL: Node.OPEN_PROCESSING_TOOL,
        Node.ORCHESTRATOR: Node.ORCHESTRATOR,
    },
)
graph_builder.add_edge(Node.MAP_ZOOM_TO, Node.ORCHESTRATOR)
graph_builder.add_edge(Node.OPEN_PROCESSING_TOOL, Node.ORCHESTRATOR)

agent_instance = None
agent_lock = asyncio.Lock()


async def get_agent():
    """Return the compiled graph with a Postgres checkpointer (lazy singleton).

    Falls back to MemorySaver if langgraph-checkpoint-postgres is not installed.
    To install: docker compose exec web pip install langgraph-checkpoint-postgres
    """
    global agent_instance

    if agent_instance is not None:
        return agent_instance

    async with agent_lock:
        if agent_instance is not None:
            return agent_instance

        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            checkpointer = await AsyncPostgresSaver.from_conn_string(
                _build_pg_conn_string()
            )
            await checkpointer.setup()
            agent_instance = graph_builder.compile(checkpointer=checkpointer)
        except ImportError:
            from langgraph.checkpoint.memory import MemorySaver

            agent_instance = graph_builder.compile(checkpointer=MemorySaver())

    return agent_instance
