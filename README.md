# Synapse — Multi-Agent E-Commerce Optimizer

> Developed as part of **BTK Hackathon 2026**, organized jointly by **BTK Akademi**, **Türkiye Girişimcilik Vakfı (TGVF)** and **Google Turkey**.  
> Built on **Google Gemini 2.5** · Deployed on **Google Cloud Run**

---

## Table of Contents

- [What It Does](#what-it-does)
- [Architecture](#architecture)
- [Services](#services)
- [AI Layer — Agent Worker](#ai-layer--agent-worker)
- [Data Flow](#data-flow)
- [Infrastructure & Cloud](#infrastructure--cloud)
- [CI/CD Pipeline](#cicd-pipeline)
- [Security](#security)
- [Technology Stack](#technology-stack)
- [Environment Variables](#environment-variables)
- [Local Development Notice](#local-development-notice)
- [Team & Development Process](#team--development-process)

---

## What It Does

E-commerce sellers on platforms like **Trendyol**, **Amazon**, and **Hepsiburada** spend enormous amounts of time manually researching competitors, crafting product titles and descriptions, and figuring out competitive pricing. Synapse automates all of this end-to-end using a multi-agent AI system.

A seller submits their product information (title, category, brand, target platform). The platform then runs two sequential AI workflows:

### 1. Rival Analysis Workflow
- **Competitor Discovery** — Finds real competitor products on the target platform matching the seller's product
- **Competitor Research** — Deep-dives into each competitor: price, ratings, review count, key features, images
- **Sentiment Analysis** — Extracts positive and negative customer sentiment from competitor reviews
- **Trend Analysis** — Identifies market trends and seasonal demand patterns in the product category
- **Market Gap Analysis** — Detects unmet customer needs that competitors fail to address
- **Smart Pricing** — Calculates an optimal price range and recommends pricing strategy based on competitor overlap

### 2. SEO & Image Workflow (runs in parallel)
- **SEO Optimizer** — Generates platform-specific listing content (title, description, bullet points, tags, meta keywords) in the selected tone (`casual`, `professional`, or `premium`), augmented by a ChromaDB RAG store of e-commerce SEO best practices
- **Image Generation** — Generates a studio-quality white-background product image with Gemini, removes the background via RemoveBG API, composites it onto a platform-sized canvas, and uploads to Google Cloud Storage

Everything runs asynchronously on a task queue. The seller watches real-time progress in the browser and receives a full analytics dashboard when the analysis completes.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js 14)                      │
│              Port 3000 · SSR + Client-Side Polling               │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTPS
┌──────────────────────────────▼───────────────────────────────────┐
│                       API Gateway (FastAPI)                       │
│   Port 8000 · JWT validation · CORS · SlowAPI rate limiting      │
│   Routes: /auth → Auth Svc  /analyze → Task+Quota  /upload → GCS│
└──────┬────────────────┬──────────────────────────────┬───────────┘
       │                │                              │
       ▼                ▼                              ▼
 ┌──────────┐    ┌─────────────┐               ┌────────────┐
 │  Auth    │    │    Task     │               │   Quota    │
 │ Service  │    │   Service   │               │  Service   │
 │  :8001   │    │   :8002     │               │   :8003    │
 │ Cloud SQL│    │ Cloud SQL + │               │ Memorystore│
 │ + JWT    │    │ Memorystore │               │  Lua atomc │
 └──────────┘    └──────┬──────┘               └────────────┘
                        │ Push to Redis Task Queue
                        ▼
               ┌─────────────────┐
               │  Broker Worker  │
               │     :8004       │
               │ BLPOP · Retry   │
               │ Exp. Backoff    │
               └────────┬────────┘
                        │ HTTP POST /run
                        ▼
        ┌───────────────────────────────────────────────┐
        │                 Agent Worker                   │
        │                  :8005                         │
        │                                               │
        │  ┌──────────────────────────────────────────┐ │
        │  │            Rival Graph (LangGraph)        │ │
        │  │  discover → research → [sentiment|trends] │ │
        │  │  → [market_gap|pricing] → finalize        │ │
        │  └────────────────────┬─────────────────────┘ │
        │                       │ rival_json             │
        │  ┌────────────────────▼─────────────────────┐ │
        │  │             SEO Graph (LangGraph)         │ │
        │  │  [generate_seo ‖ generate_image] → final  │ │
        │  └──────────────────────────────────────────┘ │
        │                                               │
        │  Gemini 2.5  ·  ChromaDB RAG  ·  GCS Upload  │
        └───────────────────────────────────────────────┘
```

Every service is a separate **Google Cloud Run** instance connected via **VPC Connector** for private network communication.

---

## Services

### API Gateway — Port 8000

The single public entry point for the entire platform. Every external HTTP request passes through here.

**Responsibilities:**
- **JWT Middleware** — validates Bearer tokens on every protected route by calling Auth Service's internal `/validate` endpoint
- **CORS Middleware** — allows the frontend origin; rejects all other cross-origin requests
- **SlowAPI Rate Limiting** — Redis-backed token-bucket rate limiting to prevent API abuse
- **`/analyze`** — checks quota (Quota Service), creates a task record (Task Service), pushes the task payload to Redis queue, returns `task_id` to caller
- **`/analyze/{task_id}`** — proxies task status and result retrieval from Task Service
- **`/auth`** — reverse proxy to Auth Service for login and registration
- **`/upload`** — generates Google Cloud Storage presigned URLs for multipart file uploads; handles `aiofiles` streaming
- **`/health`** — pings all downstream services and returns aggregated health status

**Technical choices:**
- `httpx.AsyncClient` with configurable timeout and connection pooling for all downstream calls
- `slowapi` chosen over a custom middleware for FastAPI-native integration with Redis backend
- Token validation is a local call to Auth Service per request — no shared secret lookup; this keeps the gateway stateless

---

### Auth Service — Port 8001

User identity and token management.

**Endpoints:**
- `POST /register` — creates user with bcrypt-hashed password (controllable via `REGISTRATION_ENABLED`)
- `POST /login` — validates credentials, returns access token (30 min) + refresh token (7 days)
- `POST /refresh` — exchanges refresh token for new access token
- `POST /internal/validate` — called by API Gateway; validates token, returns `user_id` claim

**Technical choices:**
- `SQLAlchemy 2.x` async ORM with `asyncpg` driver — fully non-blocking database I/O
- `Alembic` for schema migrations; migrations run automatically on service startup
- `PyJWT` with HS256 — RS256 was considered but the added operational complexity (key rotation, JWKS endpoint) was not justified for hackathon scope
- `bcrypt` with work factor 12 for password hashing
- In production, database connections go through `cloud-sql-python-connector` with IAM-based authentication — no password in the connection string

---

### Task Service — Port 8002

Owns the full lifecycle of analysis tasks and stores their results.

**Task state machine:**
```
pending ──▶ running ──▶ completed
                   └──▶ failed
                   └──▶ cancelled
```

**Key design decisions:**
- Tasks are identified by UUIDs generated at creation time; the API Gateway returns this ID to the frontend immediately so it can begin polling
- The task `payload` (all user input) is stored as JSONB in PostgreSQL — no separate input tables
- `seo_tone` is a first-class field on the task (`casual | professional | premium`) because it influences downstream SEO generation and is needed at multiple steps
- `TaskResult` is a separate table (one-to-one with Task) — this allows the main task table to be queried cheaply for status without loading large JSON result blobs
- Progress is reported via two channels simultaneously: `HSET task_progress:{task_id}` in Redis (for polling) and `PUBLISH progress:{task_id}` (for future WebSocket support)
- `PATCH /tasks/{id}/status` returns 409 if the task is already in a terminal state; Broker Worker handles this gracefully by logging and continuing

---

### Quota Service — Port 8003

Per-user daily analysis quota enforcement.

**How it works:**
- On every `POST /analyze`, API Gateway calls `POST /quota/check` before touching the task queue
- Quota Service executes a **Lua script** on Redis that atomically: increments `quota:{user_id}`, sets 86400-second TTL if the key is new, and checks against `QUOTA_LIMIT`
- If the limit is exceeded, returns 429; API Gateway surfaces this to the frontend with a human-readable message
- Lua is mandatory here — a non-atomic INCR + EXPIRE sequence would create a race condition under concurrent requests from the same user

**Configuration:**
- `QUOTA_LIMIT` — default 10, easily bumped for demo purposes
- `QUOTA_TTL_SECONDS` — default 86400 (rolling 24-hour window per user)

---

### Broker Worker — Port 8004

The async task dispatcher. Bridges Redis queue to Agent Worker with retry logic.

**Consumer loop:**
1. Runs a blocking `BLPOP` on `task_queue` in a **dedicated daemon thread** — this prevents the blocking call from interfering with the FastAPI event loop
2. On receiving a message: deserializes JSON, calls `AgentClient.run(task_id, payload)` which fires `POST /run` to Agent Worker
3. Agent Worker responds with 202 Accepted; the broker updates Task Service to `running`
4. If Agent Worker returns 5xx or times out: spawns a separate retry thread with **exponential backoff** — `delay = base_delay * 2^attempt` (default: 2s, 4s, 8s)
5. Retry state (attempt count, last error) is persisted in PostgreSQL — survives broker restarts
6. After `MAX_RETRY_COUNT` (3) exhausted: calls Task Service to mark the task `failed`

**Why a dedicated thread for BLPOP:**  
`redis-py`'s blocking commands cannot be used inside an asyncio event loop without wrapping. Running BLPOP in a thread avoids `asyncio.run_in_executor` overhead and keeps the consumer code straightforward.

---

### Agent Worker — Port 8005

The AI execution engine. Runs LangGraph workflows and calls Google Gemini.

> See [AI Layer](#ai-layer--agent-worker) for full detail.

---

### Frontend — Port 3000

A Turkish-localized Next.js 14 application.

**Page map:**

| Route | Purpose |
|-------|---------|
| `/` | Landing page — animated feature showcase, CTA |
| `/login` | JWT login form |
| `/register` | User registration |
| `/dashboard` | Overview of recent analyses |
| `/dashboard/analyze` | New analysis form (product info, platform, tone) |
| `/dashboard/analyze/[taskId]/progress` | Real-time progress tracking |
| `/dashboard/result/[taskId]` | Full result dashboard with charts |
| `/dashboard/history` | Paginated past analyses |

**Technical choices:**
- **Next.js 14 App Router** — server components for initial page load, client components for interactive parts; avoids full SPA overhead
- **Zustand** — minimal global state (auth token, user info); chosen over Redux for its zero-boilerplate API
- **shadcn/ui + Radix UI** — accessible, headless component primitives styled with TailwindCSS; much faster to customize than a pre-styled library
- **Framer Motion** — page transitions and micro-animations on the landing page and progress screen
- **react-hook-form + zod** — schema-driven form validation; the same zod schemas are reused for TypeScript types
- **Polling vs WebSocket** — frontend polls `GET /tasks/{id}` every 2 seconds for progress updates. WebSocket was intentionally skipped: it would require a persistent connection layer in Cloud Run (which has request-based billing) and adds infrastructure complexity without a significant UX difference at this scale
- **axios interceptor** — transparently refreshes the access token on 401 responses and retries the original request

---

## AI Layer — Agent Worker

### LangGraph State Machines

Both workflows are implemented as LangGraph `StateGraph` instances. The state is a Python `TypedDict` that accumulates data across nodes — no shared mutable state, no side-channel communication.

Every node is wrapped by `NodeRunner`, a lightweight middleware that:
1. Checks a Redis key `cancelled:{task_id}` before the node executes — if present, returns `{"cancelled": True}` immediately and the graph routes to END
2. Reports `(step_name, "running", pct%)` to Redis before invoking the node function
3. Reports `(step_name, "completed", pct%)` after the node function returns successfully

Progress events are written to two Redis structures simultaneously:
- `HSET task_progress:{task_id}` — durable hash for late-joining pollers
- `PUBLISH progress:{task_id}` — pub/sub channel for future real-time clients

---

#### Rival Graph

```
START
  │
  ▼  10%
discover_competitors
  │  Gemini 2.5 Flash Lite
  │  Input:  platform, category, product title, brand
  │  Output: list of competitor names with similarity scores
  │
  ▼  25%
research_competitors
  │  Gemini 2.5 Flash Lite (parallelized per competitor)
  │  Input:  competitor_names list
  │  Output: per-competitor {price, rating, review_count, features, images}
  │  Filter: relevance tiers (PRIMARY ≥ threshold, SECONDARY fallback, top-N emergency)
  │
  ├─────────────────────────────────────┐
  ▼  40%                               ▼  40%
analyze_sentiment                 analyze_trends
  │  Gemini 2.5 Flash              │  Gemini 2.5 Flash
  │  Positive/negative themes      │  Category trend signals
  │  from competitor reviews       │  Seasonality, demand patterns
  │
  ├──────────────┐         ┌────────────┘
  ▼  72%         ▼  72%
market_gap     pricing
  │  Gemini 2.5 Flash
  │  Unmet customer needs  │  Optimal price range
  │  Opportunity areas     │  Competitor overlap scoring
  │
  └──────────┬──────────────┘
             ▼  55%
          finalize
             │  Assembles complete rival_json
             │  Hands off state to SEO Graph
             ▼
            END
```

**Parallel execution:** `analyze_sentiment` and `analyze_trends` run as a parallel fan-out (LangGraph handles the join). Similarly, `market_gap` and `pricing` run in parallel. This halves latency for these two phases.

**Relevance filtering in research:** After each competitor is researched, results are sorted by the `similarity_score` from the discovery step. The agent applies a primary threshold first, then a secondary threshold, and as a last resort takes the top N. This ensures low-relevance competitors do not dilute the analysis.

---

#### SEO Graph

```
START
  ├────────────────────────────────────┐
  ▼  80%                              ▼  90%
generate_seo                   generate_image
  │  Gemini 2.5 Flash            │  Gemini 2.5 Flash (image)
  │  Input: rival_json           │  Input: product title
  │         seo_tone             │  Step 1: generate studio image
  │         ChromaDB top-6 RAG   │  Step 2: remove background (RemoveBG)
  │  Output: title, description  │  Step 3: composite on platform canvas
  │          bullets, tags, meta │  Step 4: upload to GCS → signed URL
  │
  └──────────┬─────────────────────────┘
             ▼  100%
          finalize
             │  Merges seo_output + generated_image_url
             │  Saves complete result to Task Service
             ▼
            END
```

---

### Agent Tool Detail

#### Rival Agent Tools

| Tool | Model | Purpose |
|------|-------|---------|
| `competitor_discovery` | `gemini-2.5-flash-lite` | Identifies real competitors on the target platform; returns names with similarity scores |
| `competitor_research` | `gemini-2.5-flash-lite` | Structured deep-dive per competitor; run concurrently |
| `sentiment_analysis` | `gemini-2.5-flash` | Classifies positive/negative themes from reviews; surfaces top pain points and praised features |
| `trend_analysis` | `gemini-2.5-flash` | Extracts demand trends, seasonal patterns, and emerging opportunities in the category |
| `market_gap_analyzer` | `gemini-2.5-flash` | Identifies gaps between what customers want and what competitors offer |
| `smart_pricing_engine` | `gemini-2.5-flash` | Suggests optimal price band, discounting strategy, and pricing recommendations based on competitor overlap |

**Model selection rationale:**  
Discovery and Research are high-volume, structured extraction tasks with relatively straightforward prompts — `gemini-2.5-flash-lite` provides the best cost/speed tradeoff here. The analytical nodes (Sentiment, Trends, Gap, Pricing) require deeper reasoning and produce JSON that feeds subsequent nodes, so `gemini-2.5-flash` is used to maximize output quality.

All Gemini calls set `response_mime_type: "application/json"` and include JSON schema constraints in the prompt — raw JSON parsing is used throughout; no LangChain output parsers.

#### SEO Agent Tools

**SEO Optimizer:**
- `gemini-2.5-flash` + `ChromaDB` RAG
- A curated collection of e-commerce SEO rules is stored as chunks in ChromaDB (`CHROMA_COLLECTION_NAME=seo_chunks`)
- At runtime, the top-K (`CHROMA_TOP_K=6`) most relevant chunks are retrieved based on the product category and platform, then injected into the system prompt
- Platform-specific constraints (title character limits, bullet count, tag policies) are enforced through `json_prompt_rules.py` — each platform has its own JSON schema that the model must fill
- Output tone is controlled by the `seo_tone` parameter passed in the task payload

**Image Generation Pipeline:**

```
Gemini image generation
    │  Prompt: "{product_title} product on white background, 
    │           studio lighting, professional e-commerce photo"
    │  Output: PIL Image (RGBA)
    ▼
RemoveBG API (background_removal.py)
    │  Sends raw image bytes, receives mask-applied PNG
    │  Falls back to Gemini-generated image if RemoveBG fails
    ▼
Platform Canvas Composition (utils_image.py)
    │  Trendyol:    1200 × 1800 px, product at 78% of canvas height
    │  Amazon:      1600 × 1600 px, product at 76% of canvas height
    │  Hepsiburada: 1200 × 1200 px, product at 76% of canvas height
    │  - Transparent padding cropped (4% margin preserved)
    │  - Product centered on white canvas
    ▼
Google Cloud Storage Upload
    │  Filename: UUID-based, stored in configured GCS_BUCKET
    │  Returns: signed URL included in task result JSON
    ▼
Task Result
```

**Image generation note:** Variant-based image selection (`select_variant()`) is currently inactive. `gemini-2.5-flash-image` does not fully support the structured generation constraints required by this feature, so the image pipeline bypasses variant selection and generates from the base product title. The `select_variant()` logic was also coupled to `competitor_variant_overlap` data from the pricing step, which depended on variant-aware tooling that was removed during development. The function has been retained in the codebase for future development if variant support is revisited.

---

### Cancellation Mechanism

When a user cancels a running analysis:
1. API Gateway writes `SET cancelled:{task_id} 1 EX 3600` to Redis
2. Before each node executes, `NodeRunner` checks `EXISTS cancelled:{task_id}`
3. If the key exists: the node function is skipped; `{"cancelled": True, "status": "cancelled"}` is returned
4. The `_cancel_or()` conditional edge sees `cancelled=True` and routes to `END`
5. `WorkflowErrorHandler` calls Task Service with `status=cancelled`
6. The frontend receives `status=cancelled` on the next poll and redirects to dashboard

---

### Inter-Service Authentication — `services/shared/`

All service-to-service HTTP calls use the shared `InternalHttpClient`:

- Issues JWTs with `iss="internal-service"` claim — distinguishable from user tokens at validation time
- **Token caching** with 5-minute TTL and 30-second pre-expiry refresh buffer — minimizes JWT generation overhead on high-frequency inter-service calls
- `asyncio.Lock` prevents concurrent refresh races in async contexts
- A sync variant exists for the Broker Worker (which uses `threading` rather than asyncio)

---

## Data Flow

### End-to-End: New Analysis Request

```
1. User submits form
       │
       ▼
2. API Gateway
   ├─ Validates JWT (Auth Service /internal/validate)
   ├─ Checks quota (Quota Service → Redis Lua atomic increment)
   ├─ Creates task record (Task Service → Cloud SQL)
   ├─ Pushes {task_id, payload} to Redis task_queue (RPUSH)
   └─ Returns {task_id} to frontend

3. Frontend starts polling GET /tasks/{task_id} every 2 seconds

4. Broker Worker (background thread)
   ├─ BLPOP task_queue → receives message
   ├─ PATCH /tasks/{id}/status → "running" (Task Service)
   └─ POST /run to Agent Worker

5. Agent Worker (async)
   ├─ Runs Rival Graph (LangGraph)
   │   Each node: check cancellation → report progress → execute Gemini call → update progress
   │   Parallel: [sentiment ‖ trends] then [gap ‖ pricing]
   ├─ Passes rival_json to SEO Graph
   └─ SEO Graph: [generate_seo ‖ generate_image] in parallel
       ├─ generate_seo: ChromaDB RAG + Gemini → structured listing content
       └─ generate_image: Gemini → RemoveBG → Canvas → GCS upload

6. Agent Worker finalizes
   ├─ POST /tasks/{id}/result (Task Service → Cloud SQL)
   └─ PATCH /tasks/{id}/status → "completed"

7. Frontend receives status=completed on next poll
   └─ Navigates to /dashboard/result/{taskId}
```

---

## Infrastructure & Cloud

### Google Cloud Services Used

| Service | Purpose |
|---------|---------|
| **Cloud Run** | Serverless container hosting for all 7 services; scales to zero when idle |
| **Cloud SQL (PostgreSQL 15)** | Managed relational database; used by Auth, Task, and Broker services |
| **Memorystore (Redis 7)** | Fully managed Redis; task queue, quota counters, progress events, cancellation signals |
| **Google Cloud Storage (GCS)** | Generated product image storage; returns signed URLs included in task results |
| **Artifact Registry (GAR)** | Private Docker image registry; all service images tagged with commit SHA and `latest` |
| **VPC Connector** | Private network bridge between Cloud Run services and Memorystore/Cloud SQL |
| **Workload Identity Federation** | Keyless GitHub Actions → GCP authentication (no service account JSON files) |
| **Vertex AI / Gemini API** | Gemini 2.5 Flash and Flash-Lite model inference |

### Google Cloud SQL

- PostgreSQL 15 managed instance
- Auth and Task services connect via `cloud-sql-python-connector` with IAM authentication — no plaintext passwords in connection strings
- Broker Worker uses `psycopg2` (synchronous) with the same Cloud SQL connector
- Alembic migrations run automatically at service startup using the `DATABASE_URL` environment variable injected at deploy time

### Google Cloud Memorystore (Redis)

- Fully managed Redis 7 instance within the VPC
- Replaces self-hosted Redis entirely in production — no Redis container in Cloud Run
- Used for: task queue (RPUSH/BLPOP), quota counters (Lua atomic), progress reporting (HSET + PUBLISH), cancellation signals (SET with TTL)
- Accessible from Cloud Run only through the VPC Connector — not publicly reachable

### Google Cloud Storage

- Bucket configured via `GCS_BUCKET` environment variable
- Agent Worker authenticates via the Cloud Run service account's IAM role — no API key in code
- Generated images are uploaded with `google-cloud-storage` SDK; object name is a UUID to avoid collisions
- Presigned URLs (time-limited) are returned to the frontend for direct image loading

### Google Artifact Registry

- Repository hosts Docker images for all 7 services
- Images tagged with both `github.sha` (immutable, used in Cloud Run deployments) and `latest` (human-friendly reference)
- GAR is in the same region as Cloud Run to minimize image pull latency
- Access controlled via IAM: the GitHub deploy service account has `roles/artifactregistry.writer`; Cloud Run runtime SA has `roles/artifactregistry.reader`

### Google IAM — Service Account Architecture

Each Cloud Run service runs under a **dedicated service account** with only the permissions it needs:

| Service | Service Account | Key Permissions |
|---------|----------------|-----------------|
| API Gateway | `api-gateway-sa` | `run.invoker` on downstream services |
| Auth Service | `auth-service-sa` | `cloudsql.client` |
| Task Service | `task-service-sa` | `cloudsql.client` |
| Broker Worker | `broker-worker-sa` | `cloudsql.client`, `run.invoker` on Agent Worker |
| Agent Worker | `agent-worker-sa` | `storage.objectAdmin` on GCS bucket, `aiplatform.user` (Gemini) |
| Quota Service | `quota-service-sa` | Memorystore access via VPC |
| Frontend | `frontend-sa` | `run.invoker` on API Gateway |

This principle-of-least-privilege setup means a compromise of one service cannot escalate to control other GCP resources.

---

## CI/CD Pipeline

The platform has a **fully automated, end-to-end CI/CD pipeline** on GitHub Actions. Every push to the `main` branch triggers service-specific deploy workflows. No manual deployment steps are required.

### Workflow Triggers

Each service has its own workflow file that triggers on:
- Push to `main` branch **with changes in the service's directory** (path filtering)
- Manual `workflow_dispatch` for on-demand redeployment

This means pushing a change to `services/agent-worker/` only redeploys the agent worker — other services are untouched.

### Deployment Steps (per service)

```
1. actions/checkout@v4
       │
       ▼
2. google-github-actions/auth@v2
   └─ Workload Identity Federation (OIDC token — no JSON key file)
       │
       ▼
3. gcloud auth configure-docker {GAR_LOCATION}-docker.pkg.dev
       │
       ▼
4. docker build (multi-stage)
   └─ Tags: IMAGE:${{ github.sha }}  +  IMAGE:latest
       │
       ▼
5. docker push both tags to Artifact Registry
       │
       ▼
6. gcloud run deploy
   ├─ --image IMAGE:${{ github.sha }}  (immutable pinned tag)
   ├─ --region, --project, --service-account
   ├─ --vpc-connector (private Memorystore/SQL access)
   ├─ --set-env-vars (all secrets injected from GitHub Secrets)
   └─ Traffic immediately shifts to new revision
       │
       ▼
7. Deployment Summary written to GitHub Actions job summary
   └─ Includes live Cloud Run service URL
```

### Workload Identity Federation — Zero Secret Files

GitHub Actions authenticates to GCP without any JSON service account key files. Instead:
- A **Workload Identity Pool** is configured in GCP with a GitHub OIDC provider
- The pool is bound to the deploy service account via a condition on `repository` claim
- `google-github-actions/auth@v2` exchanges the GitHub OIDC token for a short-lived GCP access token at runtime
- No long-lived credentials are stored anywhere — rotation is automatic

### Bootstrap Deploy

`deploy-all.yml` is a manually triggered workflow that builds and deploys all 7 services sequentially. Used for first-time setup or full platform resets.

---

## Security

### Secrets Management — GitHub Secrets

**No sensitive values exist anywhere in the codebase.** All secrets are stored in **GitHub Actions Secrets** and injected as environment variables at deploy time via `--set-env-vars` in `gcloud run deploy`.

Secrets stored in GitHub include:
- `JWT_SECRET_KEY` — HMAC signing key for user tokens
- `REMOVEBG_API_KEY` — RemoveBG background removal API
- `GCP_PROJECT_ID`, `GCP_REGION`, `GAR_LOCATION`, `GAR_REPO` — GCP targeting
- `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT` — CI auth
- `REDIS_URL`, `DATABASE_URL` — infrastructure connection strings
- All Gemini model names, ChromaDB config, GCS bucket name
- Cloud SQL connection parameters

In-flight secrets never touch the filesystem — they live only as Cloud Run environment variables accessible to the running container.

### Additional Security Measures

- **Non-root Docker containers** — all Python service Dockerfiles create and switch to a non-root `appuser`
- **Private networking** — Memorystore and Cloud SQL are not publicly accessible; reachable only via VPC Connector from within Cloud Run
- **Service isolation** — each Cloud Run service has its own SA with minimal IAM roles; no service can impersonate another
- **Internal JWT claims** — inter-service calls use `iss="internal-service"` tokens; user tokens are never forwarded between services
- **SlowAPI rate limiting** — API Gateway blocks brute-force and scraping attempts
- **Atomic quota operations** — Lua scripts in Quota Service prevent race conditions in concurrent quota checks

---

## Technology Stack

### Backend

| Category | Technology | Notes |
|----------|-----------|-------|
| Language | Python 3.12 | All backend services |
| Web framework | FastAPI | API Gateway, Auth, Task, Quota, Broker |
| ASGI server | Uvicorn | Production-grade, async |
| Agent HTTP server | aiohttp | Agent Worker (avoids FastAPI overhead for long-running tasks) |
| AI orchestration | LangGraph | StateGraph-based workflow management |
| AI models | Google Gemini 2.5 Flash / Flash-Lite / Image | All inference via Vertex AI |
| Gemini SDK | `google-genai` | Direct SDK, not LangChain's wrapper |
| Vector database | ChromaDB | Local persistent store pre-warmed in Docker build |
| ORM | SQLAlchemy 2.x (async) | Fully async, type-safe queries |
| DB driver | asyncpg | PostgreSQL async adapter |
| Sync DB driver | psycopg2 | Broker Worker (threading-based) |
| DB migrations | Alembic | Auto-runs on service startup |
| Cache / Queue | Redis 7 (Memorystore) | Task queue, quotas, progress, cancellation |
| Object storage | Google Cloud Storage | Signed-URL image delivery |
| Image processing | Pillow | Canvas composition, alpha channel handling |
| HTTP client | httpx (async) | All inter-service calls |
| Auth | PyJWT + bcrypt | HS256 tokens, bcrypt work factor 12 |
| Rate limiting | SlowAPI | FastAPI-native Redis-backed limiter |
| Validation | Pydantic v2 | Request/response schemas, settings |
| Logging | python-json-logger | Structured JSON logs for Cloud Logging |
| Cloud DB auth | cloud-sql-python-connector | IAM-based Cloud SQL access |

### Frontend

| Category | Technology | Notes |
|----------|-----------|-------|
| Framework | Next.js 14 | App Router, SSR + client components |
| Language | TypeScript 5 | Strict mode |
| UI layer | React 18 | |
| Styling | TailwindCSS 3 | Utility-first |
| Components | shadcn/ui + Radix UI | Accessible headless primitives |
| Animations | Framer Motion | Page transitions, micro-animations |
| State | Zustand | Auth state, lightweight |
| Forms | react-hook-form + zod | Schema-driven validation |
| HTTP | axios | Interceptor-based token refresh |
| Charts | recharts | Results dashboard visualizations |
| Icons | lucide-react | |
| Dates | date-fns | |

### Infrastructure

| Category | Technology |
|----------|-----------|
| Containerization | Docker (multi-stage builds) |
| Local orchestration | Docker Compose |
| Production hosting | Google Cloud Run (serverless) |
| Database | Google Cloud SQL — PostgreSQL 15 |
| Cache / Queue | Google Cloud Memorystore — Redis 7 |
| Image registry | Google Artifact Registry |
| Object storage | Google Cloud Storage |
| CI/CD | GitHub Actions |
| Auth (CI→GCP) | Workload Identity Federation (OIDC) |
| Private networking | VPC Connector |

---

## Environment Variables

All variables are defined in `.env.example`. Copy it to `.env` for reference; actual values in production come from GitHub Secrets injected at deploy time.

### Infrastructure

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=...
POSTGRES_DB=platform
DATABASE_URL=postgresql+asyncpg://...
BROKER_DATABASE_URL=postgresql+psycopg2://...
REDIS_URL=redis://...
```

### Service URLs

```env
AUTH_SERVICE_URL=http://auth-service:8080
TASK_SERVICE_URL=http://task-service:8080
QUOTA_SERVICE_URL=http://quota-service:8080
AGENT_WORKER_URL=http://agent-worker:8080
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Authentication

```env
JWT_SECRET_KEY=<strong-random-value>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
REGISTRATION_ENABLED=true
```

### Quota

```env
QUOTA_LIMIT=10
QUOTA_TTL_SECONDS=86400
```

### Broker / Retry

```env
TASK_QUEUE_NAME=task_queue
MAX_RETRY_COUNT=3
RETRY_BASE_DELAY=2.0
```

### AI Models

```env
GOOGLE_CLOUD_PROJECT=<project-id>
GOOGLE_CLOUD_LOCATION=us-central1

RIVAL_DISCOVERY_MODEL=gemini-2.5-flash-lite
RIVAL_RESEARCH_MODEL=gemini-2.5-flash-lite
RIVAL_SENTIMENT_MODEL=gemini-2.5-flash
RIVAL_TRENDS_MODEL=gemini-2.5-flash
RIVAL_MARKET_GAP_MODEL=gemini-2.5-flash
RIVAL_PRICING_MODEL=gemini-2.5-flash
SEO_OPTIMIZER_MODEL=gemini-2.5-flash

GEMINI_IMAGE_MODEL=gemini-2.5-flash-image
REMOVEBG_API_KEY=<removebg-api-key>
GCS_BUCKET=<bucket-name>
```

### RAG

```env
CHROMA_COLLECTION_NAME=seo_chunks
CHROMA_TOP_K=6
```

### Google Cloud (Production Deploy)

```env
GCP_PROJECT_ID=...
GCP_REGION=us-central1
GAR_LOCATION=us-central1
GAR_REPO=...
CLOUD_SQL_INSTANCE=<project>:<region>:<instance>
VPC_CONNECTOR=...
GCP_WORKLOAD_IDENTITY_PROVIDER=projects/.../workloadIdentityPools/.../providers/...
GCP_SERVICE_ACCOUNT=github-deploy-sa@...iam.gserviceaccount.com
```

---

## Local Development Notice

> **The codebase is currently configured for Google Cloud deployment and cannot be run fully locally without additional setup.**

Specifically, the following components are cloud-bound:

- **Google Gemini / Vertex AI** — Agent Worker calls Gemini via `GOOGLE_CLOUD_PROJECT` and Application Default Credentials. Running locally requires `gcloud auth application-default login` and valid Vertex AI quota in the configured project.
- **Google Cloud Storage** — Image generation uploads to GCS using the service account's IAM role. Local execution would require a service account key file (`GOOGLE_APPLICATION_CREDENTIALS`) and write access to the configured bucket.
- **RemoveBG API** — Requires a valid `REMOVEBG_API_KEY`; no local substitute.
- **Cloud SQL** — In production, connections use `cloud-sql-python-connector`. For local Docker Compose, `DATABASE_URL` must point to the local PostgreSQL container, not the Cloud SQL instance.
- **Memorystore** — The VPC-private Redis instance is unreachable outside GCP. For local development, use the Redis container in Docker Compose and set `REDIS_URL=redis://redis:6379/0`.

To run locally you would need to:
1. Replace all GCS upload calls with local filesystem writes
2. Set up Application Default Credentials for Gemini
3. Use a local Redis and PostgreSQL via Docker Compose
4. Provide a valid `REMOVEBG_API_KEY`

The platform is fully functional end-to-end in the deployed Google Cloud environment.

---

## Team & Development Process

The team maintained a **balanced task distribution** throughout the hackathon, with each member owning complete vertical slices (a service + its frontend integration) rather than horizontal layers. This avoided bottlenecks and allowed parallel progress across the stack.

Development followed a **two-environment model**:
- **`main` branch** — the production environment; always reflects what is live on Google Cloud Run. Any push here triggers an automatic CI/CD deployment.
- **`dev` branch** — the shared integration environment connected to the same Cloud SQL and Memorystore infrastructure. Developers push daily work here; it serves as a staging layer that mirrors production data flows before promotion to `main`.

This setup meant the team could test real AI workflow runs, actual database writes, and live quota enforcement on `dev` without risk to the demo environment on `main`.

---

*BTK Hackathon 2026 — organized by BTK Akademi, Türkiye Girişimcilik Vakfı and Google Turkey*
