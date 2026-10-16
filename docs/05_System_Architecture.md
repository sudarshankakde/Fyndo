# 05 - System Architecture Document

> **System**: Fyndo (Hyper-Local Video Discovery & In-Store Digital Coupon Platform)  
> **Deployment Target**: Dockerized Multi-Container Setup (VPS / Cloud + PostgreSQL + Redis + Cloudinary)

---

## 1. High-Level Architecture Diagram

```mermaid
graph TD
    subgraph Clients
        ShopperApp[Shopper PWA / Web Client]
        MerchantApp[Merchant Studio PWA / Web]
        POSScanner[Cashier Scanner Terminal]
        AdminConsole[Super Admin Web Portal]
    end

    subgraph Media_and_CDN
        Cloudinary[Cloudinary Media Engine & Global CDN]
    end

    subgraph API_Gateway_and_Load_Balancer
        Nginx[Nginx Reverse Proxy & SSL]
        RateLimiter[Redis Rate Limiter]
    end

    subgraph Backend_Services
        API[Fyndo Core API Service - Python/FastAPI]
    end

    subgraph Data_Tier
        Postgres[(PostgreSQL 16 + PostGIS)]
        RedisCache[(Redis 7 - Sessions, OTP & Limits)]
    end

    ShopperApp -->|HTTPS / REST| Nginx
    MerchantApp -->|HTTPS / REST| Nginx
    POSScanner -->|HTTPS / Scan Auth| Nginx
    AdminConsole -->|HTTPS / Admin Auth| Nginx

    Nginx --> RateLimiter
    RateLimiter --> API

    API -->|Read / Write (SQLAlchemy Async)| Postgres
    API -->|Cache / Sessions / TOTP| RedisCache
    API -->|Generate Upload Signatures| Cloudinary

    MerchantApp -->|Direct Signed Upload| Cloudinary
    ShopperApp -->|Optimized MP4 & Poster Stream| Cloudinary
```

---

## 2. Core Service Components

### 2.1 Backend API Service (`backend/`)
- **Runtime**: Python 3.11+ / 3.12 (Asynchronous).
- **Framework**: FastAPI (Uvicorn ASGI) with Pydantic v2 schemas and modular APIRouters.
- **ORM & Database**: SQLAlchemy 2.0 (Async) + GeoAlchemy2 + asyncpg with Alembic migrations.
- **Responsibilities**:
  - Authentication (OTP generation, verification, JWT signing with PyJWT/Passlib).
  - PostGIS Spatial Discovery Queries (Nearby reels within 2, 5, 10 km via GeoAlchemy2/ST_DWithin).
  - Coupon Engine & Life Cycle Management.
  - TOTP Verification & Cashier Redemption Validation (PyOTP / standard RFC 6238).
  - Admin Moderation & Audit Logging.

### 2.2 Media Delivery & Optimization Strategy (Cloudinary)
- **Direct Signed Client Upload**:
  - The frontend requests an upload signature from FastAPI (`POST /api/v1/media/sign-upload`).
  - The client uploads directly to **Cloudinary** using the signature and timestamp.
  - S3 IAM configuration, bucket policies, and local disk buffering are completely bypassed.
- **On-the-Fly Dynamic Optimization**:
  - Cloudinary automatically optimizes delivery format and quality (`f_auto,q_auto`).
  - Enforces vertical 9:16 aspect ratio (`c_fill,ar_9:16`).
  - Automatically generates WebP poster thumbnails from the first frame (`so_0` or `so_auto`) with zero backend processing overhead.
- **Global CDN Delivery**:
  - High-speed content delivery via Cloudinary's multi-CDN fabric.
- **Hardened Server-Side Fallback** (`POST /media/upload`):
  - Streams uploads to disk with a hard byte cap, verifies the real content type from magic bytes
    (defeating extension spoofing), and derives an optional ffmpeg poster frame.
  - All blocking work (disk I/O, SHA-256 hashing, ffmpeg) runs in a worker thread via
    `run_in_threadpool`, so large uploads never block the event loop.

