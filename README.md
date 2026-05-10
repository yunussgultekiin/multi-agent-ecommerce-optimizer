# AI Driven Seller Support Platform

AI-driven autonomous e-commerce intelligence platform deployed on Google Cloud Run.

---

## Architecture Overview

Seven independently deployable services communicate over a shared bridge network.

| Service | Technology | Local Port | Role |
|---|---|---|---|
| frontend | Next.js 14 + Tailwind CSS | 3000 | User interface |
| api-gateway | FastAPI | 8000 | Single entry point; fan-out health checks |
| auth-service | FastAPI + PostgreSQL | 8001 | Authentication & authorisation |
| task-service | FastAPI + PostgreSQL | 8002 | Task lifecycle management |
| quota-service | FastAPI + Redis | 8003 | Rate limiting & quota tracking |
| broker-worker | Python async + Redis | 8004 | Task queue consumer |
| agent-worker | Python async + LangGraph | 8005 | Multi-agent workflow executor |

**Data flow**

```
task-service ──► Redis queue ("tasks") ──► broker-worker ──► POST /run ──► agent-worker
                                                                               │
                                                              RivalAgent ◄─────┤
                                                              SeoAgent   ◄─────┘
```

**Shared infrastructure**

- PostgreSQL — Cloud SQL (prod) / `postgres:16-alpine` (local)
- Redis — Cloud Memorystore (prod) / `redis:7-alpine` (local)
- Container registry — Google Artifact Registry (GAR)
- Runtime — Google Cloud Run (one service per container)
- CI/CD — GitHub Actions (one independent workflow per service)

---

## Quick Start

```bash
cp .env.example .env
# Optional: set GEMINI_API_KEY for AI features; leave blank for health-check-only mode
docker compose up --build
```

All nine containers (7 services + postgres + redis) start. Health checks turn green within ~30 s.

---

## Health Check URLs

| Service | URL | Expected response |
|---|---|---|
| frontend | http://localhost:3000/api/health | `{"status":"ok","service":"frontend"}` |
| api-gateway | http://localhost:8000/health | `{"status":"ok","service":"api-gateway","dependencies":{...}}` |
| auth-service | http://localhost:8001/health | `{"status":"ok","service":"auth-service","dependencies":{"postgres":"ok"}}` |
| task-service | http://localhost:8002/health | `{"status":"ok","service":"task-service","dependencies":{"postgres":"ok"}}` |
| quota-service | http://localhost:8003/health | `{"status":"ok","service":"quota-service","dependencies":{"redis":"ok"}}` |
| broker-worker | http://localhost:8004/health | `{"status":"ok","service":"broker-worker","dependencies":{"redis":"ok"}}` |
| agent-worker | http://localhost:8005/health | `{"status":"ok","service":"agent-worker","version":"0.1.0"}` |

---

## Environment Variables

Copy `.env.example` to `.env`. All variables are optional for health-check mode.

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | Async PostgreSQL DSN | `postgresql+asyncpg://postgres:password@postgres:5432/platform` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `POSTGRES_USER` | PostgreSQL superuser | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `password` |
| `POSTGRES_DB` | Database name | `platform` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIza...` |
| `CHROMA_HOST` | ChromaDB host (RAG) | `localhost` |
| `AGENT_WORKER_URL` | agent-worker base URL for broker-worker | `http://agent-worker:8080` |

---

## GitHub Secrets Setup (Workload Identity Federation)

No long-lived service account keys are stored in GitHub.

### One-time GCP setup

```bash
PROJECT_ID=your-project-id
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com

# Create Artifact Registry repository
gcloud artifacts repositories create seller-support \
  --repository-format=docker \
  --location=us-central1

# Create deployer service account
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions deployer"

SA="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/run.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/iam.serviceAccountUser"

# Workload Identity pool + provider
gcloud iam workload-identity-pools create github-pool \
  --location=global --display-name="GitHub pool"

gcloud iam workload-identity-pools providers create-oidc github-provider \
  --workload-identity-pool=github-pool \
  --location=global \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='YOUR_ORG/YOUR_REPO'"

PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud iam service-accounts add-iam-policy-binding $SA \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR_ORG/YOUR_REPO"
```

