import json
from typing import Any, TypedDict, cast
from uuid import UUID

from asgiref.sync import sync_to_async
from asgiref.typing import WebSocketScope
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist
from langchain.messages import HumanMessage

from .agents.agent import Node, agent_new
from .constants import Role
from .models import ChatSession, Message


class UrlRoute(TypedDict):
    args: tuple[str | int, ...]
    kwargs: dict[str, str | int | UUID]


class ChannelsWebSocketScope(WebSocketScope):
    user: Any
    url_route: UrlRoute


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        scope: ChannelsWebSocketScope = self.scope  # type: ignore
        user = scope.get("user")
        url_route = scope.get("url_route")

        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return

        if url_route is None:
            await self.close(code=4400)
            return

        session_id = url_route.get("kwargs", {}).get("session_id")

        if not isinstance(session_id, (str, UUID)):
            await self.close(code=4400)
            return

        self.user = cast(Any, user)
        self.session_id = str(session_id)
        self.chat_session = await self.get_chat_session(self.session_id, self.user.id)

        if self.chat_session is None:
            await self.close(code=4404)
            return

        await self.accept()

    async def receive(self, text_data):
        try:
            payload = json.loads(text_data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON payload."}))
            return

        message = payload.get("message", "").strip()

        if not message:
            await self.send(
                text_data=json.dumps({"error": "Message content is required."})
            )
            return

        saved_message = await self.create_message(
            session_id=self.session_id,
            user_id=self.user.id,
            content=message,
        )

        await self._send_message(
            message_id=str(saved_message.id),
            role=Role.USER,
            content=saved_message.content,
        )

        saved_agent_message = await self.create_message(
            session_id=self.session_id,
            user_id=self.chat_session.user_id,
            content="",
        )

        full_content = ""

        inputs = {
            "session_id": self.session_id,
            "messages": [HumanMessage(content=message)],
            "active_node": Node,
            "next_node": None,
            "final_response": "",
        }

        try:
            last_final_response = ""
            last_ui_action = None

            async for event in agent_new.astream_events(inputs, version="v2"):
                if (
                    event["event"] == "on_chat_model_stream"
                    and event.get("metadata", {}).get("langgraph_node")
                    != Node.ORCHESTRATOR
                ):
                    chunk_content = event["data"]["chunk"].content

                    if chunk_content:
                        if not isinstance(chunk_content, str):
                            chunk_content = str(chunk_content)

                        full_content += chunk_content

                        await self._send_message(
                            message_id=str(saved_agent_message.id),
                            role=Role.ASSISTANT,
                            content=chunk_content,
                            is_chunk=True,
                        )

                # Capture node state updates to get the final response and ui_action.
                elif event["event"] == "on_chain_end":
                    output = event["data"].get("output")

                    if isinstance(output, dict):
                        if output.get("final_response"):
                            last_final_response = output["final_response"]
                        if output.get("ui_action"):
                            last_ui_action = output["ui_action"]

            # If no tokens were streamed (e.g., fallback response from orchestrator), send the final response directly.
            if not full_content and last_final_response:
                full_content = str(last_final_response)

                await self._send_message(
                    message_id=str(saved_agent_message.id),
                    role=Role.ASSISTANT,
                    content=full_content,
                    is_chunk=True,
                )

        except Exception as e:
            import logging

            logging.getLogger(__name__).exception("Agent stream error: %s", e)

            await self._send_message(
                message_id=str(saved_agent_message.id),
                role=Role.ASSISTANT,
                content="I could not process your request right now.",
                is_chunk=True,
            )

        # Notify frontend the stream is done.
        await self._send_message(
            message_id=str(saved_agent_message.id),
            role=Role.ASSISTANT,
            content="",
            is_chunk=False,
        )

        if last_ui_action:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "ui_action",
                        "session_id": self.session_id,
                        "actions": [
                            {
                                "app": last_ui_action["app"],
                                "action_type": last_ui_action["type"],
                                "payload": last_ui_action["payload"],
                            }
                        ],
                    }
                )
            )

        await self.update_message(saved_agent_message.id, full_content)

    async def _send_message(
        self,
        message_id: str,
        role: Role,
        content: str,
        is_chunk: bool = False,
    ):
        await self.send(
            text_data=json.dumps(
                {
                    "id": message_id,
                    "session_id": self.session_id,
                    "message": content,
                    "user_id": str(self.user.id),
                    "role": role,
                    "isChunk": is_chunk,
                }
            )
        )

    @sync_to_async
    def get_chat_session(self, session_id, user_id):
        try:
            return ChatSession.objects.get(id=session_id, user_id=user_id)
        except ObjectDoesNotExist:
            return None

    @sync_to_async
    def create_message(self, session_id, user_id, content):
        return Message.objects.create(
            session_id=session_id,
            user_id=user_id,
            content=content,
        )

    @sync_to_async
    def update_message(self, message_id, content):
        Message.objects.filter(id=message_id).update(content=content)
