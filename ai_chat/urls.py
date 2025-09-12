from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r"sessions", views.ChatSessionViewSet, basename="chat-session")
router.register(r"models", views.LLMModelViewSet, basename="llm-model")
router.register(r"presets", views.ChatPresetViewSet, basename="chat-preset")
router.register(r"health", views.ChatHealthViewSet, basename="chat-health")
router.register(r"mcp", views.MCPToolsViewSet, basename="mcp-tools")

app_name = "ai_chat"

urlpatterns = [
    path("api/", include(router.urls)),
]

"""
API Endpoints:

Chat Sessions:
- GET /ai-chat/api/sessions/ - List user's chat sessions
- POST /ai-chat/api/sessions/ - Create new chat session
- GET /ai-chat/api/sessions/{id}/ - Get specific chat session
- PATCH /ai-chat/api/sessions/{id}/ - Update chat session
- DELETE /ai-chat/api/sessions/{id}/ - Delete chat session
- POST /ai-chat/api/sessions/{id}/send_message/ - Send message to session
- GET /ai-chat/api/sessions/{id}/messages/ - Get session messages
- PATCH /ai-chat/api/sessions/{id}/update_settings/ - Update session settings
- DELETE /ai-chat/api/sessions/{id}/deactivate/ - Deactivate session

LLM Models:
- GET /ai-chat/api/models/ - List available models
- GET /ai-chat/api/models/{id}/ - Get specific model
- POST /ai-chat/api/models/sync_models/ - Sync models from LLM server

Chat Presets:
- GET /ai-chat/api/presets/ - List user's and public presets
- POST /ai-chat/api/presets/ - Create new preset
- GET /ai-chat/api/presets/{id}/ - Get specific preset
- PATCH /ai-chat/api/presets/{id}/ - Update preset
- DELETE /ai-chat/api/presets/{id}/ - Delete preset
- POST /ai-chat/api/presets/{id}/create_session_from_preset/ - Create session from preset

Health & Stats:
- GET /ai-chat/api/health/llm_server/ - Check LLM server health
- GET /ai-chat/api/health/stats/ - Get user chat statistics

MCP Tools:
- GET /ai-chat/api/mcp/list_tools/ - List available MCP tools
- POST /ai-chat/api/mcp/execute_tool/ - Execute any MCP tool
- GET /ai-chat/api/mcp/list_layers/ - List all geospatial layers
- POST /ai-chat/api/mcp/find_layer_by_name/ - Find layer by name
- POST /ai-chat/api/mcp/get_layer_info/ - Get layer information
- POST /ai-chat/api/mcp/analyze_population/ - Analyze population data
- POST /ai-chat/api/mcp/get_attribute_stats/ - Get attribute statistics
- POST /ai-chat/api/mcp/analyze_layer_attributes/ - Comprehensive layer analysis
- POST /ai-chat/api/mcp/web_search/ - Search the web
- POST /ai-chat/api/mcp/calculate/ - Perform calculations
"""