### 2.3 Anti-Fraud & Dynamic TOTP Engine
- **Algorithm**: RFC 6238 Time-Based One-Time Password (TOTP) customized for 60-second time steps.
- **Payload Payload**: Base64URL-encoded JSON containing `{ claim_id, totp_token, shopper_id }`.
- **Validation**:
  - The verification API checks against the shopper coupon secret using a `±1` window (allowing maximum 120s tolerance for clock drift).
  - Instant write-lock in Redis prevents double-spend race conditions across simultaneous cashier scanners.

### 2.4 Geospatial Query Engine (PostGIS)
- **Geometry Type**: `geography(Point, 4326)` for shop coordinates and user locations.
- **Spatial Index**: `GIST` index on `merchants.location`.
- **Query Strategy**:
  ```sql
  SELECT r.id, r.title, r.video_url, m.business_name,
         ST_Distance(m.location, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) AS distance_meters
  FROM reels r
  JOIN merchants m ON r.merchant_id = m.id
  WHERE r.status = 'APPROVED'
    AND ST_DWithin(m.location, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_meters)
  ORDER BY distance_meters ASC
  LIMIT :limit OFFSET :offset;
  ```

### 2.5 Client Architecture (Web & Mobile Apps)
- **UI & Component System**: **Tailwind CSS (v3.4)** utility engine paired with **shadcn/ui** (headless Radix UI primitives). Dark-mode first with high-contrast accessibility.
- **Server State Layer**: **TanStack Query v5** manages asynchronous data lifecycle:
  - Automatic cache invalidation on coupon claims and redemptions.
  - Infinite query scrolling for vertical 9:16 video feed.
  - Background polling / refetching for live moderation queues.
- **Client State Layer**: **Redux Toolkit (`@reduxjs/toolkit`)**:
  - `authSlice`: JWT access token, user session, role permissions.
  - `uiSlice`: Language selection (`EN`/`HI`/`MR`), active radius filter (2km/5km/10km), bottom sheets.
  - `scannerSlice`: Cashier POS scanner status, camera torch, daily redemption counters.

### 2.6 Observability & Audit Logging
- **Structured Logging**: stdlib `logging` with `contextvars`-based request correlation. Every request
  is stamped with a `request_id` (validated or generated, echoed back as `X-Request-ID`), the
  authenticated `user_id` and the resolved client IP.
- **Two formatters**: single-line **JSON** in production (`LOG_FORMAT=json`) and a compact **human**
  line in development, both driven by `configure_logging()` in `app/core/logging_config.py`.
- **Request Middleware**: a raw ASGI `RequestLoggingMiddleware` (not `BaseHTTPMiddleware`) emits exactly
  one access record per request — `INFO` below 500, `ERROR` at or above — with method, path, status and
  `duration_ms`. Raw ASGI is used deliberately so streaming media responses are never buffered.
- **Audit Trail**: `app/core/audit.py` exposes `audit_log(action, actor, target, outcome, **details)`,
  routed to the dedicated `fyndo.audit` logger. Every state change records actor, role, target, outcome
  and a structured detail bag. Audit records land in their own `audit.log` stream so they can be shipped
  or retained independently of application noise.
- **Sinks**: console plus rotating files (`fyndo.log`, `audit.log`) sized by `LOG_MAX_BYTES` with
  `LOG_BACKUP_COUNT` generations. Third-party loggers (`uvicorn.access`, `sqlalchemy.engine`, `httpx`,
  `httpcore`, `multipart`) are pinned to `WARNING` to keep signal high.

### 2.7 Notification & Push Service
- **In-App Inbox**: `notifications` table (see Database Design §2.12) is the durable source of truth.
  Alerts are created as a side effect of domain events — coupon claimed/redeemed, merchant KYC decided,
  reel moderated, admin broadcasts — never synchronously coupled to the user-facing response.
- **Best-Effort Dispatch**: `NotificationService.notify_safe()` swallows dispatch failures and logs a
  warning, so a broken alert can never roll back the mutation that triggered it.
- **Push Fan-Out**: `PushService` batches up to 100 messages per call to the Expo Push Service
  (`https://exp.host/--/api/v2/push/send`), which fronts FCM and APNs. Active tokens come from
  `device_tokens` (see Database Design §2.13); dispatch runs as a detached `asyncio` task.
