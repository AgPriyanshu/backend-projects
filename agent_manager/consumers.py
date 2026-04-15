import json
from typing import Any, Literal, TypedDict, cast
from uuid import UUID

from asgiref.sync import sync_to_async
from asgiref.typing import WebSocketScope
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist
from langchain.messages import HumanMessage

from agent_manager.agents.main import Node, agent
from agent_manager.models import ChatSession, Message


class UrlRoute(TypedDict):
    args: tuple[str | int, ...]
    kwargs: dict[str, str | int | UUID]


class ChannelsWebSocketScope(WebSocketScope):
    user: Any
    url_route: UrlRoute


class ChatMessage(TypedDict):
    type: Literal["chat.message"]
    message: str


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

        self.group_name = f"chat-session-{self.session_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

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

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.message",
                "message_id": str(saved_message.id),
                "session_id": str(self.session_id),
                "message": saved_message.content,
                "user_id": saved_message.user_id,  # type: ignore
                "role": "user",
            },
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
            "active_node": Node.ORCHESTRATOR,
            "next_node": None,
            "final_response": "",
        }

        try:
            last_final_response = ""
            async for event in agent.astream_events(inputs, version="v2"):
                if event["event"] == "on_chat_model_stream":
                    chunk_content = event["data"]["chunk"].content
                    if chunk_content:
                        if not isinstance(chunk_content, str):
                            chunk_content = str(chunk_content)
                        full_content += chunk_content

                        await self.channel_layer.group_send(
                            self.group_name,
                            {
                                "type": "chat.message",
                                "message_id": str(saved_agent_message.id),
                                "session_id": str(self.session_id),
                                "message": chunk_content,
                                "user_id": saved_agent_message.user_id,  # type: ignore
                                "role": "assistant",
                                "isChunk": True,
                            },
                        )
                # Capture node state updates to get the final response if no streaming occurs
                elif event["event"] == "on_chain_end":
                    output = event["data"].get("output")
                    if isinstance(output, dict) and "final_response" in output:
                        if output["final_response"]:
                            last_final_response = output["final_response"]

            # If no tokens were streamed (e.g., fallback response from orchestrator), send the final response directly
            if not full_content and last_final_response:
                full_content = str(last_final_response)
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "chat.message",
                        "message_id": str(saved_agent_message.id),
                        "session_id": str(self.session_id),
                        "message": full_content,
                        "user_id": saved_agent_message.user_id,  # type: ignore
                        "role": "assistant",
                        "isChunk": True,
                    },
                )

        except Exception as e:
            print(e)
            error_msg = "I could not process your request right now."
            full_content += error_msg
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat.message",
                    "message_id": str(saved_agent_message.id),
                    "session_id": str(self.session_id),
                    "message": error_msg,
                    "user_id": saved_agent_message.user_id,  # type: ignore
                    "role": "assistant",
                    "isChunk": True,
                },
            )

        # Notify frontend stream is done, passing `isChunk: false` triggers finalization if needed, though we already updated store incrementally
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.message",
                "message_id": str(saved_agent_message.id),
                "session_id": str(self.session_id),
                "message": "",
                "user_id": saved_agent_message.user_id,  # type: ignore
                "role": "assistant",
                "isChunk": False,
            },
        )

        await self.update_message(saved_agent_message.id, full_content)

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "id": event["message_id"],
                    "session_id": event["session_id"],
                    "message": event["message"],
                    "user_id": event["user_id"],
                    "role": event["role"],
                    "isChunk": event.get("isChunk", False),
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