### Required GitHub Secrets

Add in **Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `GCP_PROJECT_ID` | GCP project ID |
| `GCP_REGION` | Cloud Run region (e.g. `us-central1`) |
| `GAR_LOCATION` | Artifact Registry location (e.g. `us-central1`) |
| `GAR_REPO` | Artifact Registry repo name (e.g. `seller-support`) |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | WIF provider resource name |
| `GCP_SERVICE_ACCOUNT` | `github-actions@PROJECT_ID.iam.gserviceaccount.com` |
| `DATABASE_URL` | Cloud SQL connection string |
| `REDIS_URL` | Cloud Memorystore connection string |
| `GEMINI_API_KEY` | Google Gemini API key |
| `AGENT_WORKER_URL` | Cloud Run URL of the agent-worker service |

---

## CI/CD Pipelines

Each service has an independent workflow. A push to `main` triggers only the workflow(s) whose path changed.

| Workflow file | Watches path | Cloud Run service | Extra env secrets |
|---|---|---|---|
| `deploy-frontend.yml` | `frontend/**` | `frontend` | — |
| `deploy-api-gateway.yml` | `services/api-gateway/**` | `api-gateway` | — |
| `deploy-auth-service.yml` | `services/auth-service/**` | `auth-service` | `DATABASE_URL` |
| `deploy-task-service.yml` | `services/task-service/**` | `task-service` | `DATABASE_URL` |
| `deploy-quota-service.yml` | `services/quota-service/**` | `quota-service` | `REDIS_URL` |
| `deploy-broker-worker.yml` | `services/broker-worker/**` | `broker-worker` | `REDIS_URL`, `AGENT_WORKER_URL` |
| `deploy-agent-worker.yml` | `services/agent-worker/**` | `agent-worker` | `REDIS_URL`, `GEMINI_API_KEY` |

Every workflow: checkout → WIF auth → Docker buildx → push to GAR → `deploy-cloudrun@v2`.

---

## Multi-Agent Workflow

The agent-worker runs a **LangGraph** `StateGraph` with two sequential nodes:

```
START → rival_agent → seo_agent → END
```

State shape (`WorkflowState` TypedDict) travels through both nodes and is logged at completion.

### RivalAgent tools

| Tool | Status | Planned implementation |
|---|---|---|
| `WebScraperTool` | stub | crawl4ai |
| `TrendsTool` | stub | pytrends + pandas (run_in_executor) |
| `MarketGapAnalyzer` | stub | scikit-learn KMeans (run_in_executor) |
| `VisionTool` | stub | Gemini Vision API |
| `SmartPricingEngine` | stub | scikit-learn Ridge (run_in_executor) |

### SeoAgent tools

| Tool | Status | Planned implementation |
|---|---|---|
| `RagContextTool` | stub | ChromaDB async client |
| `SeoOptimizerTool` | stub | Gemini 2.0 Flash |

All stubs return valid empty defaults; the workflow completes and `/health` returns 200 with no external services required.

---

## Adding a New Service

1. Create `services/<name>/` with `Dockerfile`, `.dockerignore`, `requirements.txt`, and `app/`.
2. Add `app/main.py` (FastAPI lifespan or aiohttp runner) and `app/health.py` returning `GET /health → {"status":"ok","service":"<name>"}`.
3. Add the service to `docker-compose.yml` with `healthcheck: wget -qO- http://localhost:8080/health`.
4. Copy `.github/workflows/deploy-api-gateway.yml` → `deploy-<name>.yml`; replace service name, path glob, and env secrets.
5. Add any new GitHub Secrets.
6. Add the new service URL to `api-gateway/app/health.py` `_DOWNSTREAM` dict (via a new env var with a sensible default).
