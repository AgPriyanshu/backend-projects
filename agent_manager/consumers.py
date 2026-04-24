import asyncio
import json
import logging
from typing import Any, TypedDict, cast
from uuid import UUID

from asgiref.sync import sync_to_async
from asgiref.typing import WebSocketScope
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from langchain.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from .agents.agent import Node, get_agent
from .constants import Role
from .models import ChatSession, Message, MessageRole, MessageStatus

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4000
AGENT_LOCK_TIMEOUT = 120
GRAPH_TURN_TIMEOUT = 60
CHUNK_SAVE_INTERVAL = 25


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

    async def disconnect(self, _close_code):
        # Release any held session lock if the connection drops mid-stream.
        if hasattr(self, "session_id"):
            await sync_to_async(cache.delete)(f"agent:lock:{self.session_id}")

    async def receive(self, text_data):
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON payload."}))
            return

        message = payload.get("message", "").strip()

        if not message:
            await self.send(text_data=json.dumps({"error": "Message content is required."}))
            return

        loaded_layers = self._parse_loaded_layers(payload.get("context"))

        if len(message) > MAX_MESSAGE_LENGTH:
            await self.send(
                text_data=json.dumps({"error": f"Message exceeds {MAX_MESSAGE_LENGTH} character limit."})
            )
            return

        # Deduplicate retried messages from reconnecting clients.
        client_message_id = payload.get("message_id")

        if client_message_id:
            dedup_key = f"agent:dedup:{client_message_id}"
            is_new = await sync_to_async(cache.add)(dedup_key, "1", timeout=300)

            if not is_new:
                return

        # Prevent concurrent graph runs for the same session.
        lock_key = f"agent:lock:{self.session_id}"
        acquired = await sync_to_async(cache.add)(lock_key, "1", timeout=AGENT_LOCK_TIMEOUT)

        if not acquired:
            await self.send(
                text_data=json.dumps({"error": "Please wait for the current response to finish."})
            )
            return

        saved_message = await self.create_message(
            session_id=self.session_id,
            user_id=self.user.id,
            content=message,
            role=MessageRole.USER,
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
            role=MessageRole.ASSISTANT,
            status=MessageStatus.PENDING,
        )

        full_content = ""
        last_ui_action = None
        timed_out = False

        try:
            full_content, last_ui_action = await asyncio.wait_for(
                self._execute_graph(message, saved_agent_message.id, loaded_layers),
                timeout=GRAPH_TURN_TIMEOUT,
            )
        except asyncio.TimeoutError:
            timed_out = True
            full_content = "Request timed out. Please try again."
            logger.error("Agent graph timed out for session %s", self.session_id)

            await self._send_message(
                message_id=str(saved_agent_message.id),
                role=Role.ASSISTANT,
                content=full_content,
                is_chunk=True,
            )
        finally:
            await sync_to_async(cache.delete)(lock_key)

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

        final_status = MessageStatus.FAILED if timed_out else MessageStatus.COMPLETE
        await self.update_message(saved_agent_message.id, full_content, final_status)

    async def _execute_graph(
        self,
        message: str,
        agent_message_id,
        loaded_layers: list[dict] | None = None,
    ) -> tuple[str, dict | None]:
        """Run the LangGraph agent and stream tokens to the client.

        Returns (full_content, last_ui_action) after the stream completes.
        """
        agent = await get_agent()
        inputs = {
            "session_id": self.session_id,
            "messages": [HumanMessage(content=message)],
            "active_node": Node.ORCHESTRATOR,
            "next_node": None,
            "final_response": "",
            "loaded_layers": loaded_layers or [],
            "pending_processing_tool": None,
        }
        config = cast(
            RunnableConfig,
            {
                "configurable": {"thread_id": self.session_id},
                "recursion_limit": 10,
            },
        )

        full_content = ""
        last_final_response = ""
        last_ui_action = None
        chunk_count = 0

        try:
            async for event in agent.astream_events(inputs, version="v2", config=config):
                if (
                    event["event"] == "on_chat_model_stream"
                    and event.get("metadata", {}).get("langgraph_node") != Node.ORCHESTRATOR
                ):
                    chunk = event["data"].get("chunk")
                    chunk_content = chunk.content if chunk else None

                    if chunk_content:
                        if not isinstance(chunk_content, str):
                            chunk_content = str(chunk_content)

                        full_content += chunk_content
                        chunk_count += 1

                        await self._send_message(
                            message_id=str(agent_message_id),
                            role=Role.ASSISTANT,
                            content=chunk_content,
                            is_chunk=True,
                        )

                        # Persist partial content periodically so crashes don't lose everything.
                        if chunk_count % CHUNK_SAVE_INTERVAL == 0:
                            await self.update_message(
                                agent_message_id, full_content, MessageStatus.PENDING
                            )

                elif event["event"] == "on_chain_end":
                    output = event["data"].get("output")

                    if isinstance(output, dict):
                        if output.get("final_response"):
                            last_final_response = output["final_response"]

                        if output.get("ui_action"):
                            last_ui_action = output["ui_action"]

            if not full_content and last_final_response:
                full_content = str(last_final_response)

                await self._send_message(
                    message_id=str(agent_message_id),
                    role=Role.ASSISTANT,
                    content=full_content,
                    is_chunk=True,
                )

        except Exception as e:
            logger.exception("Agent stream error for session %s: %s", self.session_id, e)
            full_content = full_content or "I could not process your request right now."

            await self._send_message(
                message_id=str(agent_message_id),
                role=Role.ASSISTANT,
                content="I could not process your request right now.",
                is_chunk=True,
            )

        return full_content, last_ui_action

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

    @staticmethod
    def _parse_loaded_layers(context: Any) -> list[dict]:
        """Extract a sanitized list of loaded layers from the inbound payload."""
        if not isinstance(context, dict):
            return []

        raw = context.get("loaded_layers")

        if not isinstance(raw, list):
            return []

        result: list[dict] = []

        for entry in raw[:100]:
            if not isinstance(entry, dict):
                continue

            layer_id = entry.get("id")
            name = entry.get("name")
            layer_type = entry.get("type")

            if not isinstance(layer_id, str) or not isinstance(name, str):
                continue

            sanitized: dict[str, Any] = {
                "id": layer_id,
                "name": name,
                "type": layer_type if isinstance(layer_type, str) else "",
            }

            dataset_id = entry.get("datasetId") or entry.get("dataset_id")

            if isinstance(dataset_id, str):
                sanitized["dataset_id"] = dataset_id

            result.append(sanitized)

        return result

    @sync_to_async
    def get_chat_session(self, session_id, user_id):
        try:
            return ChatSession.objects.get(id=session_id, user_id=user_id)
        except ObjectDoesNotExist:
            return None

    @sync_to_async
    def create_message(self, session_id, user_id, content, role, status=MessageStatus.COMPLETE):
        return Message.objects.create(
            session_id=session_id,
            user_id=user_id,
            content=content,
            role=role,
            status=status,
        )

    @sync_to_async
    def update_message(self, message_id, content, status=MessageStatus.COMPLETE):
        Message.objects.filter(id=message_id).update(content=content, status=status)
