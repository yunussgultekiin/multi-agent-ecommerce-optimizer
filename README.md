# Multi-Agent E-Commerce Optimizer, Synapse

> **BTK Hackathon 2026 · Google Gemini Track**  
> AI destekli çok-ajanlı e-ticaret satıcı destek platformu

---

## İçindekiler

- [Proje Hakkında](#proje-hakkında)
- [Mimari Genel Bakış](#mimari-genel-bakış)
- [Servisler](#servisler)
- [Yapay Zeka Katmanı — Agent Worker](#yapay-zeka-katmanı--agent-worker)
- [Veri Akışı](#veri-akışı)
- [Teknoloji Yığını](#teknoloji-yığını)
- [Ortam Değişkenleri](#ortam-değişkenleri)
- [Yerel Geliştirme](#yerel-geliştirme)
- [Deployment — Google Cloud Run](#deployment--google-cloud-run)
- [CI/CD Pipeline](#cicd-pipeline)
- [Katkı Sağlama](#katkı-sağlama)

---

## Proje Hakkında

E-ticaret satıcıları Trendyol, Amazon ve Hepsiburada gibi platformlarda rakipleri analiz etmek, fiyatlandırma stratejisi oluşturmak ve ürün listelemelerini optimize etmek için cidli zaman harcıyor. Bu platform bu süreci tamamen otomatize eder:

1. **Rakip Analizi** — Satıcının ürününe benzer rakipleri keşfeder, her birini derinlemesine araştırır, müşteri duygu analizini (sentiment) ve trend verilerini çıkarır, pazar boşluklarını tespit eder ve optimal fiyat aralığını hesaplar.
2. **SEO & Görsel Optimizasyonu** — Rakip analizinin çıktısını kullanarak platforma özgü SEO metinleri (başlık, açıklama, bullet point, tag) üretir ve arka plan kaldırılmış, platforma göre boyutlandırılmış ürün görseli oluşturur.

Her şey asenkron bir görev kuyruğu üzerinde çalışır; kullanıcı sonuçları gerçek zamanlı ilerleme takibiyle bekler.

---

## Mimari Genel Bakış

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                  │
│              Port 3000  —  SSR + Client Polling          │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTP
┌─────────────────────────▼───────────────────────────────┐
│                    API Gateway (FastAPI)                  │
│  Port 8000  —  JWT doğrulama · CORS · SlowAPI rate limit │
│  Proxy:  /auth → Auth Svc · /analyze → Task+Quota Svc   │
└────┬──────────┬──────────────────────────────┬──────────┘
     │          │                              │
     ▼          ▼                              ▼
┌────────┐ ┌──────────┐                 ┌────────────┐
│  Auth  │ │  Task    │                 │   Quota    │
│  Svc   │ │  Svc     │                 │   Svc      │
│  8001  │ │  8002    │                 │  8003      │
│  PG+JWT│ │  PG+Redis│                 │  Redis Lua │
└────────┘ └────┬─────┘                 └────────────┘
                │ Redis Task Queue
                ▼
        ┌───────────────┐
        │ Broker Worker │
        │    Port 8004  │
        │ Retry · Poll  │
        └───────┬───────┘
                │ HTTP POST
                ▼
        ┌───────────────────────────────────────────┐
        │              Agent Worker                  │
        │               Port 8005                    │
        │                                            │
        │  ┌─────────────┐     ┌──────────────────┐ │
        │  │ Rival Graph │────▶│    SEO Graph     │ │
        │  │  LangGraph  │     │    LangGraph     │ │
        │  └─────────────┘     └──────────────────┘ │
        │                                            │
        │  Google Gemini 2.5 · ChromaDB · GCS       │
        └───────────────────────────────────────────┘
```

Tüm servisler Docker Compose ile ayağa kalkar; production'da her biri ayrı bir Google Cloud Run servisidir.

---

## Servisler

### API Gateway — `services/api-gateway` (Port 8000)

Platforma açılan tek kapı. Dışarıdan gelen tüm HTTP isteklerini karşılar.

**Sorumlulukları:**
- JWT middleware ile her isteği doğrular (Auth Service'e çağrı)
- CORS middleware — frontend origin'ine izin verir
- SlowAPI rate limiting — kötüye kullanımı engeller
- `/analyze` — Quota Service'e kotayı kontrol ettirir, Task Service'e görevi oluşturur, Redis kuyruğuna iter
- `/auth` — Auth Service'e proxy
- `/upload` — Google Cloud Storage presigned URL üretimi (multipart form desteği)
- `/health` — tüm downstream servislerin sağlık kontrolü

**Teknik seçimler:**
- `httpx.AsyncClient` — downstream çağrılar için async HTTP; timeout ve retry ayarlı
- `slowapi` — FastAPI uyumlu token-bucket rate limiting; Redis'e dayalı
- Güvenlik ihlali olmaması için Auth Service'e her istek başına `Authorization` header'ı iletilmez; token yalnızca doğrulama amacıyla kullanılır

---

### Auth Service — `services/auth-service` (Port 8001)

Kullanıcı kimlik doğrulama ve JWT yönetimi.

**Özellikler:**
- Kayıt (e-posta + bcrypt şifre hash) — `REGISTRATION_ENABLED` flag'i ile kapatılabilir
- Login → access token (30 dk) + refresh token (7 gün)
- `/internal/validate` endpoint'i — API Gateway'in token doğrulaması için
- Alembic ile veritabanı migration yönetimi

**Teknik seçimler:**
- `SQLAlchemy 2.x async` + `asyncpg` — non-blocking veritabanı IO
- `PyJWT` — RS256 yerine HS256 tercih edildi; hackathon scope'u için yeterli güvenlik düzeyi
- `python-bcrypt` — work factor 12, şifre hash'leme için
- Production'da `cloud-sql-python-connector` ile Cloud SQL IAM auth

---

### Task Service — `services/task-service` (Port 8002)

Görev yaşam döngüsü yönetimi ve sonuç depolama.

**Görev durumları:**
```
pending → running → completed
                 └─ failed
                 └─ cancelled
```

**Özellikler:**
- UUID tabanlı görev ID'leri
- Görev payload'ı (kullanıcı girişi) veritabanında JSON olarak saklanır
- `seo_tone` alanı — SEO metninin tonu: `casual | professional | premium`
- Sayfalı görev listeleme (kullanıcıya göre filtrelenmiş)
- `TaskResult` tablosu — tamamlanan görevin JSON sonucu ayrı tabloda
- Broker Worker'ın progress güncellemeleri için `/tasks/{id}/status` PATCH endpoint'i
- Redis pub/sub üzerinden gerçek zamanlı progress event'leri (frontend polling ile tüketilir)

---

### Quota Service — `services/quota-service` (Port 8003)

Kullanıcı başına analiz kotası.

**Nasıl çalışır:**
- Redis'te `quota:{user_id}` anahtarı, Lua script ile atomik INCR + EXPIRE
- `QUOTA_LIMIT` (varsayılan: 10) aşılırsa 429 döner
- TTL: 86400 saniye (24 saat) — gün bazlı pencere
- Lua script kullanımı: INCR ve EXPIRE arasında race condition'ı önlemek için

---

### Broker Worker — `services/broker-worker` (Port 8004)

Redis kuyruğunu dinleyip Agent Worker'a görev dağıtan orchestrator.

**Akış:**
1. `BLPOP` ile Redis kuyruğundan (varsayılan: `task_queue`) görev mesajı alır
2. Task Service'e `status = running` günceller
3. Agent Worker'a `POST /run` isteği atar (async, 202 Accepted beklenir)
4. Hata durumunda exponential backoff ile retry: `base_delay * 2^attempt`
5. `MAX_RETRY_COUNT` (3) aşılırsa Task Service'e `status = failed` yazar

**Teknik seçimler:**
- `threading` + asyncio event loop — BLPOP bloklamasını ana döngüden ayırmak için
- Retry state veritabanında tutulur — servis yeniden başlatılsa bile retry sayısı korunur
- Agent Worker'ın 202 dönmesi beklenir; 500 alınırsa retry sayılır

---

### Agent Worker — `services/agent-worker` (Port 8005)

Tüm yapay zeka iş yükünü yürüten ana servis.

> Detaylı açıklama için: [Yapay Zeka Katmanı](#yapay-zeka-katmanı--agent-worker)

---

### Frontend — `frontend` (Port 3000)

Next.js 14 ile yazılmış Türkçe arayüz.

**Sayfalar:**

| Rota | Açıklama |
|------|----------|
| `/` | Landing — özellikler, nasıl çalışır, CTA |
| `/login` | Giriş formu |
| `/register` | Kayıt formu |
| `/dashboard` | Kullanıcının analizleri |
| `/dashboard/analyze` | Yeni analiz oluştur |
| `/dashboard/analyze/[taskId]/progress` | Gerçek zamanlı ilerleme |
| `/dashboard/result/[taskId]` | Sonuç görselleştirme |
| `/dashboard/history` | Geçmiş analizler |

**Teknik seçimler:**
- `Next.js 14 App Router` — SSR + client component mimarisi
- `Zustand` — global auth state management; lightweight, Redux karmaşıklığı olmadan
- `shadcn/ui` + `Radix UI` — erişilebilir, unstyled bileşen kütüphanesi; TailwindCSS ile özelleştirildi
- `Framer Motion` — sayfa geçişleri ve animasyonlar
- `react-hook-form` + `zod` — form validasyonu; şema-driven type-safe doğrulama
- `axios` — HTTP client; interceptor ile token yenileme
- Progress tracking: Task Service'e düzenli polling (WebSocket yerine; deployment karmaşıklığını azaltır)

---

## Yapay Zeka Katmanı — Agent Worker

### LangGraph Workflow'ları

Agent Worker iki ayrı LangGraph `StateGraph` içerir. Her node, `NodeRunner` middleware'i tarafından sarılır; bu middleware:
- Her node başlamadan önce Redis'ten **iptal sinyali** kontrol eder (`cancelled:{task_id}` key'i)
- Node başlarken Task Service'e progress rapor eder
- Node tamamlanınca completion_pct'yi günceller

#### Rival Graph (Rakip Analizi)

```
START
  │
  ▼
discover_competitors (10%)
  │ — Gemini 2.5 Flash Lite ile rakip isimleri keşfeder
  ▼
research_competitors (25%)
  │ — Her rakibi derinlemesine araştırır
  ├─────────────────────────────────┐
  ▼                                 ▼
analyze_sentiment (40%)      analyze_trends (40%)
  │ — Müşteri yorumları            │ — Pazar trendleri
  ├──────────────┐        ┌────────┘
  ▼              ▼        ▼
market_gap (72%)    pricing (72%)
  │ — Pazar boşluğu    │ — Optimal fiyat aralığı
  └──────┬──────────────┘
         ▼
      finalize (55%)
         │ — rival_json çıktısı oluşturulur
         ▼
        END
```

> `analyze_sentiment` ve `analyze_trends` paralel çalışır; `market_gap` ve `pricing` da paralel çalışır. LangGraph bu branching'i otomatik yönetir.

#### SEO Graph (SEO & Görsel)

```
START
  ├────────────────────────────────┐
  ▼                                ▼
generate_seo (80%)         generate_image (90%)
  │ — RAG destekli SEO           │ — Gemini görsel üretimi
  │   metinleri                  │   + RemoveBG arka plan kaldırma
  └──────────┬───────────────────┘
             ▼
          finalize (100%)
             │ — Sonuç Task Service'e yazılır
             ▼
            END
```

> `generate_seo` ve `generate_image` paralel çalışır.

---

### Agent Tool'ları

#### Rival Agent Tools (`services/agent-worker/app/tools/rival_agent_tools/`)

| Tool | Gemini Modeli | Görev |
|------|---------------|-------|
| `competitor_discovery` | `gemini-2.5-flash-lite` | Ürün adı ve platforma göre rakip isimleri keşfeder |
| `competitor_research` | `gemini-2.5-flash-lite` | Her rakip için fiyat, özellik, puan, yorum sayısı araştırır |
| `sentiment_analysis` | `gemini-2.5-flash` | Rakip yorumlarından pozitif/negatif duygu analizi |
| `trend_analysis` | `gemini-2.5-flash` | Kategori trendleri ve mevsimsel değişimler |
| `market_gap_analyzer` | `gemini-2.5-flash` | Rakiplerin karşılamadığı pazar boşluklarını tespit eder |
| `smart_pricing_engine` | `gemini-2.5-flash` | Optimum fiyat aralığı ve varyant-bazlı öneri |

**Model seçim mantığı:**  
Discovery ve Research aşamaları yüksek hacimli, nispeten basit extraction görevleri olduğundan `gemini-2.5-flash-lite` tercih edildi (hız + maliyet). Daha derin analiz gerektiren aşamalar (sentiment, trends, gap, pricing) `gemini-2.5-flash` kullanır.

#### SEO Agent Tools (`services/agent-worker/app/tools/seo_agent_tools/`)

**SEO Optimizer:**
- `gemini-2.5-flash` + ChromaDB RAG
- `CHROMA_COLLECTION_NAME=seo_chunks`, `CHROMA_TOP_K=6` — e-ticaret SEO kuralları chunk'ları vektör veritabanında
- `json_prompt_rules.py` — platforma özgü JSON şema kuralları; başlık uzunluğu, karakter limiti, tag sayısı vb.
- `seo_tone` parametresine göre metin tonu ayarlanır: `casual | professional | premium`

**Image Generation Pipeline:**
1. `gemini-2.5-flash-preview-image-generation` ile ürün görseli üretilir (beyaz arka planlı stüdyo fotoğrafı)
2. `background_removal.py` — RemoveBG API ile arka plan kaldırılır
3. `utils_image.py` — Platform-spesifik canvas boyutuna göre görsel oluşturulur:

| Platform | Canvas Boyutu | Ürün Oranı |
|----------|--------------|------------|
| Trendyol | 1200 × 1800 | %78 |
| Amazon | 1600 × 1600 | %76 |
| Hepsiburada | 1200 × 1200 | %76 |

4. `select_variant()` — `competitor_variant_overlap` verisine bakarak kullanıcının hangi varyantına odaklanılacağına karar verir (en az rakip çakışması)
5. Sonuç Google Cloud Storage'a yüklenir; imzalı URL göreve eklenir

---

### Google Gemini Entegrasyonu

- `google-genai` SDK kullanılır (LangChain'in Google entegrasyonu değil; daha az abstraction, daha fazla kontrol)
- `GOOGLE_CLOUD_PROJECT` ve `GOOGLE_CLOUD_LOCATION` — Vertex AI endpoint konfigürasyonu
- Her model kendi `GenerationConfig`'ini taşır (temperature, response_mime_type: `application/json`)
- Tüm model yanıtları JSON parse edilir; parse hatası `WorkflowError` fırlatır

---

### RAG (Retrieval-Augmented Generation)

SEO optimizasyonunda `ChromaDB` kullanılır:

- `chroma_collection_name=seo_chunks` — e-ticaret SEO en iyi pratiklerini barındıran chunk koleksiyonu
- `TOP_K=6` — en alakalı 6 chunk context'e eklenir
- Vektör embedding: ChromaDB'nin default embedding fonksiyonu
- Agent Worker başlarken ChromaDB cache pre-warm edilir (Dockerfile'da `HF_HOME` env var ile Hugging Face model cache konumu ayarlı)

---

### İptal Mekanizması

Kullanıcı analizi iptal ettiğinde:
1. API Gateway Redis'e `cancelled:{task_id}` key'ini yazar (TTL: 1 saat)
2. `NodeRunner.wrap()` her node başlamadan önce bu key'i kontrol eder
3. Key mevcutsa node çalıştırılmaz, `{"cancelled": True}` döner
4. LangGraph `_cancel_or()` koşullu edge'i `END`'e yönlendirir
5. `WorkflowErrorHandler` Task Service'e `status=cancelled` yazar

---

### Servis İletişimi — `services/shared/`

Servisler arası HTTP çağrıları `internal_client.py` tarafından yönetilir:

- `iss="internal-service"` claim'li JWT token — dış kullanıcı token'larından ayırt etmek için
- Token cache: 30 saniyelik yenileme buffer'ı ile 5 dakika TTL
- `asyncio.Lock` ile thread-safe token yenileme
- `InternalHttpClient` — tüm servisler bu sınıfı kullanır; her istek otomatik token ekler

---

## Veri Akışı

### Analiz Oluşturma (End-to-End)

```
Kullanıcı formu gönderir
    ↓
API Gateway:
  1. JWT doğrular (Auth Service)
  2. Quota kontrol eder (Quota Service) — kota doluysa 429
  3. Task oluşturur (Task Service) → task_id döner
  4. Redis kuyruğuna {"task_id": ..., "payload": ...} iter
  5. Frontend'e {task_id} döner

Broker Worker (arka planda):
  1. BLPOP ile mesajı alır
  2. Task status → running
  3. Agent Worker'a POST /run

Agent Worker:
  1. workflow_type'a göre Rival veya SEO graph seçer
  2. LangGraph workflow'u asenkron çalıştırır
  3. Her node: Redis'e progress event, Task Service'e status güncelleme
  4. Tamamlanınca Task Service'e result kaydeder

Frontend (polling):
  1. /tasks/{id}/status'u her 2 sn'de bir polling
  2. Progress bar güncellenir
  3. status=completed → result sayfasına yönlendirir
```

### İki Aşamalı Analiz

Bazı task'lar iki aşamalıdır: önce Rival Workflow, ardından (rival_json çıktısını input olarak alarak) SEO Workflow çalışır. Bu `run_rival_workflow` → `build_seo_state_from_rival` → `run_seo_workflow` zinciriyle sağlanır; aynı `task_id` korunur.

---

## Teknoloji Yığını

### Backend

| Kategori | Teknoloji | Versiyon |
|----------|-----------|----------|
| Dil | Python | 3.12 |
| Web Framework | FastAPI | ≥0.110 |
| ASGI Server | Uvicorn | ≥0.29 |
| Agent Worker HTTP | aiohttp | ≥3.9 |
| AI Orchestration | LangGraph | latest |
| AI Models | Google Gemini 2.5 | Flash / Flash-Lite / Image |
| Vector DB | ChromaDB | latest |
| ORM | SQLAlchemy 2.x (async) | ≥2.0 |
| DB Driver | asyncpg | ≥0.29 |
| Migrations | Alembic | ≥1.13 |
| Cache / Queue | Redis | 7.x |
| Storage | Google Cloud Storage | — |
| Image Processing | Pillow | ≥10 |
| HTTP Client | httpx | ≥0.27 |
| Auth | PyJWT + bcrypt | — |
| Rate Limiting | SlowAPI | ≥0.0.7 |
| Validation | Pydantic v2 | ≥2.0 |
| Logging | python-json-logger | — |

### Frontend

| Kategori | Teknoloji | Versiyon |
|----------|-----------|----------|
| Framework | Next.js | 14.2 |
| UI Library | React | 18 |
| Dil | TypeScript | 5.x |
| Stil | TailwindCSS | 3.x |
| Bileşenler | shadcn/ui + Radix UI | — |
| Animasyon | Framer Motion | ≥10 |
| State | Zustand | ≥4 |
| Formlar | react-hook-form + zod | — |
| HTTP | axios | ≥1.6 |
| Grafikler | recharts | ≥2 |
| Tarih | date-fns | ≥3 |

### Altyapı

| Kategori | Teknoloji |
|----------|-----------|
| Container | Docker (multi-stage build) |
| Orchestration (local) | Docker Compose |
| Orchestration (prod) | Google Cloud Run |
| Veritabanı | PostgreSQL 15 (Cloud SQL) |
| Cache/Queue | Redis 7 (Memorystore) |
| Image Registry | Google Artifact Registry |
| Auth (CI/CD) | Workload Identity Federation |
| Proxy (local) | Nginx |

---

## Ortam Değişkenleri

Tüm değişkenler `.env.example`'dan kopyalanarak `.env` oluşturulur.

### Altyapı

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=...
POSTGRES_DB=platform
DATABASE_URL=postgresql+asyncpg://...
BROKER_DATABASE_URL=postgresql+psycopg2://...
REDIS_URL=redis://redis:6379/0
```

### Servis URL'leri

```env
AUTH_SERVICE_URL=http://auth-service:8080
TASK_SERVICE_URL=http://task-service:8080
QUOTA_SERVICE_URL=http://quota-service:8080
AGENT_WORKER_URL=http://agent-worker:8080
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Kimlik Doğrulama

```env
JWT_SECRET_KEY=<güçlü-rastgele-değer>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
REGISTRATION_ENABLED=true
```

### Kota

```env
QUOTA_LIMIT=10          # günlük maksimum analiz sayısı
QUOTA_TTL_SECONDS=86400 # pencere süresi (24 saat)
```

### Broker / Retry

```env
TASK_QUEUE_NAME=task_queue
MAX_RETRY_COUNT=3
RETRY_BASE_DELAY=2.0    # saniye; her retry'da 2 katına çıkar
```

### AI Modelleri

```env
GOOGLE_CLOUD_PROJECT=<proje-id>
GOOGLE_CLOUD_LOCATION=us-central1

RIVAL_DISCOVERY_MODEL=gemini-2.5-flash-lite
RIVAL_RESEARCH_MODEL=gemini-2.5-flash-lite
RIVAL_SENTIMENT_MODEL=gemini-2.5-flash
RIVAL_TRENDS_MODEL=gemini-2.5-flash
RIVAL_MARKET_GAP_MODEL=gemini-2.5-flash
RIVAL_PRICING_MODEL=gemini-2.5-flash
SEO_OPTIMIZER_MODEL=gemini-2.5-flash

GEMINI_IMAGE_MODEL=gemini-2.5-flash-image
REMOVEBG_API_KEY=<removebg-api-anahtarı>
GCS_BUCKET=<bucket-adı>
```

### RAG

```env
CHROMA_COLLECTION_NAME=seo_chunks
CHROMA_TOP_K=6
```

### Google Cloud (Production)

```env
GCP_PROJECT_ID=...
GCP_REGION=us-central1
GAR_LOCATION=us-central1
GAR_REPO=...
CLOUD_SQL_INSTANCE=<proje>:<bölge>:<instance>
VPC_CONNECTOR=...
GCP_WORKLOAD_IDENTITY_PROVIDER=...
GCP_SERVICE_ACCOUNT=...
```

---

## Yerel Geliştirme

### Gereksinimler

- Docker Desktop (veya Docker Engine + Compose plugin)
- Google Cloud kredansiyeli (Application Default Credentials) — Gemini API için
- RemoveBG API anahtarı (görsel pipeline için)

### Başlatma

```bash
# Repo'yu klonla
git clone https://github.com/<org>/multi-agent-ecommerce-optimizer.git
cd multi-agent-ecommerce-optimizer

# Ortam değişkenlerini yapılandır
cp .env.example .env
# .env dosyasını düzenle: JWT_SECRET_KEY, API anahtarları vb.

# Tüm servisleri ayağa kaldır
docker compose up --build

# Logları takip et (belirli servis)
docker compose logs -f agent-worker
```

Servisler hazır olduğunda:
- Frontend: http://localhost:3000
- API Gateway: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs

### Veritabanı Migration

```bash
# Auth Service migration
docker compose exec auth-service alembic upgrade head

# Task Service migration
docker compose exec task-service alembic upgrade head
```

### Geliştirme İpuçları

```bash
# Sadece altyapıyı ayağa kaldır (DB + Redis), servisleri local çalıştır
docker compose up postgres redis

# Agent Worker'ı hot-reload ile çalıştır
cd services/agent-worker
pip install -r requirements.txt
python -m app.main
```

---

## Deployment — Google Cloud Run

Her servis bağımsız bir Cloud Run servisidir. Deployment sırasında:

1. Docker image multi-stage build ile oluşturulur
2. Google Artifact Registry'e push edilir (commit SHA + `latest` tag)
3. Cloud Run servisi güncellenir; traffic anında yeni revision'a yönlendirilir
4. PostgreSQL bağlantısı `cloud-sql-python-connector` ile Cloud SQL IAM auth üzerinden kurulur
5. Servisler arası iletişim Cloud Run internal URL'leri üzerinden (VPC Connector)

### Dockerfile Stratejisi

Tüm Python servisleri iki aşamalı build kullanır:

```dockerfile
# Aşama 1: Builder
FROM python:3.12-slim AS builder
RUN pip install --user -r requirements.txt

# Aşama 2: Runtime
FROM python:3.12-slim
COPY --from=builder /root/.local /root/.local
# Non-root user — güvenlik için
USER appuser
```

Frontend standalone Next.js modunda build edilir:

```dockerfile
FROM node:20-alpine AS builder
RUN npm ci && npm run build

FROM node:20-alpine AS runner
COPY --from=builder /app/.next/standalone ./
```

Agent Worker'da ChromaDB Hugging Face model cache pre-warm'u Dockerfile'da yapılır:
```dockerfile
ENV HF_HOME=/app/.cache/huggingface
RUN python -c "import chromadb; ..."
```

---

## CI/CD Pipeline

`.github/workflows/` altında her servis için ayrı workflow dosyası bulunur.

### Workflow Adımları

```yaml
1. Checkout kodu
2. Google Cloud auth (Workload Identity Federation — OIDC, secret yok)
3. Docker Buildx ile multi-platform image build
4. GAR'a push: <sha> ve latest tag
5. Cloud Run'a deploy: --image <sha-tag> --region us-central1
```

### Workload Identity Federation

GitHub Actions'tan GCP'ye güvenli erişim için service account key'i kullanılmaz. Bunun yerine:
- GCP'de Workload Identity Pool + GitHub Provider tanımlı
- GitHub repo'nun `subject` claim'i SA'ya bind edilmiş
- Her deploy OIDC token ile doğrulanır

### deploy-all.yml

Tüm servisleri sıralı olarak deploy eden manuel tetikleyicili workflow. İlk kurulum veya tam sıfırlama için kullanılır.

---

## Katkı Sağlama

### Branch Stratejisi

```
main  →  Demo/production. Her zaman çalışır durumda olmalı.
dev   →  Günlük geliştirme. Herkes buraya push eder.
```

- `main`'e doğrudan push yapılmaz
- Demo/milestone öncesi `dev → main` merge yapılır

### Commit Formatı (Conventional Commits)

```
<type>(<scope>): <ne yaptın>
```

**Type:**

| Type | Kullanım |
|------|----------|
| `feat` | Yeni özellik |
| `fix` | Bug düzeltme |
| `refactor` | Davranış değişikliği olmadan yeniden yazım |
| `test` | Test ekleme/güncelleme |
| `docs` | Dokümantasyon |
| `chore` | Bağımlılık, config vb. |
| `ci` | GitHub Actions |
| `perf` | Performans iyileştirme |

**Scope örnekleri:** `gateway`, `auth`, `quota`, `task`, `broker`, `agent`, `llm`, `frontend`, `db`, `cache`, `infra`

**Örnekler:**
```
feat(agent): add competitor variant overlap detection
fix(broker): handle redis connection timeout on startup
refactor(llm): switch discovery model to flash-lite for cost reduction
perf(image): cache removebg responses by image hash
```

### Gizlilik Kuralı

- API anahtarları, şifreler, JWT secret'ları asla commit'lenmez
- `.env` dosyası `.gitignore`'da
- CI/CD secret'ları GitHub Actions Secrets veya GCP Secret Manager'da

---

## Proje Yapısı

```
multi-agent-ecommerce-optimizer/
├── .github/
│   └── workflows/
│       ├── deploy-all.yml
│       ├── deploy-agent.yml
│       ├── deploy-api.yml
│       ├── deploy-auth.yml
│       ├── deploy-broker.yml
│       ├── deploy-frontend.yml
│       ├── deploy-quota.yml
│       └── deploy-task.yml
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js App Router sayfaları
│   │   ├── components/             # UI bileşenleri
│   │   └── lib/                    # Yardımcı fonksiyonlar, hooks
│   ├── package.json
│   └── Dockerfile
├── infra/
│   └── nginx.conf
├── services/
│   ├── shared/
│   │   └── internal_client.py      # Servisler arası JWT auth
│   ├── api-gateway/
│   │   └── app/
│   │       ├── main.py
│   │       ├── middleware/
│   │       └── routers/
│   ├── auth-service/
│   │   └── app/
│   │       ├── main.py
│   │       ├── models.py
│   │       ├── services.py
│   │       └── alembic/
│   ├── task-service/
│   │   └── app/
│   │       ├── main.py
│   │       ├── models.py
│   │       └── task_service.py
│   ├── quota-service/
│   │   └── app/
│   │       └── main.py
│   ├── broker-worker/
│   │   └── app/
│   │       ├── main.py
│   │       └── consumer.py
│   └── agent-worker/
│       └── app/
│           ├── main.py
│           ├── agents/
│           │   ├── rival_agent.py
│           │   ├── seo_agent.py
│           │   └── state.py
│           ├── workflow/
│           │   ├── rival_graph.py
│           │   ├── seo_graph.py
│           │   ├── node_runner.py
│           │   └── error_handler.py
│           ├── tools/
│           │   ├── rival_agent_tools/
│           │   │   ├── competitor_discovery/
│           │   │   ├── competitor_research/
│           │   │   ├── sentiment_analysis/
│           │   │   ├── trend_analysis/
│           │   │   ├── market_gap_analyzer/
│           │   │   └── smart_pricing_engine/
│           │   └── seo_agent_tools/
│           │       ├── seo_optimizer/
│           │       └── image_generation/
│           │           ├── tools_image.py
│           │           ├── models_image.py
│           │           ├── utils_image.py
│           │           └── background_removal.py
│           ├── task_client.py
│           └── redis.py
├── docker-compose.yml
├── .env.example
└── CONTRIBUTING.md
```

---

*BTK Hackathon 2026 — BİRİNCİYİZ ekibi*
