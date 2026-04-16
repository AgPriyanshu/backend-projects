import operator
from enum import StrEnum
from typing import Annotated, Literal, TypedDict

from langchain.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

llm = ChatOllama(
    model="qwen3:4b-instruct",
    base_url="http://100.64.122.97:11434",
)


class Node(StrEnum):
    ORCHESTRATOR = "orchestrator"
    WEB_GIS_EXPERT = "web_gis_expert"
    NOTE_EXPERT = "node_expert"


class WebGISAction(BaseModel):
    action_type: Literal["load_dataset", "remove_layer", "fit_to_layer", "none"]
    dataset_name: str | None = None


class WebGISActionPlan(BaseModel):
    actions: list[WebGISAction]


class GlobalMessageState(TypedDict):
    session_id: str
    messages: Annotated[list[AnyMessage], operator.add]
    active_node: Node
    next_node: Node | None
    final_response: str
    ui_actions: list[dict]


class WebGISMessageState(TypedDict):
    query: str
    response: str
    active_node: Node
    next_node: Node | None
    ui_actions: list[dict]


def get_latest_human_message(messages: list[AnyMessage]) -> HumanMessage:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message

    raise ValueError("A human message is required.")


class OrchestratorOutput(TypedDict):
    next_node: Node


def orchestrator_node(state: GlobalMessageState):
    question = get_latest_human_message(state["messages"]).content

    if not isinstance(question, str):
        question = str(question)

    response = llm.with_structured_output(OrchestratorOutput).invoke(
        [
            SystemMessage(
                content=(
                    "You are an orchestrator that routes user queries to the correct expert agent.\n\n"
                    "Available agents:\n"
                    f"- {Node.WEB_GIS_EXPERT}: Handles questions about maps, geospatial data, GIS layers, "
                    "raster/vector datasets, tile rendering, and any Web GIS functionality.\n"
                    f"- {Node.NOTE_EXPERT}: Handles note-taking requests, grammar fixes, and rephrasing of user notes.\n\n"
                    "Respond with the name of the agent best suited to handle the user's query."
                )
            ),
            question,
        ]
    )

    return response


def build_web_gis_state(state: GlobalMessageState) -> WebGISMessageState:
    question = get_latest_human_message(state["messages"]).content

    if not isinstance(question, str):
        question = str(question)

    return {
        "query": question,
        "response": "",
        "active_node": Node.WEB_GIS_EXPERT,
        "next_node": None,
        "ui_actions": [],
    }


async def web_gis_expert_node(state: WebGISMessageState) -> WebGISMessageState:
    question = state["query"]

    action_plan: WebGISActionPlan = llm.with_structured_output(WebGISActionPlan).invoke(  # type: ignore[assignment]
        [
            SystemMessage(
                content=(
                    "You are a Web GIS assistant. Analyze the user's request and identify any map actions to perform.\n\n"
                    "Available actions:\n"
                    "- load_dataset: User wants to load/show/display a dataset on the map. Extract the dataset_name.\n"
                    "- remove_layer: User wants to remove/hide a layer from the map. Extract the dataset_name.\n"
                    "- fit_to_layer: User wants to zoom or fit the map to a specific layer. Extract the dataset_name.\n"
                    "- none: The request is purely informational — no map action needed.\n\n"
                    "Return all applicable actions. Use 'none' only when no map action is requested."
                )
            ),
            HumanMessage(content=question),
        ]
    )

    ui_actions = [
        action.model_dump()
        for action in action_plan.actions
        if action.action_type != "none"
    ]

    expert_response = ""
    async for chunk in llm.astream(
        [
            SystemMessage(
                content=(
                    "You are a Web GIS expert. Answer only the user's Web GIS "
                    "question with a concise, accurate explanation."
                )
            ),
            HumanMessage(content=question),
        ]
    ):
        expert_response += chunk.content or ""

    return {
        "active_node": Node.WEB_GIS_EXPERT,
        "next_node": None,
        "query": question,
        "response": expert_response,
        "ui_actions": ui_actions,
    }


async def note_taker_expert(state: GlobalMessageState):
    question = get_latest_human_message(state["messages"])

    expert_response = ""
    async for chunk in llm.astream(
        [
            SystemMessage(
                content=(
                    "You are a Note taker expert and you fix the grammar and rephrase the user note"
                )
            ),
            HumanMessage(content=question.content),
        ]
    ):
        expert_response += chunk.content or ""

    return {"messages": [AIMessage(content=expert_response)]}


async def web_gis_expert_entry_node(state: GlobalMessageState) -> dict:
    web_gis_state = build_web_gis_state(state)
    web_gis_result = await web_gis_expert_node(web_gis_state)
    final_response = web_gis_result["response"]

    return {
        "active_node": web_gis_result["active_node"],
        "next_node": web_gis_result["next_node"],
        "final_response": final_response,
        "ui_actions": web_gis_result["ui_actions"],
        "messages": [AIMessage(content=final_response)],
    }


def graph_router(state: GlobalMessageState) -> str:
    next_node = state["next_node"]

    if next_node == Node.WEB_GIS_EXPERT:
        return Node.WEB_GIS_EXPERT
    elif next_node == Node.NOTE_EXPERT:
        return Node.NOTE_EXPERT

    return END


graph = StateGraph(GlobalMessageState)

graph.add_node(Node.ORCHESTRATOR, orchestrator_node)
graph.add_node(Node.WEB_GIS_EXPERT, web_gis_expert_entry_node)
graph.add_node(Node.NOTE_EXPERT, note_taker_expert)

graph.add_edge(START, Node.ORCHESTRATOR)
graph.add_conditional_edges(
    Node.ORCHESTRATOR,
    graph_router,
    {
        Node.WEB_GIS_EXPERT: Node.WEB_GIS_EXPERT,
        Node.NOTE_EXPERT: Node.NOTE_EXPERT,
        END: END,
    },
)
graph.add_edge(Node.WEB_GIS_EXPERT, END)
graph.add_edge(Node.NOTE_EXPERT, END)

agent = graph.compile()


if __name__ == "__main__":
    import asyncio

    # query = input("User Query")
    print(
        asyncio.run(
            agent.ainvoke(
                {
                    "session_id": "12312312312",
                    "messages": [
                        HumanMessage(content="hello tell me about note taking")
                    ],
                    "active_node": Node.ORCHESTRATOR,
                    "next_node": None,
                    "final_response": "",
                    "ui_actions": [],
                }
            )
        )
    )
