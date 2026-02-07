# AI Chat Integration with Django Channels

This document explains the complete integration between the Django AI Chat app and your LLM server using Django Channels for real-time WebSocket communication.

## Architecture Overview

```
Frontend (React)     Backend (Django)         LLM Server (FastAPI)
     │                       │                        │
     │── WebSocket ──────────┤                        │
     │   (Real-time chat)     │                        │
     │                       │                        │
     │── HTTP REST ───────────┤                        │
     │   (Session mgmt)       │                        │
     │                       │                        │
     │                       │── HTTP ─────────────────┤
     │                       │   (Chat completion)     │
```

## Features

### ✅ Real-time Communication
- **WebSocket chat**: Instant messaging with AI
- **Streaming responses**: Live AI response generation
- **Typing indicators**: User and AI typing status
- **Connection management**: Auto-reconnection, heartbeat

### ✅ Session Management
- **Persistent chat sessions**: Save conversation history
- **Multiple sessions**: Users can have multiple concurrent chats
- **Session settings**: Per-session model, temperature, etc.
- **Soft delete**: Sessions can be deactivated but preserved

### ✅ Model Management
- **Dynamic model sync**: Auto-discover available LLM models
- **Model configuration**: Temperature, max tokens, tools
- **Default model selection**: System-wide and user preferences

### ✅ Chat Presets
- **Template system**: Pre-configured chat setups
- **System prompts**: Role-based AI behavior
- **Public/private presets**: Share templates with other users

## API Endpoints

### HTTP REST API
```
# Session Management
GET    /ai-chat/api/sessions/                     # List user sessions
POST   /ai-chat/api/sessions/                     # Create new session
GET    /ai-chat/api/sessions/{id}/                # Get session details
PATCH  /ai-chat/api/sessions/{id}/                # Update session
DELETE /ai-chat/api/sessions/{id}/                # Delete session

# Messaging (HTTP fallback)
POST   /ai-chat/api/sessions/{id}/send_message/   # Send message
GET    /ai-chat/api/sessions/{id}/messages/       # Get messages

# Models
GET    /ai-chat/api/models/                       # List available models
POST   /ai-chat/api/models/sync_models/           # Sync from LLM server

# Presets
GET    /ai-chat/api/presets/                      # List presets
POST   /ai-chat/api/presets/                      # Create preset
POST   /ai-chat/api/presets/{id}/create_session_from_preset/

# Health & Stats
GET    /ai-chat/api/health/llm_server/            # LLM server status
GET    /ai-chat/api/health/stats/                 # User chat statistics
```

### WebSocket API
```
# Individual Chat Session
ws://localhost:8000/ws/ai-chat/session/{session_id}/?token={auth_token}

# Chat List Updates
ws://localhost:8000/ws/ai-chat/sessions/?token={auth_token}
```

## WebSocket Message Types

### Client → Server
```json
// Send a message
{
  "type": "send_message",
  "message": "Hello, AI!"
}

// Typing indicators
{
  "type": "typing"
}
{
  "type": "stop_typing"
}

// Connection check
{
  "type": "ping"
}
```

### Server → Client
```json
// Connection established
{
  "type": "connection_established",
  "session_id": "uuid",
  "message": "Connected to chat session"
}

// User message saved
{
  "type": "user_message",
  "message": {
    "id": "uuid",
    "role": "user",
    "content": "Hello, AI!",
    "created_at": "2024-01-01T12:00:00Z"
  }
}

// AI typing
{
  "type": "ai_typing",
  "message": "AI is thinking..."
}

// AI response chunk (streaming)
{
  "type": "ai_message_chunk",
  "content": "Hello",
  "full_content": "Hello"
}

// AI response complete
{
  "type": "ai_message_complete",
  "message": {
    "id": "uuid",
    "role": "assistant",
    "content": "Hello! How can I help you today?",
    "created_at": "2024-01-01T12:00:01Z"
  }
}

// Error handling
{
  "type": "error",
  "message": "Error description"
}
```

## Frontend Integration

### React WebSocket Connection
```typescript
// Connect to chat session
const ws = new WebSocket(
  `ws://localhost:8000/ws/ai-chat/session/${sessionId}/?token=${authToken}`
);

// Send message
ws.send(JSON.stringify({
  type: 'send_message',
  message: 'Hello, AI!'
}));

// Handle responses
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'user_message':
      // Add user message to chat
      break;
    case 'ai_message_chunk':
      // Update streaming AI response
      break;
    case 'ai_message_complete':
      // Finalize AI response
      break;
    case 'error':
      // Handle error
      break;
  }
};
```

### Authentication
WebSockets use token authentication:
- **Query parameter**: `?token={auth_token}`
- **Header**: `Authorization: Token {auth_token}`

## Setup Instructions

### 1. Run Database Migrations
```bash
cd backend-projects
source virtual-env/bin/activate
python manage.py migrate
```

### 2. Start Redis (Required for Channels)
```bash
# Using Docker
docker run -d -p 6379:6379 redis:latest

# Or install locally
sudo apt-get install redis-server
redis-server
```

### 3. Start LLM Server
```bash
cd ../llm_server
python llm_server.py
# Runs on http://localhost:8001
```

### 4. Start Django with ASGI
```bash
cd backend-projects
source virtual-env/bin/activate
python manage.py runserver
# Or for production: daphne -b 0.0.0.0 -p 8000 backend_projects.asgi:application
```

### 5. Sync LLM Models
```bash
python manage.py sync_llm_models
```

## Environment Variables

```bash
# LLM Server Configuration
LLM_SERVER_URL=http://localhost:8001
LLM_DEFAULT_MODEL=qwen3:8b
LLM_TIMEOUT=30
LLM_MAX_TOKENS=2000
LLM_TEMPERATURE=0.7
LLM_ENABLE_TOOLS=true

# Redis Configuration (for Channels)
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=backend_projects
DB_USER=postgres
DB_PASSWORD=your_password
```

## Development vs Production

### Development
- WebSocket allows all origins (`*`)
- Debug logging enabled
- SQLite/PostgreSQL local database

### Production
- Restrict WebSocket origins to your domains
- Use production Redis cluster
- Configure proper logging
- Use environment variables for secrets

## Monitoring & Debugging

### Health Checks
```bash
# Check LLM server health
curl http://localhost:8000/ai-chat/api/health/llm_server/

# Check user stats
curl -H "Authorization: Token your_token" \
     http://localhost:8000/ai-chat/api/health/stats/
```

### Logs
- Django logs WebSocket connections/disconnections
- LLM server requests/responses logged
- Error tracking for failed messages

## Performance Considerations

- **Redis scaling**: Use Redis Cluster for high traffic
- **Database indexing**: Messages indexed by session and timestamp
- **Connection limits**: Configure WebSocket connection limits
- **LLM server scaling**: Load balance multiple LLM server instances

---

**Next Steps**: Update your frontend to use the new WebSocket endpoints for real-time chat experience!
