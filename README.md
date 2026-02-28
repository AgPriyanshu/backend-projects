# Backend Projects with Django: From Fundamentals to Production Patterns

This repository is a multi-app Django backend playground inspired by [Roadmap.sh backend project ideas](https://roadmap.sh/backend/project-ideas). It started as a learning-focused collection and has evolved into a more production-shaped backend system with async processing, geospatial workloads, object storage integration, real-time notifications, and Kubernetes deployment assets.

## Why This Repo Is Complex

This is not a single CRUD app. It is a shared backend platform with multiple bounded contexts and cross-cutting infrastructure:

- Multi-app Django architecture with a shared core module.
- ASGI-first serving with `uvicorn`, `daphne`, and Channels support.
- PostGIS-backed data model for geospatial workflows.
- Celery workers for asynchronous and long-running jobs.
- Redis for caching, pub/sub notifications, and queue backing.
- SeaweedFS S3-compatible object storage integration.
- Reusable workflow/operation abstraction for pipeline-style processing.
- Kubernetes Helm charts for platform and application deployment.

## Current Feature Surface

The project currently includes these active API domains:

- `auth_app`: Authentication and token-based access patterns.
- `blogs_app`: Blog APIs and content workflows.
- `todo_app`: Task management APIs.
- `expense_tracker_app`: Expense APIs with OpenAPI docs.
- `note_markdown_app`: Markdown note APIs with OpenAPI docs.
- `url_shortner_app`: URL shortener APIs.
- `ecommerce_app`: Products, categories, and cart flows.
- `web_gis_app`: Geospatial datasets, layers, tile serving, and COG processing.
- `shared`: Notifications, SSE stream endpoint, shared serializers/models/utilities.

There are also incubating modules (`chat_app`, `ai_chat`, `device_classifier`) present in the codebase, with some routes currently not enabled in project-level URL wiring.

## Architecture Snapshot

- Django project config: `backend_projects`.
- API framework: Django REST Framework.
- Database: PostgreSQL/PostGIS.
- Cache + queue infra: Redis.
- Async jobs: Celery worker (`worker` service in Docker Compose).
- Real-time stream: Server-Sent Events endpoint at `/events/` with Redis pub/sub.
- Storage: S3-compatible object storage via SeaweedFS.
- Geospatial pipeline: COG generation workflow (`web_gis_app/tasks.py` + workflow operations).

## Local Development (Docker Compose)

This repository is intended to be run via Docker Compose:

```bash
git clone https://github.com/AgPriyanshu/backend-projects.git
cd backend-projects
docker compose up --build
```

Services started by default:

- `web`: Django ASGI app.
- `worker`: Celery worker.
- `db`: PostGIS.
- `redis`: Cache and broker.
- `seaweedfs`: S3-compatible object storage.

Common Django commands:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py shell
```

## Kubernetes Deployment

Kubernetes assets are under `k8s/` and include both application and platform layers.

- App charts: `k8s/apps/backend`, `k8s/apps/frontend`, `k8s/apps/shared`.
- Platform charts: gateway, namespaces, PostgreSQL, Redis, object storage, registry, Cloudflare tunnel.
- Gateway API and NGINX Gateway Fabric integration.
- HPA configuration for backend workloads.
- k6 scripts for load, soak, and spike testing (`k8s/k6`).

Quick deployment entrypoint:

```bash
cd k8s
./setup.sh
```

## Engineering Focus and Future Plans

The next iteration of this repository will push deeper into advanced backend patterns:

- Job queues with better retry policies, failure isolation, and scheduling semantics.
- More asynchronous job orchestration for compute-heavy and I/O-heavy tasks.
- Real-time collaboration capabilities beyond notifications (presence, shared state updates, and collaborative streams).
- Stronger Kubernetes operational posture around scaling, rollout strategy, reliability, and observability.
- Expansion of websocket-based and event-driven communication patterns where SSE is not sufficient.

## Technologies Used

- Django + Django REST Framework.
- Channels + Daphne + Uvicorn.
- Celery.
- PostgreSQL/PostGIS.
- Redis.
- SeaweedFS (S3-compatible object storage).
- Docker + Docker Compose.
- Kubernetes + Helm + Gateway API.

## Contributing

Contributions are welcome. Please open an issue or submit a pull request for improvements, bug fixes, or new project modules.

## Docker Image Optimization

This project uses [SlimToolkit](https://github.com/slimtoolkit/slim) to optimize Docker images in CI/CD.

### Automated Optimization (CI/CD)

When you push to the `master` branch, GitHub Actions:

1. Builds the Docker image.
2. Optimizes it with SlimToolkit.
3. Pushes the optimized image to GitHub Container Registry.
4. Reports size reduction in the workflow summary.

### Local Optimization

Install SlimToolkit:

```bash
brew install slimtoolkit/tap/slim
```

Build and optimize:

```bash
docker build -t backend-projects:original .

slim build \
  --target backend-projects:original \
  --tag backend-projects:slim \
  --http-probe=true \
  --http-probe-cmd='http://localhost:8000/health/' \
  --continue-after=60

docker images | grep backend-projects
```

Run optimized image:

```bash
docker run -p 8000:8000 --env-file .env backend-projects:slim
```

## License

This repository is licensed under the MIT License.
