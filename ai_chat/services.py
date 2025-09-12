import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
import httpx
from django.conf import settings
from django.contrib.auth.models import User
from asgiref.sync import sync_to_async
from .models import ChatSession, ChatMessage, LLMModel

logger = logging.getLogger(__name__)

class LLMService:
    """Service for communicating with the LLM server"""
    
    def __init__(self):
        self.base_url = settings.LLM_SERVER_CONFIG.get('BASE_URL', 'http://localhost:8001')
        self.timeout = settings.LLM_SERVER_CONFIG.get('TIMEOUT', 30)
        self.default_model = settings.LLM_SERVER_CONFIG.get('DEFAULT_MODEL', 'qwen3:8b')
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get available models from LLM server"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/models")
                if response.status_code == 200:
                    return response.json().get('data', [])
                else:
                    logger.error(f"Failed to get models: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Error getting models: {str(e)}")
            return []
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        enable_tools: bool = True,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Send chat completion request to LLM server"""
        try:
            payload = {
                "model": model or self.default_model,
                "messages": messages,
                "temperature": temperature,
                "stream": stream,
                "tools": [] if not enable_tools else None  # Let server decide on tools
            }
            
            if max_tokens:
                payload["max_tokens"] = max_tokens
            
            async with httpx.AsyncClient(timeout=self.timeout * 2) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload
                )
                
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    logger.error(f"Chat completion failed: {response.status_code}")
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Error in chat completion: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        enable_tools: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completion from LLM server"""
        try:
            payload = {
                "model": model or self.default_model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
                "tools": [] if not enable_tools else None
            }
            
            if max_tokens:
                payload["max_tokens"] = max_tokens
            
            async with httpx.AsyncClient(timeout=self.timeout * 2) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=payload
                ) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                chunk_data = line[6:]
                                if chunk_data.strip() == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(chunk_data)
                                    yield {"success": True, "data": chunk}
                                except json.JSONDecodeError:
                                    continue
                    else:
                        yield {"success": False, "error": f"HTTP {response.status_code}"}
                        
        except Exception as e:
            logger.error(f"Error in streaming chat: {str(e)}")
            yield {"success": False, "error": str(e)}
    
    async def health_check(self) -> bool:
        """Check if LLM server is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False


class ChatService:
    """Service for managing chat sessions and messages"""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def create_session(
        self, 
        user: User, 
        title: str = None,
        model_name: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        enable_tools: bool = True,
        system_prompt: str = None
    ) -> ChatSession:
        """Create a new chat session"""
        session = ChatSession.objects.create(
            user=user,
            title=title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            model_name=model_name or settings.LLM_SERVER_CONFIG.get('DEFAULT_MODEL', 'qwen3:8b'),
            temperature=temperature,
            max_tokens=max_tokens,
            enable_tools=enable_tools
        )
        
        # Add system message if provided
        if system_prompt:
            ChatMessage.objects.create(
                session=session,
                role='system',
                content=system_prompt
            )
        
        return session
    
    def add_message(self, session: ChatSession, role: str, content: str, **kwargs) -> ChatMessage:
        """Add a message to the chat session"""
        return ChatMessage.objects.create(
            session=session,
            role=role,
            content=content,
            tool_calls=kwargs.get('tool_calls'),
            tool_call_id=kwargs.get('tool_call_id'),
            metadata=kwargs.get('metadata', {}),
            token_count=kwargs.get('token_count')
        )
    
    def get_session_messages(self, session: ChatSession) -> List[Dict[str, str]]:
        """Get messages for LLM format"""
        messages = []
        for msg in session.messages.all():
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        return messages
    
    async def send_message(
        self, 
        session: ChatSession, 
        user_message: str,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Send a message and get AI response"""
        try:
            # Add user message (wrap sync operation)
            add_message_sync = sync_to_async(self.add_message)
            user_msg = await add_message_sync(session, 'user', user_message)
            
            # Get conversation history (wrap sync operation)
            get_messages_sync = sync_to_async(self.get_session_messages)
            messages = await get_messages_sync(session)
            
            if stream:
                return {"success": True, "stream": True}
            else:
                # Get AI response
                result = await self.llm_service.chat_completion(
                    messages=messages,
                    model=session.model_name,
                    temperature=session.temperature,
                    max_tokens=session.max_tokens,
                    enable_tools=session.enable_tools
                )
                
                if result.get('success'):
                    response_data = result['data']
                    if response_data.get('choices'):
                        ai_content = response_data['choices'][0]['message']['content']
                        
                        # Save AI response (wrap sync operation)
                        ai_msg = await add_message_sync(session, 'assistant', ai_content)
                        
                        # Update session timestamp (wrap sync operation)
                        save_session_sync = sync_to_async(session.save)
                        await save_session_sync()
                        
                        return {
                            "success": True,
                            "user_message": {
                                "id": str(user_msg.id),
                                "content": user_message,
                                "created_at": user_msg.created_at.isoformat()
                            },
                            "ai_message": {
                                "id": str(ai_msg.id),
                                "content": ai_content,
                                "created_at": ai_msg.created_at.isoformat()
                            }
                        }
                    else:
                        return {"success": False, "error": "No response from AI"}
                else:
                    return {"success": False, "error": result.get('error', 'Unknown error')}
                    
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def stream_message(
        self, 
        session: ChatSession, 
        user_message: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream AI response to a message"""
        try:
            # Add user message (wrap sync operation)
            add_message_sync = sync_to_async(self.add_message)
            user_msg = await add_message_sync(session, 'user', user_message)
            
            # Yield user message first
            yield {
                "type": "user_message",
                "data": {
                    "id": str(user_msg.id),
                    "content": user_message,
                    "created_at": user_msg.created_at.isoformat()
                }
            }
            
            # Get conversation history (wrap sync operation)
            get_messages_sync = sync_to_async(self.get_session_messages)
            messages = await get_messages_sync(session)
            
            # Stream AI response
            ai_content = ""
            async for chunk in self.llm_service.stream_chat_completion(
                messages=messages,
                model=session.model_name,
                temperature=session.temperature,
                max_tokens=session.max_tokens,
                enable_tools=session.enable_tools
            ):
                if chunk.get('success') and chunk.get('data'):
                    chunk_data = chunk['data']
                    if chunk_data.get('choices'):
                        delta = chunk_data['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            ai_content += content
                            yield {
                                "type": "ai_chunk",
                                "data": {
                                    "content": content,
                                    "full_content": ai_content
                                }
                            }
                else:
                    yield {
                        "type": "error",
                        "data": {"error": chunk.get('error', 'Unknown error')}
                    }
                    return
            
            # Save complete AI response (wrap sync operations)
            if ai_content:
                ai_msg = await add_message_sync(session, 'assistant', ai_content)
                save_session_sync = sync_to_async(session.save)
                await save_session_sync()
                
                yield {
                    "type": "ai_complete",
                    "data": {
                        "id": str(ai_msg.id),
                        "content": ai_content,
                        "created_at": ai_msg.created_at.isoformat()
                    }
                }
            
        except Exception as e:
            logger.error(f"Error streaming message: {str(e)}")
            yield {
                "type": "error",
                "data": {"error": str(e)}
            }
    
    async def sync_models(self):
        """Sync available models with database"""
        try:
            models = await self.llm_service.get_available_models()
            
            for model_data in models:
                model_name = model_data.get('id', '')
                if model_name:
                    model_obj, created = LLMModel.objects.get_or_create(
                        name=model_name,
                        defaults={
                            'display_name': model_name,
                            'description': f"Model: {model_name}",
                            'is_available': True
                        }
                    )
                    if not created:
                        model_obj.is_available = True
                        model_obj.save()
            
            # Mark unavailable models
            available_names = [m.get('id') for m in models if m.get('id')]
            LLMModel.objects.exclude(name__in=available_names).update(is_available=False)
            
        except Exception as e:
            logger.error(f"Error syncing models: {str(e)}") 