- **Client Registration**: the mobile app requests notification permission after sign-in, registers its
  Expo push token, and unregisters it on sign-out. The unread badge is hydrated from
  `GET /notifications/unread-count`.

### 2.8 Super-Admin Panel (`backend/app/admin/`)
- **Purpose**: a server-rendered **HTML back office** so operators can see and edit every table
  (full CRUD including delete) without SQL access. See `docs/17_Admin_Panel.md`.
- **Stack**: FastAPI + **Jinja2** templates + **htmx 2.0.4** (vendored locally at
  `app/admin/static/htmx.min.js` — no CDN, works offline) with a hand-written `admin.css`.
- **Mounting**: a separate `APIRouter(prefix="/admin", include_in_schema=False)`, so it stays
  outside the JSON API contract and the OpenAPI schema. Anonymous visitors are bounced to
  `/admin/login` via a dedicated `RedirectToLogin` handler rather than the global JSON `401`.
- **Auth**: its **own** signed session cookie (`fyndo_admin_session`, httpOnly, samesite=lax,
  path `/admin`, 8-hour TTL) — deliberately **not** reusing `get_current_user`, so a leaked
  shopper/merchant bearer token can never be replayed against the back office.
- **Engine**: a generic CRUD engine (`registry.py`) that introspects SQLAlchemy mappers, so all
  12 tables are served by one code path plus a small per-table config list (`configs.py`).
- **Audit**: every create/update/delete emits `admin.create` / `admin.update` / `admin.delete`
  through `audit_log(..., source="admin_panel")` into the `audit.log` stream.

---

## 3. Storage & Caching Architecture

| Resource | Service | Purpose | Eviction / Retention |
|---|---|---|---|
| **Primary Data** | PostgreSQL 16 | Relational tables, spatial data, ledger | Persistent |
| **Cache & Sessions** | Redis 7 | JWT blacklist, OTP secrets, Rate limits | TTL 2m to 24h |
| **Feed Page Cache** | Redis 7 | Serialized proximity feed pages keyed by coords / sector / cursor / viewer | TTL 30s |
| **Videos & Thumbnails**| Cloudinary | Merchant vertical reels, auto-extracted poster WebP images | Persistent (Cloudinary CDN) |
| **Merchant KYC Docs** | Cloudinary | Encrypted/authenticated upload of GSTIN/Gumasta PDFs | Persistent (Restricted access) |
| **Static App Assets** | Global CDN | Web app bundle, icons, fonts | Edge caching (Cache-Control) |
| **Alerts & Push Tokens** | PostgreSQL 16 | `notifications` inbox + `device_tokens` registry | Purged after `NOTIFICATION_RETENTION_DAYS` |
| **Request & Audit Logs** | Rotating local files | `fyndo.log` (app) and `audit.log` (state changes) | Rotated at `LOG_MAX_BYTES` × `LOG_BACKUP_COUNT` |

---

## 4. Security & Network Topology
- **Zero Raw API Exposure**: All traffic routed via Nginx reverse proxy with TLS 1.3.
- **CORS Protection**: Scoped strictly to verified frontend web domains.
- **Rate Limiting**:
  - Public OTP endpoints: 3 requests per 10 minutes per IP.
  - Feed queries: 60 requests per minute per authenticated user.
  - POS Scanner redemption: 30 requests per minute per merchant staff terminal.
- **Double-Spend Prevention**: Redemption is committed through an atomic single-winner SQL guard
  (`UPDATE ... WHERE status = 'CLAIMED'`); when the row count is not exactly 1 the request is
  rejected with `409`. This reinforces the Redis write-lock so two concurrent cashier scans cannot
  both redeem the same voucher.
- **HTTP Hardening**: Raw-ASGI middleware adds `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy`, `Permissions-Policy` and `Cross-Origin-Opener-Policy` (plus HSTS in production),
  and rejects request bodies beyond `MAX_REQUEST_BYTES` with `413` before routing. CORS is registered
  last so it stays outermost and decorates every response — including the `413`.
- **Data Protection**: Strict row-level access control ensuring cashiers can only query their own merchant's coupons.
