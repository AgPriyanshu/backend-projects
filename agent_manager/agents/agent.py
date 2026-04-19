import asyncio
import operator
from enum import StrEnum
from typing import Annotated, TypedDict, cast

from langchain.messages import AnyMessage
from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, SecretStr

from .prompts import orchestrator_prompt, verifier_prompt, web_gis_prompt
from .schemas import UIAction, UIActionType
from .tools import geocode

llm = ChatOpenAI(
    model="Qwen/Qwen3-8B-AWQ",
    base_url="http://100.64.122.97:8080/v1",
    api_key=SecretStr("not-needed"),
)

llm_with_tools = llm.bind_tools([geocode])


class Node(StrEnum):
    ORCHESTRATOR = "orchestrator"
    WEB_GIS_EXPERT = "web_gis_expert"
    UI_EXPERT = "ui_expert"
    MAP_ZOOM_TO = "map_zoom_to"


class GlobalMessageState(TypedDict):
    session_id: str
    messages: Annotated[list[AnyMessage], operator.add]
    active_node: str
    prev_node: str | None
    next_node: str | None
    final_response: str | list[str | dict]
    ui_action: UIAction
    geocode_result: dict | None


def graph_router(state: GlobalMessageState) -> str:
    next_node = state.get("next_node")

    if next_node:
        return next_node

    return END


class RoutingDecision(BaseModel):
    next_node: str | None
    response: str


async def orchestrator_node(state: GlobalMessageState):
    if state.get("prev_node") in (Node.WEB_GIS_EXPERT, Node.UI_EXPERT, Node.MAP_ZOOM_TO):
        verifier_chain = verifier_prompt | llm

        verified = await verifier_chain.ainvoke({"messages": state["messages"]})
        assert isinstance(verified.content, str)

        return {
            "prev_node": Node.ORCHESTRATOR,
            "next_node": None,
            "final_response": verified.content,
        }

    orchestrator_chain = orchestrator_prompt | llm.with_structured_output(
        RoutingDecision
    )

    decision = cast(
        RoutingDecision,
        await orchestrator_chain.ainvoke({"messages": state["messages"]}),
    )

    return {
        "prev_node": Node.ORCHESTRATOR,
        "next_node": decision.next_node,
        "final_response": decision.response,
    }


async def web_gis_expert(state: GlobalMessageState):
    messages = list(state["messages"])
    last_geocode_result: dict | None = None

    while True:
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


graph = StateGraph(GlobalMessageState)

# Nodes.
graph.add_node(Node.ORCHESTRATOR, orchestrator_node)
graph.add_node(Node.WEB_GIS_EXPERT, web_gis_expert)
graph.add_node(Node.UI_EXPERT, ui_expert)
graph.add_node(Node.MAP_ZOOM_TO, map_zoom_to_node)

# Edges.
graph.add_edge(START, Node.ORCHESTRATOR)
graph.add_conditional_edges(
    Node.ORCHESTRATOR,
    graph_router,
    {Node.WEB_GIS_EXPERT: Node.WEB_GIS_EXPERT, END: END},
)
graph.add_edge(Node.WEB_GIS_EXPERT, Node.UI_EXPERT)
graph.add_conditional_edges(
    Node.UI_EXPERT,
    graph_router,
    {Node.MAP_ZOOM_TO: Node.MAP_ZOOM_TO, Node.ORCHESTRATOR: Node.ORCHESTRATOR},
)
graph.add_edge(Node.MAP_ZOOM_TO, Node.ORCHESTRATOR)

agent_new = graph.compile()
