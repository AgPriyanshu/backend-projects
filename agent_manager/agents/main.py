import operator
from enum import StrEnum
from typing import Annotated, TypedDict

from langchain.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

llm = ChatOllama(
    model="qwen3:4b",
    base_url="http://host.docker.internal:11434",
)


class Node(StrEnum):
    ORCHESTRATOR = "orchestrator"
    WEB_GIS_EXPERT = "web_gis_expert"
    NOTE_EXPERT = "node_expert"


class UIState(TypedDict):
    current_app: str
    actions: dict


class GlobalMessageState(TypedDict):
    session_id: str
    messages: Annotated[list[AnyMessage], operator.add]
    active_node: Node
    next_node: Node | None
    final_response: str
    ui: UIState


class WebGISMessageState(TypedDict):
    query: str
    response: str
    active_node: Node
    next_node: Node | None


def get_latest_human_message(messages: list[AnyMessage]) -> HumanMessage:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message

    raise ValueError("A human message is required.")


def orchestrator_node(state: GlobalMessageState) -> dict:
    question = get_latest_human_message(state["messages"]).content

    if not isinstance(question, str):
        question = str(question)

    if "web gis" in question.lower() or "gis" in question.lower():
        return {
            "active_node": Node.ORCHESTRATOR,
            "next_node": Node.WEB_GIS_EXPERT,
        }

    elif any(word in question.lower() for word in ["note", "todo"]):
        return {"active_node": Node.ORCHESTRATOR, "next_node": Node.NOTE_EXPERT}

    fallback_response = (
        "I can only answer Web GIS questions and Note taking questions in this graph."
    )

    return {
        "active_node": Node.ORCHESTRATOR,
        "next_node": None,
        "final_response": fallback_response,
        "messages": [AIMessage(content=fallback_response)],
    }


def build_web_gis_state(state: GlobalMessageState) -> WebGISMessageState:
    question = get_latest_human_message(state["messages"]).content

    if not isinstance(question, str):
        question = str(question)

    return {
        "query": question,
        "response": "",
        "active_node": Node.WEB_GIS_EXPERT,
        "next_node": None,
    }


async def web_gis_expert_node(state: WebGISMessageState) -> WebGISMessageState:
    question = state["query"]

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

    final_response = expert_response

    return {
        "active_node": Node.WEB_GIS_EXPERT,
        "next_node": None,
        "query": question,
        "response": final_response,
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

    return {"messages": AIMessage(content=expert_response)}


async def web_gis_expert_entry_node(state: GlobalMessageState) -> dict:
    web_gis_state = build_web_gis_state(state)
    web_gis_result = await web_gis_expert_node(web_gis_state)
    final_response = web_gis_result["response"]

    return {
        "active_node": web_gis_result["active_node"],
        "next_node": web_gis_result["next_node"],
        "final_response": final_response,
        "messages": [AIMessage(content=final_response)],
    }


def graph_router(state: GlobalMessageState) -> str:
    if state["next_node"]:
        return Node.WEB_GIS_EXPERT
    elif state["next_node"]:
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
