# agent_manager

Django app powering the Atlas Platform AI chat — LangGraph multi-agent graph streamed over WebSockets.

## Architecture

- **Graph:** 4-node LangGraph (`ORCHESTRATOR → WEB_GIS_EXPERT → UI_EXPERT → MAP_ZOOM_TO`)
- **Transport:** Django Channels WebSocket at `ws/ai/sessions/<uuid:session_id>/`
- **Streaming:** `astream_events(v2)` — token-level chunks sent to frontend in real time
- **LLM:** Qwen via local vLLM server (configurable)
- **Auth:** Bearer token middleware on WebSocket handshake

---

## Production Readiness TODO

### Critical — Correctness & Safety

- [x] Add `recursion_limit` to graph config to prevent infinite node loops
- [x] Wrap `astream_events()` with `asyncio.timeout()` (hard limit per turn) to prevent infinite hangs
- [x] Add per-session Redis lock to reject new messages while a graph run is in progress
- [x] Handle `ValidationError` / `OutputParserException` from `with_structured_output` — retry with a repair prompt instead of falling back to a generic error message

### High — Memory & State

- [x] Integrate LangGraph checkpointing (`AsyncPostgresSaver`) so multi-turn conversation state persists across messages and reconnects
- [x] Pass `thread_id = str(session_id)` in graph config so each session has its own checkpoint thread
- [x] Add sliding window or `trim_messages` step to prevent context window overflow on long conversations (~20+ turns)
- [ ] Reconstruct DB message history as initial context when a new WebSocket connects to an existing session

### High — Infrastructure

- [x] Move vLLM URL and model name out of `agents/agent.py` — load from environment variables or the `LLM` DB model
- [ ] Add health check for the vLLM server; fall back to a cloud model (e.g. Claude Haiku) when primary is unreachable
- [x] Verify `CHANNEL_LAYERS` uses `channels_redis.core.RedisChannelLayer`, not `InMemoryChannelLayer`, to support multiple `web` containers
- [ ] Add Kubernetes `readinessProbe` and `livenessProbe` that verify DB + LLM reachability before marking the pod ready
- [ ] Run Celery workers and Channels workers on separate pools with separate CPU/memory limits in k8s

### High — Operational Correctness

- [x] Add `status` field to `Message` model (`pending` / `complete` / `failed`) to detect orphaned rows after consumer crashes
- [x] Write periodic cleanup task to mark or delete stale `pending` messages older than N minutes
- [x] Update the `Message` DB row incrementally during streaming (every N chunks or every 5 seconds) so partial content survives consumer crashes
- [x] Expose a REST endpoint for the frontend to fetch the last message of a session on reconnect
- [x] Add client-generated `message_id` (UUID) in WebSocket payload; server deduplicates via Redis to prevent duplicate runs on reconnect
- [x] Add `websocket_disconnect` handler that saves partial content and sends a reconnect hint to the client before closing

### Medium — Security

- [ ] Add message size validation — reject messages exceeding a max character limit (e.g. 4000 chars)
- [ ] Add prompt injection guardrail layer before the orchestrator node (regex blocklist or LlamaGuard)
- [ ] Sanitize tool output before injecting into LLM context to guard against indirect prompt injection from third-party APIs
- [ ] Re-validate auth token on every `receive()` call, not just on WebSocket connect, to handle mid-session token revocation
- [ ] Ensure vLLM server traffic is TLS-terminated even on the private/Tailscale network

### Medium — LLM & Graph

- [ ] Track token usage per message/session/node via `on_llm_end` event — write to `Message` model or a metrics table
- [ ] Build a golden-set eval suite (10–20 inputs with expected routing outcomes) to run against the graph before deploying updated model weights

### Medium — Data & Privacy

- [ ] Add soft-delete (`deleted_at`) to `ChatSession` and `Message` models to support GDPR/CCPA user data deletion
- [ ] Add message retention policy / TTL for old sessions
- [ ] Tag geocode query strings and location data as PII in the logging pipeline to prevent plain-text location data in log aggregators

### Medium — Testing

- [ ] Write integration tests for the graph with a mocked LLM — cover end-to-end execution, `recursion_limit`, and malformed LLM output
- [ ] Add WebSocket consumer lifecycle tests using `pytest-asyncio` + `channels.testing.WebsocketCommunicator`
- [ ] Add chaos tests for LLM failure modes: empty response, malformed `RoutingDecision`, unknown `next_node` value

### Low — Observability

- [ ] Integrate LangSmith (or self-hosted LangFuse) tracing — add `LANGCHAIN_TRACING_V2` and project config to settings
- [ ] Add per-user rate limiting on WebSocket messages using Redis (cap messages per minute)
