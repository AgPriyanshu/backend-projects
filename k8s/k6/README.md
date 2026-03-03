# k6 Load Testing Suite

Comprehensive load tests for the k8s deployment, covering all backend apps.

## Prerequisites

- [k6](https://k6.io/docs/getting-started/installation/) installed
- A running backend instance (local or production)
- A valid auth token or test user credentials

## Quick Start

```bash
# 1. Get an auth token
curl -X POST https://api.worldofapps.bar/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"your_user","password":"your_pass"}'

# 2. Run a test
k6 run -e BASE_URL=https://api.worldofapps.bar -e AUTH_TOKEN=<token> load.ts
```

Or let the tests auto-register a test user:

```bash
k6 run -e BASE_URL=https://api.worldofapps.bar \
       -e TEST_USERNAME=k6_loadtest \
       -e TEST_PASSWORD=strongPassword123 \
       load.ts
```

## Test Types

| Test           | File            | Duration | Peak VUs | Purpose                                  |
| -------------- | --------------- | -------- | -------- | ---------------------------------------- |
| **Load**       | `load.ts`       | ~8 min   | 50       | Normal expected traffic                  |
| **Soak**       | `soak.ts`       | ~35 min  | 30       | Memory leaks, degradation over time      |
| **Spike**      | `spike.ts`      | ~12 min  | 200      | Sudden traffic bursts, HPA response      |
| **Stress**     | `stress.ts`     | ~16 min  | 300      | Find degradation sweet spot              |
| **Breakpoint** | `breakpoint.ts` | Variable | 1000     | Find absolute max capacity (auto-aborts) |

## What Gets Tested

Each iteration simulates a full user session across **all apps**:

- `GET /ping/` — health check (unauthenticated)
- **Tasks** — list, create, get, delete
- **Blogs** — list, create
- **Expenses** — list, create
- **Notes** — list, create
- **Ecommerce** — products, categories, cart listing
- **Web GIS** — datasets, layers listing
- **Notifications** — listing

## File Structure

```
k6/
├── config.ts       # Shared config (BASE_URL, thresholds, auth)
├── helpers.ts      # Reusable scenario functions & custom metrics
├── load.ts         # Standard load test
├── soak.ts         # Endurance / soak test
├── spike.ts        # Traffic spike test
├── stress.ts       # Beyond-capacity stress test
├── breakpoint.ts   # Find-the-limit test
└── README.md
```

## Custom Metrics

| Metric              | Type  | Description                 |
| ------------------- | ----- | --------------------------- |
| `custom_error_rate` | Rate  | Percentage of failed checks |
| `auth_duration`     | Trend | Login request duration      |
| `api_duration`      | Trend | All API request durations   |

## Environment Variables

| Variable        | Default                       | Description                  |
| --------------- | ----------------------------- | ---------------------------- |
| `BASE_URL`      | `https://api.worldofapps.bar` | Backend API base URL         |
| `AUTH_TOKEN`    | _(empty)_                     | Pre-provisioned Bearer token |
| `TEST_USERNAME` | `k6_loadtest`                 | Auto-register username       |
| `TEST_PASSWORD` | `k6_loadtest_password_2026`   | Auto-register password       |

## Tips

- **Start with `load.ts`** to establish a performance baseline
- **Run `soak.ts` overnight** for real endurance testing (increase the 30m hold)
- **Watch `spike.ts`** with `kubectl get hpa -w` to observe autoscaler response
- **`breakpoint.ts` is destructive** — only run in staging with monitoring
- Use `k6 run --out json=results.json` to save results for post-analysis
