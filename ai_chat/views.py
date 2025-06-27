from django.shortcuts import render
import asyncio
import json
import logging
from typing import AsyncGenerator
from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.authentication import TokenAuthentication
from django.contrib.auth.models import User
from asgiref.sync import sync_to_async, async_to_sync
import django.db.models

from .models import ChatSession, ChatMessage, LLMModel, ChatPreset
from .serializers import (
    ChatSessionSerializer, ChatSessionListSerializer, CreateChatSessionSerializer,
    ChatMessageSerializer, SendMessageSerializer, LLMModelSerializer,
    ChatPresetSerializer, ChatPresetListSerializer
)
from .services import ChatService

logger = logging.getLogger(__name__)


class ChatSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing chat sessions"""
    permission_classes = [AllowAny]  # Allow access without authentication
    
    def get_queryset(self):
        # For now, return all active sessions since we don't have user authentication
        return ChatSession.objects.filter(is_active=True)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ChatSessionListSerializer
        elif self.action == 'create':
            return CreateChatSessionSerializer
        return ChatSessionSerializer
    
    def perform_create(self, serializer):
        """Create a new chat session"""
        chat_service = ChatService()
        system_prompt = serializer.validated_data.pop('system_prompt', None)
        
        # Get or create a default user for sessions without authentication
        default_user, _ = User.objects.get_or_create(
            username='default_user',
            defaults={'email': 'default@example.com'}
        )
        
        session = chat_service.create_session(
            user=default_user,
            system_prompt=system_prompt,
            **serializer.validated_data
        )
        
        # Return the created session data
        return session
    
    def create(self, request, *args, **kwargs):
        """Override create to return proper response"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        session = self.perform_create(serializer)
        
        # Serialize the created session properly
        response_serializer = ChatSessionSerializer(session)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message to the chat session"""
        session = self.get_object()
        serializer = SendMessageSerializer(data=request.data)
        
        if serializer.is_valid():
            message = serializer.validated_data['message']
            stream = serializer.validated_data.get('stream', False)
            
            chat_service = ChatService()
            
            if stream:
                # With WebSockets, we recommend using the WebSocket endpoint for streaming
                # This HTTP streaming is kept for backward compatibility
                def generate_stream():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        async_gen = chat_service.stream_message(session, message)
                        while True:
                            try:
                                chunk = loop.run_until_complete(async_gen.__anext__())
                                yield f"data: {json.dumps(chunk)}\n\n"
                            except StopAsyncIteration:
                                break
                    finally:
                        loop.close()
                    yield "data: [DONE]\n\n"
                
                return StreamingHttpResponse(
                    generate_stream(),
                    content_type='text/plain',
                    headers={
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive',
                        'Access-Control-Allow-Origin': '*',
                    }
                )
            else:
                # Regular response
                try:
                    result = async_to_sync(chat_service.send_message)(session, message, stream=False)
                    if result.get('success'):
                        return Response(result, status=status.HTTP_200_OK)
                    else:
                        return Response(
                            {'error': result.get('error', 'Unknown error')},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                except Exception as e:
                    logger.error(f"Error sending message: {str(e)}")
                    return Response(
                        {'error': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get all messages in a chat session"""
        session = self.get_object()
        messages = session.messages.all()
        serializer = ChatMessageSerializer(messages, many=True)
        return Response({
            'session_id': str(session.id),
            'messages': serializer.data,
            'total_count': messages.count()
        })
    
    @action(detail=True, methods=['patch'])
    def update_settings(self, request, pk=None):
        """Update chat session settings"""
        session = self.get_object()
        
        # Only allow certain fields to be updated
        allowed_fields = ['title', 'model_name', 'temperature', 'max_tokens', 'enable_tools']
        
        for field in allowed_fields:
            if field in request.data:
                setattr(session, field, request.data[field])
        
        session.save()
        serializer = ChatSessionSerializer(session)
        return Response(serializer.data)
    
    @action(detail=True, methods=['delete'])
    def deactivate(self, request, pk=None):
        """Soft delete a chat session"""
        session = self.get_object()
        session.is_active = False
        session.save()
        return Response({'message': 'Chat session deactivated'}, status=status.HTTP_200_OK)


class LLMModelViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for LLM models (read-only)"""
    queryset = LLMModel.objects.filter(is_available=True)
    serializer_class = LLMModelSerializer
    permission_classes = [AllowAny]
    authentication_classes = [TokenAuthentication]
    
    @action(detail=False, methods=['post'])
    def sync_models(self, request):
        """Sync available models from LLM server"""
        try:
            chat_service = ChatService()
            async_to_sync(chat_service.sync_models)()
            
            # Return updated models
            models = LLMModel.objects.filter(is_available=True)
            serializer = self.get_serializer(models, many=True)
            return Response({
                'message': 'Models synced successfully',
                'models': serializer.data
            })
        except Exception as e:
            logger.error(f"Error syncing models: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChatPresetViewSet(viewsets.ModelViewSet):
    """ViewSet for chat presets"""
    permission_classes = [AllowAny]
    authentication_classes = [TokenAuthentication]
    
    def get_queryset(self):
        # Return all public presets since we don't have user authentication
        return ChatPreset.objects.filter(is_public=True)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ChatPresetListSerializer
        return ChatPresetSerializer
    
    def perform_create(self, serializer):
        # Get or create a default user for presets without authentication
        default_user, _ = User.objects.get_or_create(
            username='default_user',
            defaults={'email': 'default@example.com'}
        )
        serializer.save(created_by=default_user)
    
    @action(detail=True, methods=['post'])
    def create_session_from_preset(self, request, pk=None):
        """Create a new chat session from a preset"""
        preset = self.get_object()
        
        # Get or create a default user for sessions without authentication
        default_user, _ = User.objects.get_or_create(
            username='default_user',
            defaults={'email': 'default@example.com'}
        )
        
        chat_service = ChatService()
        session = chat_service.create_session(
            user=default_user,
            title=f"Chat from {preset.name}",
            model_name=preset.model_name,
            temperature=preset.temperature,
            max_tokens=preset.max_tokens,
            enable_tools=preset.enable_tools,
            system_prompt=preset.system_prompt
        )
        
        serializer = ChatSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ChatHealthViewSet(viewsets.ViewSet):
    """ViewSet for health checks"""
    permission_classes = [AllowAny]
    authentication_classes = [TokenAuthentication]
    
    @action(detail=False, methods=['get'])
    def llm_server(self, request):
        """Check LLM server health"""
        try:
            chat_service = ChatService()
            is_healthy = async_to_sync(chat_service.llm_service.health_check)()
            
            return Response({
                'llm_server_healthy': is_healthy,
                'llm_server_url': chat_service.llm_service.base_url,
                'timestamp': ChatMessage.objects.aggregate(
                    latest=django.db.models.Max('created_at')
                ).get('latest')
            })
        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            return Response(
                {'error': str(e), 'llm_server_healthy': False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get chat statistics"""
        try:
            # Get or create a default user for stats without authentication
            default_user, _ = User.objects.get_or_create(
                username='default_user',
                defaults={'email': 'default@example.com'}
            )
            
            stats = {
                'total_sessions': ChatSession.objects.filter(user=default_user, is_active=True).count(),
                'total_messages': ChatMessage.objects.filter(session__user=default_user).count(),
                'recent_sessions': ChatSession.objects.filter(
                    user=default_user, is_active=True
                ).order_by('-updated_at')[:5].count(),
                'favorite_model': ChatSession.objects.filter(
                    user=default_user, is_active=True
                ).values('model_name').annotate(
                    count=django.db.models.Count('model_name')
                ).order_by('-count').first()
            }
            
            return Response(stats)
        except Exception as e:
            logger.error(f"Stats error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
