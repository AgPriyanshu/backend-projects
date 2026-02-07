import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token

from .models import ChatMessage, ChatSession
from .serializers import ChatMessageSerializer
from .services import ChatService

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for AI chat functionality"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = None
        self.session = None
        self.user = None
        self.chat_service = ChatService()
        self.room_group_name = None

    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # Get session ID from URL
            self.session_id = self.scope['url_route']['kwargs']['session_id']
            self.room_group_name = f"chat_{self.session_id}"

            # Authenticate user
            self.user = await self.get_user_from_token()
            if self.user is None or isinstance(self.user, AnonymousUser):
                await self.close(code=4001)  # Unauthorized
                return

            # Validate session belongs to user
            self.session = await self.get_chat_session()
            if not self.session:
                await self.close(code=4004)  # Not found
                return

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()

            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'session_id': str(self.session_id),
                'message': 'Connected to chat session'
            }))

            logger.info(f"User {self.user.username} connected to chat session {self.session_id}")

        except Exception as e:
            logger.error(f"Error in WebSocket connect: {str(e)}")
            await self.close(code=4500)  # Internal server error

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

        logger.info(f"User disconnected from chat session {self.session_id} with code {close_code}")

    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'send_message':
                await self.handle_send_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'stop_typing':
                await self.handle_stop_typing(data)
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            else:
                await self.send_error(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}")
            await self.send_error(f"Internal error: {str(e)}")

    async def handle_send_message(self, data):
        """Handle sending a chat message"""
        try:
            message_content = data.get('message', '').strip()
            if not message_content:
                await self.send_error("Message cannot be empty")
                return

            # Send user message immediately
            user_message = await self.save_message('user', message_content)
            await self.send_message_to_group({
                'type': 'user_message',
                'message': await self.serialize_message(user_message)
            })

            # Send typing indicator for AI
            await self.send_message_to_group({
                'type': 'ai_typing',
                'message': 'AI is thinking...'
            })

            # Get AI response via streaming
            await self.stream_ai_response(message_content)

        except Exception as e:
            logger.error(f"Error handling send_message: {str(e)}")
            await self.send_error(f"Failed to send message: {str(e)}")

    async def stream_ai_response(self, user_message: str):
        """Stream AI response to the client"""
        try:
            ai_content = ""

            # Get conversation history
            messages = await database_sync_to_async(
                lambda: list(self.session.messages.all().values('role', 'content'))
            )()

            # Convert to LLM format
            llm_messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages]

            # Stream response from LLM service
            async for chunk in self.chat_service.llm_service.stream_chat_completion(
                messages=llm_messages,
                model=self.session.model_name,
                temperature=self.session.temperature,
                max_tokens=self.session.max_tokens,
                enable_tools=self.session.enable_tools
            ):
                if chunk.get('success') and chunk.get('data'):
                    chunk_data = chunk['data']
                    if chunk_data.get('choices'):
                        delta = chunk_data['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            ai_content += content
                            await self.send_message_to_group({
                                'type': 'ai_message_chunk',
                                'content': content,
                                'full_content': ai_content
                            })
                elif not chunk.get('success'):
                    await self.send_error(f"AI Error: {chunk.get('error', 'Unknown error')}")
                    return

            # Save complete AI response
            if ai_content:
                ai_message = await self.save_message('assistant', ai_content)
                await self.send_message_to_group({
                    'type': 'ai_message_complete',
                    'message': await self.serialize_message(ai_message)
                })

            # Stop AI typing indicator
            await self.send_message_to_group({
                'type': 'ai_typing_stop'
            })

        except Exception as e:
            logger.error(f"Error streaming AI response: {str(e)}")
            await self.send_error(f"AI response error: {str(e)}")
            await self.send_message_to_group({'type': 'ai_typing_stop'})

    async def handle_typing(self, data):
        """Handle typing indicator"""
        await self.send_message_to_group({
            'type': 'user_typing',
            'user': self.user.username
        })

    async def handle_stop_typing(self, data):
        """Handle stop typing indicator"""
        await self.send_message_to_group({
            'type': 'user_typing_stop',
            'user': self.user.username
        })

    async def send_message_to_group(self, message):
        """Send message to the room group"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    async def chat_message(self, event):
        """Receive message from room group"""
        message = event['message']
        await self.send(text_data=json.dumps(message))

    async def send_error(self, error_message: str):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message
        }))

    @database_sync_to_async
    def get_user_from_token(self):
        """Get user from token in query string or headers"""
        try:
            # Try to get token from query string
            query_string = self.scope.get('query_string', b'').decode()
            if 'token=' in query_string:
                token_value = query_string.split('token=')[1].split('&')[0]
            else:
                # Try to get from headers
                headers = dict(self.scope.get('headers', []))
                auth_header = headers.get(b'authorization', b'').decode()
                if auth_header.startswith('Token '):
                    token_value = auth_header[6:]
                else:
                    return None

            token = Token.objects.select_related('user').get(key=token_value)
            return token.user
        except (Token.DoesNotExist, IndexError, AttributeError):
            return None

    @database_sync_to_async
    def get_chat_session(self):
        """Get chat session if it belongs to the user"""
        try:
            return ChatSession.objects.get(
                id=self.session_id,
                user=self.user,
                is_active=True
            )
        except ChatSession.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, role: str, content: str):
        """Save message to database"""
        return ChatMessage.objects.create(
            session=self.session,
            role=role,
            content=content
        )

    @database_sync_to_async
    def serialize_message(self, message):
        """Serialize message for JSON response"""
        serializer = ChatMessageSerializer(message)
        return serializer.data


class ChatListConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for chat session list updates"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.user_group_name = None

    async def connect(self):
        """Handle WebSocket connection for chat list"""
        try:
            # Authenticate user
            self.user = await self.get_user_from_token()
            if self.user is None or isinstance(self.user, AnonymousUser):
                await self.close(code=4001)
                return

            # Join user-specific group
            self.user_group_name = f"user_chats_{self.user.id}"
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )

            await self.accept()

            # Send initial chat list
            await self.send_chat_list()

        except Exception as e:
            logger.error(f"Error in chat list WebSocket connect: {str(e)}")
            await self.close(code=4500)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if self.user_group_name:
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'refresh_chat_list':
                await self.send_chat_list()
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling chat list message: {str(e)}")
            await self.send_error(f"Internal error: {str(e)}")

    async def send_chat_list(self):
        """Send updated chat list to client"""
        try:
            sessions = await self.get_user_chat_sessions()
            await self.send(text_data=json.dumps({
                'type': 'chat_list_update',
                'sessions': sessions
            }))
        except Exception as e:
            logger.error(f"Error sending chat list: {str(e)}")

    async def chat_list_update(self, event):
        """Receive chat list update from group"""
        await self.send(text_data=json.dumps(event['message']))

    async def send_error(self, error_message: str):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message
        }))

    @database_sync_to_async
    def get_user_from_token(self):
        """Get user from token - same as ChatConsumer"""
        try:
            query_string = self.scope.get('query_string', b'').decode()
            if 'token=' in query_string:
                token_value = query_string.split('token=')[1].split('&')[0]
            else:
                headers = dict(self.scope.get('headers', []))
                auth_header = headers.get(b'authorization', b'').decode()
                if auth_header.startswith('Token '):
                    token_value = auth_header[6:]
                else:
                    return None

            token = Token.objects.select_related('user').get(key=token_value)
            return token.user
        except (Token.DoesNotExist, IndexError, AttributeError):
            return None

    @database_sync_to_async
    def get_user_chat_sessions(self):
        """Get user's chat sessions"""
        from .serializers import ChatSessionListSerializer
        sessions = ChatSession.objects.filter(
            user=self.user,
            is_active=True
        ).order_by('-updated_at')
        serializer = ChatSessionListSerializer(sessions, many=True)
        return serializer.data
