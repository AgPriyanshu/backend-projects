import asyncio
from typing import cast

from django.conf import settings
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import SecretStr, ValidationError

from .prompts import orchestrator_prompt, verifier_prompt, web_gis_prompt
from .schemas import GlobalMessageState, Node, RoutingDecision, UIActionType
from .tools import geocode

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
        model_kwargs={"max_tokens": config["MAX_TOKENS"]},
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
llm_with_tools = llm.bind_tools([geocode])


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
        # Structured output parsing failed — fall back to a direct response without routing.
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


async def web_gis_expert(state: GlobalMessageState):
    messages = list(_trim(state["messages"]))
    last_geocode_result: dict | None = None
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
            result = await asyncio.to_thread(geocode.invoke, tool_call["args"])
            last_geocode_result = result
            messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_call["id"])
            )

    return {
        "prev_node": Node.WEB_GIS_EXPERT,
        "messages": [messages[-1]],
        "geocode_result": last_geocode_result,
    }


def ui_expert(state: GlobalMessageState):
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


graph_builder = StateGraph(GlobalMessageState)

graph_builder.add_node(Node.ORCHESTRATOR, orchestrator_node)
graph_builder.add_node(Node.WEB_GIS_EXPERT, web_gis_expert)
graph_builder.add_node(Node.UI_EXPERT, ui_expert)
graph_builder.add_node(Node.MAP_ZOOM_TO, map_zoom_to_node)

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
    {Node.MAP_ZOOM_TO: Node.MAP_ZOOM_TO, Node.ORCHESTRATOR: Node.ORCHESTRATOR},
)
graph_builder.add_edge(Node.MAP_ZOOM_TO, Node.ORCHESTRATOR)

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
