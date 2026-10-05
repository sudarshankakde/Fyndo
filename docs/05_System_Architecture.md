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

---

## 3. Storage & Caching Architecture

| Resource | Service | Purpose | Eviction / Retention |
|---|---|---|---|
| **Primary Data** | PostgreSQL 16 | Relational tables, spatial data, ledger | Persistent |
| **Cache & Sessions** | Redis 7 | JWT blacklist, OTP secrets, Rate limits | TTL 2m to 24h |
| **Videos & Thumbnails**| Cloudinary | Merchant vertical reels, auto-extracted poster WebP images | Persistent (Cloudinary CDN) |
| **Merchant KYC Docs** | Cloudinary | Encrypted/authenticated upload of GSTIN/Gumasta PDFs | Persistent (Restricted access) |
| **Static App Assets** | Global CDN | Web app bundle, icons, fonts | Edge caching (Cache-Control) |

---

## 4. Security & Network Topology
- **Zero Raw API Exposure**: All traffic routed via Nginx reverse proxy with TLS 1.3.
- **CORS Protection**: Scoped strictly to verified frontend web domains.
- **Rate Limiting**:
  - Public OTP endpoints: 3 requests per 10 minutes per IP.
  - Feed queries: 60 requests per minute per authenticated user.
  - POS Scanner redemption: 30 requests per minute per merchant staff terminal.
- **Data Protection**: Strict row-level access control ensuring cashiers can only query their own merchant's coupons.
