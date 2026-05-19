# Synapse — Çok Ajanlı E-Ticaret Optimizasyon Platformu

> **BTK Hackathon 2026** kapsamında geliştirilmiştir. Organizatörler: **BTK Akademi**, **Türkiye Girişimcilik Vakfı (TGVF)** ve **Google Türkiye**.  
> **Google Gemini 2.5** · **Google Cloud Run** üzerinde çalışmaktadır.

---

## İçindekiler

- [Ne Yapar?](#ne-yapar)
- [Mimari](#mimari)
- [Servisler](#servisler)
- [Yapay Zeka Katmanı — Agent Worker](#yapay-zeka-katmanı--agent-worker)
- [Uçtan Uca Veri Akışı](#uçtan-uca-veri-akışı)
- [Altyapı ve Google Cloud](#altyapı-ve-google-cloud)
- [CI/CD Pipeline](#cicd-pipeline)
- [Güvenlik](#güvenlik)
- [Teknoloji Yığını](#teknoloji-yığını)
- [Ortam Değişkenleri](#ortam-değişkenleri)
- [Yerel Geliştirme Notu](#yerel-geliştirme-notu)
- [Ekip ve Geliştirme Süreci](#ekip-ve-geliştirme-süreci)

---

## Ne Yapar?

Trendyol, Amazon ve Hepsiburada gibi platformlarda satış yapan e-ticaret satıcıları; rakip araştırması, fiyatlandırma stratejisi oluşturma ve ürün listeleme optimizasyonu için ciddi zaman harcamaktadır. Synapse bu sürecin tamamını uçtan uca otomatize eden bir çok ajanlı yapay zeka platformudur.

Satıcı, ürün bilgilerini (başlık, kategori, marka, varyantlar, hedef platform) girer. Platform iki ardışık yapay zeka iş akışı çalıştırır:

### 1. Rakip Analizi İş Akışı
- **Rakip Keşfi** — Hedef platformda satıcının ürününe benzer gerçek rakip ürünleri tespit eder
- **Rakip Araştırması** — Her rakip için derinlemesine veri toplar: fiyat, puan, yorum sayısı, öne çıkan özellikler
- **Duygu Analizi** — Rakip ürünlerin müşteri yorumlarından olumlu/olumsuz duygu temalarını çıkarır
- **Trend Analizi** — Ürün kategorisindeki pazar trendlerini ve mevsimsel talep değişimlerini belirler
- **Pazar Boşluğu Analizi** — Rakiplerin karşılamadığı müşteri ihtiyaçlarını ve fırsatları saptar
- **Akıllı Fiyatlandırma** — Rakip çakışmasına göre optimal fiyat aralığı ve varyant bazlı strateji önerir

### 2. SEO & Görsel İş Akışı (paralel çalışır)
- **SEO Optimizer** — Platforma özgü listeleme içeriği üretir (başlık, açıklama, bullet point, etiket, meta anahtar kelimeler); seçilen tona göre (`casual`, `professional`, `premium`) ChromaDB RAG deposuyla zenginleştirilmiş
- **Görsel Üretimi** — Gemini ile stüdyo kalitesi beyaz arka planlı ürün görseli oluşturur, RemoveBG API ile arka planı kaldırır, platforma özel canvas'a yerleştirir ve Google Cloud Storage'a yükler

Her şey asenkron bir görev kuyruğu üzerinde çalışır; satıcı tarayıcıda gerçek zamanlı ilerlemeyi izler ve analiz tamamlandığında kapsamlı bir sonuç panosu alır.

---

## Mimari

```
┌──────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js 14)                        │
│             Port 3000 · SSR + İstemci Taraflı Polling           │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTPS
┌──────────────────────────────▼───────────────────────────────────┐
│                       API Gateway (FastAPI)                       │
│   Port 8000 · JWT doğrulama · CORS · SlowAPI rate limiting      │
│   /auth → Auth Svc  /analyze → Task+Quota  /upload → GCS        │
└──────┬────────────────┬──────────────────────────────┬───────────┘
       │                │                              │
       ▼                ▼                              ▼
 ┌──────────┐    ┌─────────────┐               ┌────────────┐
 │   Auth   │    │    Task     │               │   Quota    │
 │  Service │    │   Service   │               │  Service   │
 │  :8001   │    │   :8002     │               │   :8003    │
 │Cloud SQL │    │Cloud SQL +  │               │Memorystore │
 │  + JWT   │    │Memorystore  │               │ Lua atomik │
 └──────────┘    └──────┬──────┘               └────────────┘
                        │ Redis Task Queue'ya Push
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
        │  │         Rival Graph (LangGraph)           │ │
        │  │  keşif → araştırma → [duygu‖trend]       │ │
        │  │  → [pazar_boşluğu‖fiyat] → finalize      │ │
        │  └────────────────────┬─────────────────────┘ │
        │                       │ rival_json             │
        │  ┌────────────────────▼─────────────────────┐ │
        │  │            SEO Graph (LangGraph)          │ │
        │  │  [seo_üret ‖ görsel_üret] → finalize      │ │
        │  └──────────────────────────────────────────┘ │
        │                                               │
        │  Gemini 2.5  ·  ChromaDB RAG  ·  GCS Yükleme │
        └───────────────────────────────────────────────┘
```

Her servis ayrı bir **Google Cloud Run** instance'ıdır; servisler arası iletişim **VPC Connector** üzerinden özel ağda gerçekleşir.

---

## Servisler

### API Gateway — Port 8000

Platformun tek genel giriş noktası. Dışarıdan gelen tüm HTTP istekleri buradan geçer.

**Sorumlulukları:**
- **JWT Middleware** — korumalı her rotada Bearer token'ı, Auth Service'in `/internal/validate` endpoint'i üzerinden doğrular
- **CORS Middleware** — frontend origin'ine izin verir, diğer çapraz kaynak isteklerini reddeder
- **SlowAPI Rate Limiting** — API kötüye kullanımını önlemek için Redis destekli token-bucket algoritması
- **`/analyze`** — kota kontrolü (Quota Service), görev kaydı oluşturma (Task Service), Redis kuyruğuna push, frontend'e `task_id` döndürme
- **`/analyze/{task_id}`** — Task Service'ten görev durumu ve sonuç sorgulama proxy'si
- **`/auth`** — Auth Service'e reverse proxy (login, kayıt)
- **`/upload`** — Google Cloud Storage presigned URL üretimi; multipart yüklemeler için `aiofiles` streaming desteği
- **`/health`** — tüm downstream servislerin sağlık kontrolü ve toplu durum raporu

**Teknik seçimler:**
- `httpx.AsyncClient` — tüm downstream çağrılar için bağlantı havuzu ve yapılandırılabilir timeout ile async HTTP
- `slowapi` — FastAPI native entegrasyon; Redis destekli; özel middleware yazmaktan kaçınıldı
- Token doğrulaması her istekte Auth Service'e ayrı çağrı yapar — gateway durumsuzdur, gizli anahtar paylaşımı gerektirmez

---

### Auth Service — Port 8001

Kullanıcı kimlik doğrulama ve JWT token yönetimi.

**Endpoint'ler:**
- `POST /register` — bcrypt ile hash'lenmiş şifreyle kullanıcı oluşturur (`REGISTRATION_ENABLED` ile kontrol edilir)
- `POST /login` — kimlik bilgilerini doğrular, access token (30 dk) + refresh token (7 gün) döner
- `POST /refresh` — refresh token ile yeni access token üretir
- `POST /internal/validate` — API Gateway tarafından çağrılır; token'ı doğrular, `user_id` claim'ini döner

**Teknik seçimler:**
- `SQLAlchemy 2.x async` + `asyncpg` — tamamen non-blocking veritabanı I/O
- `Alembic` — schema migration'ları; servis başlangıcında otomatik çalışır
- `PyJWT` ile HS256 — RS256 ve JWKS endpoint'i gerektiren alternatife göre hackathon scope'u için daha sade
- `bcrypt` work factor 12 — şifre hash'leme için
- Production'da `cloud-sql-python-connector` + IAM authentication — connection string'de düz metin şifre yok

---

### Task Service — Port 8002

Analiz görevlerinin yaşam döngüsü yönetimi ve sonuç depolama.

**Görev durum makinesi:**
```
pending ──▶ running ──▶ completed
                   └──▶ failed
                   └──▶ cancelled
```

**Temel tasarım kararları:**
- Görevler oluşturma anında UUID ile tanımlanır; API Gateway bu ID'yi anında frontend'e döner, polling başlar
- Görev `payload`'ı (tüm kullanıcı girişi) PostgreSQL'de JSONB olarak saklanır — ayrı input tablosu yok
- `seo_tone` görev üzerinde birinci sınıf alan: `casual | professional | premium`; downstream SEO üretimini doğrudan etkiler
- `TaskResult` ayrı tablo (Task ile bire-bir) — büyük JSON sonuçları durum sorgularından ayrılır, performans kazanımı
- Progress iki kanala eş zamanlı yazılır: `HSET task_progress:{task_id}` (geç katılan poller'lar için) ve `PUBLISH progress:{task_id}` (gelecekteki WebSocket desteği için)
- Görev zaten terminal durumundaysa `/tasks/{id}/status` PATCH 409 döner; Broker Worker bunu loglayarak devam eder

---

### Quota Service — Port 8003

Kullanıcı başına günlük analiz kotası.

**Çalışma mantığı:**
- Her `POST /analyze`'da API Gateway, kuyruğa dokunmadan önce Quota Service'e `POST /quota/check` çağrısı yapar
- Quota Service, Redis'te **Lua script** çalıştırır: `quota:{user_id}` atomik olarak arttırılır, yeni anahtarsa 86400 saniyelik TTL set edilir, `QUOTA_LIMIT` ile karşılaştırılır
- Limit aşılırsa 429 döner; API Gateway bunu frontend'e okunabilir bir mesajla iletir
- Lua zorunluluğu: non-atomik INCR + EXPIRE dizisi eş zamanlı isteklerde race condition yaratırdı

**Konfigürasyon:**
- `QUOTA_LIMIT` — varsayılan 10, demo için kolayca artırılabilir
- `QUOTA_TTL_SECONDS` — varsayılan 86400 (kullanıcı başına kayan 24 saatlik pencere)

---

### Broker Worker — Port 8004

Asenkron görev dağıtıcı. Redis kuyruğunu Agent Worker'a bağlar; retry mantığını yönetir.

**Consumer döngüsü:**
1. **Ayrılmış daemon thread** içinde `BLPOP task_queue` — bloklamanın FastAPI event loop'unu etkilememesi için
2. Mesaj alındığında: JSON deserialize, `AgentClient.run(task_id, payload)` → Agent Worker'a `POST /run`
3. Agent Worker 202 döner; broker Task Service'e `status = running` günceller
4. Agent Worker 5xx veya timeout verirse: **exponential backoff** ile ayrı retry thread'i başlatır — `delay = base_delay * 2^girişim` (varsayılan: 2s, 4s, 8s)
5. Retry durumu PostgreSQL'de saklanır — servis yeniden başlasa da sayaç korunur
6. `MAX_RETRY_COUNT` (3) tüketilince Task Service'e `status = failed`

**Neden ayrı thread:**  
`redis-py`'nin blocking komutları asyncio event loop içinde `run_in_executor` sarmalama olmadan kullanılamaz. Thread ile bu ek yük ve karmaşıklık önlenir.

---

### Agent Worker — Port 8005

AI yürütme motoru. LangGraph iş akışlarını çalıştırır, Google Gemini'yi çağırır.

> Detaylı açıklama: [Yapay Zeka Katmanı](#yapay-zeka-katmanı--agent-worker)

---

### Frontend — Port 3000

Next.js 14 ile yazılmış Türkçe yerelleştirilmiş arayüz.

**Sayfa haritası:**

| Rota | Açıklama |
|------|----------|
| `/` | Landing — animasyonlu özellik vitrini, CTA |
| `/login` | JWT giriş formu |
| `/register` | Kullanıcı kayıt formu |
| `/dashboard` | Son analizlere genel bakış |
| `/dashboard/analyze` | Yeni analiz oluşturma (ürün bilgisi, platform, ton) |
| `/dashboard/analyze/[taskId]/progress` | Gerçek zamanlı ilerleme takibi |
| `/dashboard/result/[taskId]` | Grafiklerle tam sonuç panosu |
| `/dashboard/history` | Sayfalanmış geçmiş analizler |

**Teknik seçimler:**
- **Next.js 14 App Router** — server component'ler ilk sayfa yüklemesi için, client component'ler etkileşimli kısımlar için; tam SPA yükü yok
- **Zustand** — auth token, kullanıcı bilgisi için minimal global state; boilerplate'siz API
- **shadcn/ui + Radix UI** — TailwindCSS ile özelleştirilen erişilebilir, başsız bileşen kütüphanesi
- **Framer Motion** — sayfa geçişleri ve landing/progress ekranında mikro animasyonlar
- **react-hook-form + zod** — şema odaklı form validasyonu; zod şemaları TypeScript tipleri olarak da kullanılır
- **Polling vs WebSocket** — frontend her 2 saniyede bir `GET /tasks/{id}` sorgular. WebSocket kasıtlı olarak atlandı: Cloud Run'ın istek bazlı faturalandırmasıyla kalıcı bağlantı katmanı altyapı karmaşıklığı ekler, bu ölçekte UX farkı ihmal edilebilir
- **axios interceptor** — 401 yanıtlarında access token'ı şeffaf biçimde yeniler, orijinal isteği yeniden dener

---

## Yapay Zeka Katmanı — Agent Worker

### LangGraph Durum Makineleri

Her iki iş akışı da LangGraph `StateGraph` instance'ları olarak implement edilmiştir. State, node'lar arasında veriyi biriktiren Python `TypedDict`'tir — paylaşılan mutable state yok, yan-kanal iletişimi yok.

Her node `NodeRunner` middleware'i tarafından sarılır:
1. Node çalışmadan önce Redis'te `cancelled:{task_id}` key'ini kontrol eder — varsa `{"cancelled": True}` döner, graph END'e yönlendirilir
2. Node fonksiyonu çağrılmadan önce `(adım_adı, "running", %pct)` Redis'e rapor edilir
3. Node fonksiyonu başarıyla dönünce `(adım_adı, "completed", %pct)` güncellenir

Progress event'leri eş zamanlı iki Redis yapısına yazılır:
- `HSET task_progress:{task_id}` — geç bağlanan poller'lar için kalıcı hash
- `PUBLISH progress:{task_id}` — gelecekteki gerçek zamanlı client'lar için pub/sub kanalı

---

#### Rival Graph

```
START
  │
  ▼  %10
discover_competitors
  │  Gemini 2.5 Flash Lite
  │  Giriş:  platform, kategori, ürün başlığı, marka
  │  Çıkış:  benzerlik skoru ile rakip isim listesi
  │
  ▼  %25
research_competitors
  │  Gemini 2.5 Flash Lite (rakip başına paralel)
  │  Giriş:  competitor_names listesi
  │  Çıkış:  {fiyat, puan, yorum_sayısı, özellikler} per rakip
  │  Filtre: birincil eşik → ikincil eşik → acil top-N
  │
  ├─────────────────────────────────────┐
  ▼  %40                               ▼  %40
analyze_sentiment                  analyze_trends
  │  Gemini 2.5 Flash               │  Gemini 2.5 Flash
  │  Rakip yorumlarından            │  Kategori talep trendleri
  │  olumlu/olumsuz temalar         │  Mevsimsellik, yükselen fırsatlar
  │
  ├──────────────┐         ┌────────────┘
  ▼  %72         ▼  %72
market_gap      pricing
  │  Gemini 2.5 Flash      │  Gemini 2.5 Flash
  │  Karşılanmayan müşteri │  Optimal fiyat bandı
  │  ihtiyaçları           │  Varyant çakışma skoru
  │
  └──────────┬──────────────┘
             ▼  %55
          finalize
             │  Eksiksiz rival_json oluşturulur
             │  State SEO Graph'a devredilir
             ▼
            END
```

**Paralel yürütme:** `analyze_sentiment` ve `analyze_trends` fan-out olarak paralel çalışır (LangGraph join'i yönetir). Benzer şekilde `market_gap` ve `pricing` paralel çalışır — bu iki aşamanın toplam süresini yaklaşık yarıya indirir.

**Araştırma alaka filtresi:** Her rakip araştırıldıktan sonra sonuçlar discovery adımındaki `similarity_score`'a göre sıralanır. Ajan önce birincil eşiği, ardından ikincil eşiği uygular; son çare olarak üst-N'i alır. Bu, düşük alaka düzeyli rakiplerin analizi sulandırmasını önler.

---

#### SEO Graph

```
START
  ├────────────────────────────────────┐
  ▼  %80                              ▼  %90
generate_seo                    generate_image
  │  Gemini 2.5 Flash             │  Gemini 2.5 Flash (görsel)
  │  Giriş: rival_json            │  Giriş: ürün başlığı + varyant
  │         seo_tone              │  Ad. 1: stüdyo görseli üret
  │         ChromaDB top-6 RAG    │  Ad. 2: arka plan kaldır (RemoveBG)
  │  Çıkış: başlık, açıklama,     │  Ad. 3: platform canvas'ına yerleştir
  │          bullet, tag, meta    │  Ad. 4: GCS'e yükle → signed URL
  │
  └──────────┬─────────────────────────┘
             ▼  %100
          finalize
             │  seo_output + generated_image_url birleştirilir
             │  Eksiksiz sonuç Task Service'e kaydedilir
             ▼
            END
```

---

### Agent Tool Detayları

#### Rival Agent Tool'ları

| Tool | Model | Amaç |
|------|-------|------|
| `competitor_discovery` | `gemini-2.5-flash-lite` | Hedef platformda gerçek rakipleri benzerlik skoruyla tespit eder |
| `competitor_research` | `gemini-2.5-flash-lite` | Rakip başına yapılandırılmış derin araştırma; eş zamanlı çalışır |
| `sentiment_analysis` | `gemini-2.5-flash` | Yorumlardan olumlu/olumsuz temaları sınıflandırır; öne çıkan pain point'leri ve övülen özellikleri ortaya çıkarır |
| `trend_analysis` | `gemini-2.5-flash` | Talep trendlerini, mevsimsel kalıpları ve yükselen fırsatları çıkarır |
| `market_gap_analyzer` | `gemini-2.5-flash` | Müşterilerin isteyip rakiplerin sunamadığı boşlukları belirler |
| `smart_pricing_engine` | `gemini-2.5-flash` | Optimal fiyat bandı, indirim stratejisi ve rakip çakışmasına göre varyant fiyatlandırması önerir |

**Model seçim gerekçesi:**  
Discovery ve Research yüksek hacimli, yapılandırılmış extraction görevleridir — `gemini-2.5-flash-lite` maliyet/hız açısından en iyi dengeyi sağlar. Analitik node'lar (Sentiment, Trends, Gap, Pricing) daha derin akıl yürütme gerektirir ve çıktıları sonraki node'lara beslenir; bu yüzden `gemini-2.5-flash` kullanılır.

Tüm Gemini çağrıları `response_mime_type: "application/json"` set eder ve prompt'ta JSON şema kısıtlamaları içerir.

#### SEO Agent Tool'ları

**SEO Optimizer:**
- `gemini-2.5-flash` + `ChromaDB` RAG
- E-ticaret SEO kurallarından oluşan küratörlü chunk koleksiyonu ChromaDB'de saklanır (`CHROMA_COLLECTION_NAME=seo_chunks`)
- Çalışma zamanında ürün kategorisi ve platforma göre en alakalı `CHROMA_TOP_K=6` chunk alınır, sistem prompt'una enjekte edilir
- Platforma özgü kısıtlamalar (başlık karakter limiti, bullet sayısı, tag politikası) `json_prompt_rules.py` aracılığıyla uygulanır
- Çıkış tonu görev payload'ındaki `seo_tone` parametresiyle kontrol edilir

**Görsel Üretim Pipeline'ı:**

```
Gemini görsel üretimi
    │  Prompt: "{ürün_başlığı}, beyaz arka plan, stüdyo aydınlatması,
    │           profesyonel e-ticaret fotoğrafı"
    │  Çıkış:  PIL Image (RGBA)
    ▼
RemoveBG API (background_removal.py)
    │  Ham görsel byte gönderilir, maske uygulanmış PNG alınır
    │  RemoveBG başarısız olursa Gemini görseline geri döner
    ▼
Platform Canvas Kompozisyonu (utils_image.py)
    │  Trendyol:    1200 × 1800 px, ürün canvas yüksekliğinin %78'i
    │  Amazon:      1600 × 1600 px, ürün canvas yüksekliğinin %76'sı
    │  Hepsiburada: 1200 × 1200 px, ürün canvas yüksekliğinin %76'sı
    │  - Şeffaf dolgu kırpılır (%4 kenar boşluğu korunur)
    │  - Ürün beyaz canvas'a ortalanır
    ▼
Google Cloud Storage Yükleme
    │  Dosya adı: çakışmayı önlemek için UUID
    │  Signed URL görev sonuç JSON'una eklenir
    ▼
Görev Sonucu
```

**Varyant seçimi:** `select_variant()` planlar doğrultusunda henüz kullanılmamaktadır; pipeline her zaman `valid[0]` ile devam eder. Gemini görsel üretimi zaman zaman başarısız olduğundan, bu durumda canvas çıktısı doğrudan kullanıcıya iletilir.
---

### İptal Mekanizması

Kullanıcı çalışan bir analizi iptal ettiğinde:
1. API Gateway, Redis'e `SET cancelled:{task_id} 1 EX 3600` yazar
2. Her node çalışmadan önce `NodeRunner`, `EXISTS cancelled:{task_id}` kontrol eder
3. Key mevcutsa node fonksiyonu atlanır, `{"cancelled": True, "status": "cancelled"}` döner
4. `_cancel_or()` conditional edge `cancelled=True` görür ve END'e yönlendirir
5. `WorkflowErrorHandler`, Task Service'e `status=cancelled` çağrısı yapar
6. Frontend bir sonraki polling'de `status=cancelled` alır, dashboard'a yönlendirir

---

### Servisler Arası Kimlik Doğrulama — `services/shared/`

Tüm servis-içi HTTP çağrıları paylaşılan `InternalHttpClient` kullanır:

- `iss="internal-service"` claim'li JWT üretir — kullanıcı token'larından doğrulama anında ayırt edilir
- **Token cache**: 5 dakika TTL, 30 saniyelik yenileme buffer'ı — yüksek frekanslı servis çağrılarında JWT üretim yükü minimize edilir
- `asyncio.Lock` — async context'te eş zamanlı yenileme yarışlarını önler
- Broker Worker (threading tabanlı) için sync varyant ayrıca mevcuttur

---

## Uçtan Uca Veri Akışı

### Yeni Analiz İsteği (Uçtan Uca)

```
1. Kullanıcı formu gönderir
       │
       ▼
2. API Gateway
   ├─ JWT doğrular (Auth Service /internal/validate)
   ├─ Kota kontrol eder (Quota Service → Redis Lua atomik increment)
   ├─ Görev kaydı oluşturur (Task Service → Cloud SQL)
   ├─ {task_id, payload} Redis task_queue'ya RPUSH eder
   └─ {task_id} frontend'e döner

3. Frontend her 2 saniyede GET /tasks/{task_id} polling başlatır

4. Broker Worker (arka planda)
   ├─ BLPOP task_queue → mesajı alır
   ├─ PATCH /tasks/{id}/status → "running" (Task Service)
   └─ Agent Worker'a POST /run

5. Agent Worker (asenkron)
   ├─ Rival Graph çalışır (LangGraph)
   │   Her node: iptal kontrolü → progress raporu → Gemini çağrısı → progress güncelleme
   │   Paralel: [duygu ‖ trend] ardından [pazar_boşluğu ‖ fiyat]
   ├─ rival_json SEO Graph'a aktarılır
   └─ SEO Graph: [seo_üret ‖ görsel_üret] paralel
       ├─ seo_üret: ChromaDB RAG + Gemini → yapılandırılmış listeleme içeriği
       └─ görsel_üret: Gemini → RemoveBG → Canvas → GCS yükleme

6. Agent Worker finalize
   ├─ POST /tasks/{id}/result (Task Service → Cloud SQL)
   └─ PATCH /tasks/{id}/status → "completed"

7. Frontend bir sonraki polling'de status=completed alır
   └─ /dashboard/result/{taskId}'ye yönlendirir
```

---

## Altyapı ve Google Cloud

### Kullanılan Google Cloud Servisleri

| Servis | Amaç |
|--------|------|
| **Cloud Run** | Tüm 7 servis için sunucusuz container barındırma; boştayken sıfıra ölçeklenir |
| **Cloud SQL (PostgreSQL 15)** | Yönetilen ilişkisel veritabanı; Auth, Task ve Broker servisleri tarafından kullanılır |
| **Memorystore (Redis 7)** | Tam yönetilen Redis; görev kuyruğu, kota sayaçları, progress event'leri, iptal sinyalleri |
| **Google Cloud Storage (GCS)** | Üretilen ürün görseli depolama; görev sonuçlarına signed URL eklenir |
| **Artifact Registry (GAR)** | Özel Docker image registry; tüm servis image'ları commit SHA ve `latest` ile etiketlenir |
| **VPC Connector** | Cloud Run servisleri ile Memorystore/Cloud SQL arasında özel ağ köprüsü |
| **Workload Identity Federation** | Anahtarsız GitHub Actions → GCP kimlik doğrulaması (service account JSON dosyası yok) |
| **Vertex AI / Gemini API** | Gemini 2.5 Flash ve Flash-Lite model inferansı |

### Google Cloud SQL

- PostgreSQL 15 yönetilen instance
- Auth ve Task servisleri `cloud-sql-python-connector` + IAM authentication ile bağlanır — connection string'de düz metin şifre yoktur
- Broker Worker `psycopg2` (senkron) ile aynı Cloud SQL connector'ı kullanır
- Alembic migration'ları, servis başlangıcında deploy zamanında enjekte edilen `DATABASE_URL` environment variable'ı ile otomatik çalışır

### Google Cloud Memorystore (Redis)

- VPC içinde tam yönetilen Redis 7 instance
- Production'da self-hosted Redis tamamen yerine geçer — Cloud Run'da Redis container'ı çalışmaz
- Kullanım alanları: görev kuyruğu (RPUSH/BLPOP), kota sayaçları (Lua atomik), progress raporlama (HSET + PUBLISH), iptal sinyalleri (TTL'li SET)
- Cloud Run'dan yalnızca VPC Connector üzerinden erişilebilir — internetten ulaşılamaz

### Google Cloud Storage

- Bucket `GCS_BUCKET` environment variable ile yapılandırılır
- Agent Worker, Cloud Run service account'ının IAM rolü üzerinden kimlik doğrular — kodda API key yoktur
- Üretilen görseller `google-cloud-storage` SDK ile UUID tabanlı nesne adıyla yüklenir
- Zaman sınırlı signed URL'ler frontend'e doğrudan görsel yüklemek için döndürülür

### Google Artifact Registry

- Repository, 7 servisin tüm Docker image'larını barındırır
- Image'lar hem `github.sha` (değiştirilemez, Cloud Run deploy'larında kullanılır) hem de `latest` (okunabilir referans) ile etiketlenir
- GAR, Cloud Run ile aynı bölgede — image pull gecikmesi minimize edilir
- IAM erişim kontrolü: GitHub deploy service account `roles/artifactregistry.writer`; Cloud Run runtime SA `roles/artifactregistry.reader`

### Google IAM — Service Account Mimarisi

Her Cloud Run servisi **özel bir service account** altında çalışır, yalnızca ihtiyaç duyduğu izinlere sahiptir:

| Servis | Service Account | Temel İzinler |
|--------|----------------|---------------|
| API Gateway | `api-gateway-sa` | downstream servislerde `run.invoker` |
| Auth Service | `auth-service-sa` | `cloudsql.client` |
| Task Service | `task-service-sa` | `cloudsql.client` |
| Broker Worker | `broker-worker-sa` | `cloudsql.client`, Agent Worker'da `run.invoker` |
| Agent Worker | `agent-worker-sa` | GCS bucket'ta `storage.objectAdmin`, `aiplatform.user` (Gemini) |
| Quota Service | `quota-service-sa` | VPC üzerinden Memorystore erişimi |
| Frontend | `frontend-sa` | API Gateway'de `run.invoker` |

Bu en az ayrıcalık prensibi, bir servisin ele geçirilmesinin diğer GCP kaynaklarının kontrolüne yükseltilememesini sağlar.

---

## CI/CD Pipeline

Platform, GitHub Actions üzerinde **tam otomatik, uçtan uca CI/CD pipeline'ına** sahiptir. `main` branch'e her push, servis bazlı deploy workflow'larını tetikler. Manuel deployment adımı yoktur.

### Workflow Tetikleyicileri

Her servisin kendi workflow dosyası şu durumlarda tetiklenir:
- `main` branch'e push ile **servise ait dizinde değişiklik** (path filtering)
- İsteğe bağlı yeniden deployment için manuel `workflow_dispatch`

Bu sayede `services/agent-worker/` altına bir değişiklik push edildiğinde yalnızca agent worker yeniden deploy edilir — diğer servisler dokunulmaz.

### Deployment Adımları (servis başına)

```
1. actions/checkout@v4
       │
       ▼
2. google-github-actions/auth@v2
   └─ Workload Identity Federation (OIDC token — JSON key dosyası yok)
       │
       ▼
3. gcloud auth configure-docker {GAR_LOCATION}-docker.pkg.dev
       │
       ▼
4. docker build (çok aşamalı)
   └─ Etiketler: IMAGE:${{ github.sha }}  +  IMAGE:latest
       │
       ▼
5. Her iki etiketi Artifact Registry'e docker push
       │
       ▼
6. gcloud run deploy
   ├─ --image IMAGE:${{ github.sha }}  (değiştirilemez sabitlenmiş etiket)
   ├─ --region, --project, --service-account
   ├─ --vpc-connector (özel Memorystore/SQL erişimi)
   ├─ --set-env-vars (tüm secret'lar GitHub Secrets'tan enjekte edilir)
   └─ Traffic anında yeni revision'a yönlendirilir
       │
       ▼
7. Deployment Özeti GitHub Actions iş özetine yazılır
   └─ Canlı Cloud Run servis URL'si dahil
```

### Workload Identity Federation — Sıfır Secret Dosyası

GitHub Actions, GCP'ye JSON service account key dosyası olmadan kimlik doğrular:
- GCP'de bir **Workload Identity Pool**, GitHub OIDC provider ile yapılandırılmıştır
- Pool, deploy service account'ına `repository` claim'i koşuluyla bağlanmıştır
- `google-github-actions/auth@v2`, GitHub OIDC token'ını çalışma zamanında kısa ömürlü GCP access token'ı ile değiştirir
- Kalıcı credential hiçbir yerde saklanmaz — rotasyon otomatiktir

### Bootstrap Deploy

`deploy-all.yml`, tüm 7 servisi sırayla build edip deploy eden manuel tetikleyicili workflow'dur. İlk kurulum veya tam platform sıfırlama için kullanılır.

---

## Güvenlik

### Secret Yönetimi — GitHub Secrets

**Kod tabanında hiçbir yerde hassas değer bulunmaz.** Tüm secret'lar **GitHub Actions Secrets**'ta saklanır ve deploy zamanında `gcloud run deploy` içindeki `--set-env-vars` aracılığıyla environment variable olarak enjekte edilir.

GitHub'da saklanan secret'lar:
- `JWT_SECRET_KEY` — kullanıcı token'ları için HMAC imzalama anahtarı
- `REMOVEBG_API_KEY` — RemoveBG arka plan kaldırma API anahtarı
- `GCP_PROJECT_ID`, `GCP_REGION`, `GAR_LOCATION`, `GAR_REPO` — GCP hedefleme
- `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT` — CI kimlik doğrulama
- `REDIS_URL`, `DATABASE_URL` — altyapı bağlantı stringleri
- Tüm Gemini model adları, ChromaDB konfigürasyonu, GCS bucket adı
- Cloud SQL bağlantı parametreleri

Çalışma zamanındaki secret'lar dosya sistemine dokunmaz — yalnızca çalışan container'a erişilebilen Cloud Run environment variable'ları olarak yaşar.

### Ek Güvenlik Önlemleri

- **Root olmayan Docker container'ları** — tüm Python servis Dockerfile'ları root olmayan `appuser` oluşturur ve geçer
- **Özel ağ** — Memorystore ve Cloud SQL herkese açık değil; yalnızca VPC Connector üzerinden Cloud Run'dan erişilebilir
- **Servis izolasyonu** — her Cloud Run servisi minimum IAM rolüne sahip kendi SA'sında çalışır; hiçbir servis diğerinin kimliğine bürünemez
- **Internal JWT claim'leri** — servisler arası çağrılar `iss="internal-service"` token'ı kullanır; kullanıcı token'ları servisler arasında iletilmez
- **SlowAPI rate limiting** — API Gateway brute-force ve scraping girişimlerini engeller
- **Atomik kota işlemleri** — Quota Service'teki Lua script'leri eş zamanlı kota kontrollerindeki race condition'ları önler

---

## Teknoloji Yığını

### Backend

| Kategori | Teknoloji | Notlar |
|----------|-----------|--------|
| Dil | Python 3.12 | Tüm backend servisler |
| Web framework | FastAPI | API Gateway, Auth, Task, Quota, Broker |
| ASGI sunucusu | Uvicorn | Production grade, async |
| Agent HTTP sunucusu | aiohttp | Agent Worker (uzun süren görevler için FastAPI yükü yok) |
| AI orchestrasyonu | LangGraph | StateGraph tabanlı iş akışı yönetimi |
| AI modelleri | Google Gemini 2.5 Flash / Flash-Lite / Image | Vertex AI üzerinden |
| Gemini SDK | `google-genai` | Doğrudan SDK, LangChain wrapper'ı değil |
| Vektör veritabanı | ChromaDB | Docker build'de pre-warm edilen yerel kalıcı store |
| ORM | SQLAlchemy 2.x (async) | Tam async, tip güvenli sorgular |
| DB driver | asyncpg | PostgreSQL async adapter |
| Senkron DB driver | psycopg2 | Broker Worker (threading tabanlı) |
| DB migration | Alembic | Servis başlangıcında otomatik çalışır |
| Cache / Queue | Redis 7 (Memorystore) | Görev kuyruğu, kotalar, progress, iptal |
| Object storage | Google Cloud Storage | Signed-URL görsel dağıtımı |
| Görsel işleme | Pillow | Canvas kompozisyonu, alpha kanal işleme |
| HTTP client | httpx (async) | Tüm servisler arası çağrılar |
| Auth | PyJWT + bcrypt | HS256 token, bcrypt work factor 12 |
| Rate limiting | SlowAPI | FastAPI native Redis destekli limiter |
| Validasyon | Pydantic v2 | Request/response şemaları, ayarlar |
| Loglama | python-json-logger | Cloud Logging için yapılandırılmış JSON loglar |
| Cloud DB auth | cloud-sql-python-connector | IAM tabanlı Cloud SQL erişimi |

### Frontend

| Kategori | Teknoloji | Notlar |
|----------|-----------|--------|
| Framework | Next.js 14 | App Router, SSR + client component'ler |
| Dil | TypeScript 5 | Strict mode |
| UI katmanı | React 18 | |
| Stil | TailwindCSS 3 | Utility-first |
| Bileşenler | shadcn/ui + Radix UI | Erişilebilir başsız primitifler |
| Animasyonlar | Framer Motion | Sayfa geçişleri, mikro animasyonlar |
| State | Zustand | Auth state, hafif |
| Formlar | react-hook-form + zod | Şema odaklı validasyon |
| HTTP | axios | Interceptor tabanlı token yenileme |
| Grafikler | recharts | Sonuç panosu görselleştirmeleri |
| İkonlar | lucide-react | |
| Tarih | date-fns | |

### Altyapı

| Kategori | Teknoloji |
|----------|-----------|
| Containerization | Docker (çok aşamalı build) |
| Yerel orchestrasyon | Docker Compose |
| Production barındırma | Google Cloud Run (sunucusuz) |
| Veritabanı | Google Cloud SQL — PostgreSQL 15 |
| Cache / Queue | Google Cloud Memorystore — Redis 7 |
| Image registry | Google Artifact Registry |
| Object storage | Google Cloud Storage |
| CI/CD | GitHub Actions |
| Auth (CI→GCP) | Workload Identity Federation (OIDC) |
| Özel ağ | VPC Connector |

---

## Ortam Değişkenleri

Tüm değişkenler `.env.example`'da tanımlıdır. Production'daki gerçek değerler GitHub Secrets'tan deploy zamanında gelir.

### Altyapı

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=...
POSTGRES_DB=platform
DATABASE_URL=postgresql+asyncpg://...
BROKER_DATABASE_URL=postgresql+psycopg2://...
REDIS_URL=redis://...
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
QUOTA_LIMIT=10
QUOTA_TTL_SECONDS=86400
```

### Broker / Retry

```env
TASK_QUEUE_NAME=task_queue
MAX_RETRY_COUNT=3
RETRY_BASE_DELAY=2.0
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

### Google Cloud (Production Deploy)

```env
GCP_PROJECT_ID=...
GCP_REGION=us-central1
GAR_LOCATION=us-central1
GAR_REPO=...
CLOUD_SQL_INSTANCE=<proje>:<bölge>:<instance>
VPC_CONNECTOR=...
GCP_WORKLOAD_IDENTITY_PROVIDER=projects/.../workloadIdentityPools/.../providers/...
GCP_SERVICE_ACCOUNT=github-deploy-sa@...iam.gserviceaccount.com
```

---

## Yerel Geliştirme Notu

> **Kod tabanı şu anda Google Cloud deployment için yapılandırılmıştır ve ek kurulum olmadan yerel olarak tam çalıştırılamaz.**

Buluta bağlı bileşenler:

- **Google Gemini / Vertex AI** — Agent Worker, Gemini'yi `GOOGLE_CLOUD_PROJECT` ve Application Default Credentials üzerinden çağırır. Yerel çalıştırma için `gcloud auth application-default login` ve yapılandırılmış projede geçerli Vertex AI kotası gerekir.
- **Google Cloud Storage** — Görsel üretimi GCS'e service account'ın IAM rolü kullanarak yükler. Yerel çalıştırma için service account key dosyası (`GOOGLE_APPLICATION_CREDENTIALS`) ve yapılandırılmış bucket'a yazma erişimi gerekir.
- **RemoveBG API** — Geçerli `REMOVEBG_API_KEY` gerektirir; yerel alternatif yoktur.
- **Cloud SQL** — Production'da `cloud-sql-python-connector` kullanılır. Yerel Docker Compose için `DATABASE_URL`, Cloud SQL instance'ı değil yerel PostgreSQL container'ına işaret etmelidir.
- **Memorystore** — VPC'ye özel Redis instance, GCP dışından ulaşılamaz. Yerel geliştirme için Docker Compose'daki Redis container'ını kullanın ve `REDIS_URL=redis://redis:6379/0` ayarlayın.

Platform, Google Cloud ortamında uçtan uca tam işlevseldir.

---

## Ekip ve Geliştirme Süreci

Ekip hackathon boyunca **dengeli görev dağılımı** anlayışıyla çalıştı; her üye yatay katmanlar yerine eksiksiz dikey dilimler sahiplendi (bir servis + frontend entegrasyonu). Bu yaklaşım darboğazları önledi ve stack genelinde paralel ilerleme sağladı.

Geliştirme **iki ortamlı bir model** izledi:
- **`main` branch** — production ortamı; Google Cloud Run'da canlı olanı her zaman yansıtır. Buraya yapılan her push otomatik CI/CD deployment tetikler.
- **`dev` branch** — ekibin günlük çalışma ortamı; aynı Cloud SQL ve Memorystore altyapısına bağlı paylaşılan entegrasyon ortamı. Geliştiriciler günlük çalışmalarını buraya push eder; `main`'e alınmadan önce gerçek AI iş akışı çalışmalarını, veritabanı yazma işlemlerini ve canlı kota uygulama adımlarını test etmek için staging katmanı işlevi görür.

Bu kurulum ekibin demo ortamı olan `main`'i riske atmadan `dev` üzerinde gerçek AI workflow çalışmalarını, gerçek veritabanı yazma işlemlerini ve canlı kota uygulamasını test edebilmesini sağladı.

---

*BTK Hackathon 2026 — BTK Akademi, Türkiye Girişimcilik Vakfı ve Google Türkiye tarafından organize edilmiştir*
