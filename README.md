# ⚙️ Atlas Platform Services

> **An enterprise-grade, event-driven modular monolithic architecture orchestrating Python/Django micro-apps, heavy geospatial data workloads, and asynchronous ML tasks.**

Atlas Services is the core backbone powering the [Atlas Platform Web Client](https://github.com/AgPriyanshu/atlas-platform-web). Deployed securely behind a Kubernetes Gateway, it serves as an ultra-reliable API gateway and processing orchestrator for diverse, resource-intensive workflows including Web GIS rendering, Server-Sent Events (SSE) streaming, and external ML integration.

## 🏗️ Core Architecture & Distributed System Design

Atlas Platform rejects the "silver bullet microservices" premise in favor of a **Modular Monolith Architecture**. This ensures domain separation across 10+ core apps without incurring network latency or distributed transaction complexities.

### Key Engineering Decisions:

- **Asynchronous Task Queue:** Heavy workloads—specifically COG (Cloud Optimized GeoTIFF) generation and interactions with our dedicated local LLM server—are aggressively offloaded to an asynchronous compute layer populated by **Celery** workers. This guarantees the Django WSGI/ASGI core remains unblocked, responding instantly.
- **Geospatial (GIS) Database Engine:** Leverages **PostgreSQL + PostGIS** extensions as the absolute source of truth for location data. Atlas translates complex spatial bounding-box queries into highly optimized vector and raster tile responses for the client's Web GIS module.
- **Low-Latency Real-Time Infrastructure:** Adopted an ASGI-first topology using `uvicorn`, `daphne`, and **Django Channels**. **Redis** operates as a high-throughput broker to establish pub/sub systems, pushing real-time synchronization diffs down to connected clients via Server-Sent Events (`/events/`).
- **S3-Compatible Object Storage:** Interoperable file systems leveraging **SeaweedFS** to store large-scale DEM models, images, and static resources without bloating the app tier.

```mermaid
graph TD
    Client[Atlas Web Client] -->|HTTPS/WSS| K8s[K8s NGINX Gateway / Route]

    K8s -->|REST APIs| Django[Django Monolithic Core]
    K8s -->|SSE / WebSockets| Daphne[Daphne ASGI Layer]

    subgraph Memory & Queue Layer
        Daphne -.->|Pub/Sub Channels| Redis Broker & Cache]
        Redis <--->|Cache| Django
    end

    subgraph Data & Persistence
        Django --> PostGIS[(PostgreSQL/PostGIS)]
        Django --> S3[SeaweedFS Object Storage]
    end

    subgraph Asynchronous Processing
        Django -->|Dispatch Task| Celery[Celery Worker Farm]
        Celery -->|Read/Write State| Redis
        Celery -->|Process COG / Compute| PostGIS
        Celery -->|Inference Query| LLM((Local LLM Server))
    end
```

## 🛠️ Technology Stack

**Framework:** Python 3.12, Django 5.1, Django REST Framework
**Real-Time comms:** Django Channels, Server-Sent Events, Daphne
**Database Engine:** PostgreSQL (PostGIS Extension)
**Background Processing:** Celery + Redis
**Cloud Object Storage:** SeaweedFS (S3-Compatible)
**Local Inference:** Qwen3:8b Local Server

## 🐳 Infrastructure & Container Orchestration

This platform is containerized for deterministic deployment sequences and orchestration via **Kubernetes**.

### Fast Local Development

For isolated local testing, a complete infrastructure mock is provided via Docker Compose.

```bash
# Spins up the entire modular monolith, workers, DB, Redis, and Object Storage
docker compose up --build
```

**Auto-Provisioned Services:**

- `web`: Main Django ASGI/WSGI app.
- `worker`: Scaleable Celery task processor.
- `db`: Bootstrapped PostGIS DB instance.
- `redis`: Ephemeral state store / task broker.
- `seaweedfs`: Local S3-compatible backend.

### Kubernetes Helm Deployments

Production assets are templated under `k8s/` utilizing structural layers: Applications, Platform Middleware, and Gateway ingress.

```bash
# Deploys standard Postgres, Redis caching, Gateways and Cloudflare tunnels
cd k8s
./setup.sh
```

## 📊 Scale and Load Testing Pipeline

All new API models, database indices, and infrastructure routing rules are vetted locally via a rigorous `k6` load-testing suite stored inside `k8s/k6`. We simulate multi-vector load, soak, and spike concurrency tests to ensure response latency falls within target SLOs before promotion.

## 🗜️ Docker Image Optimization Pipeline

Because Atlas powers large GIS manipulation libraries, binary bloating is mitigated in CI/CD via an automated integration with [SlimToolkit](https://github.com/slimtoolkit/slim). Committing to the `master` branch triggers the GitHub Action, radically minifying the Docker image pushed to the GHCR registry while preserving crucial `/health/` probes.
