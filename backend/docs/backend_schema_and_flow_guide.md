# Fyndo Backend Architecture: Database Schema & Service Flows

> **Platform**: Fyndo (Hyper-Local Video Discovery & In-Store Digital Coupon Platform)  
> **Backend Engine**: FastAPI (Python 3.13) + Async SQLAlchemy 2.0 + PostgreSQL 16 (PostGIS) / SQLite fallback + Redis 7  
> **Media Infrastructure**: Cloudinary (Direct Signed Client Upload + Multi-CDN Delivery)  
> **Security Core**: RFC 6238 60s Dynamic TOTP + Bcrypt Hashed Staff PINs + Dual JWT (Access/Refresh)

---

## 1. Database Schema Specification

### 1.1 Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    users ||--o| merchants : "owns (1:1)"
    merchants ||--o{ merchant_staff : "employs"
    merchants ||--o{ reels : "publishes (1:N)"
    reels ||--|| coupon_templates : "attaches (1:1)"
    coupon_templates ||--o{ user_coupons : "generates claims (1:N)"
    users ||--o{ user_coupons : "holds in wallet (1:N)"
    user_coupons ||--o| redemptions_ledger : "settled by (1:1)"
    merchants ||--o{ redemptions_ledger : "redeems at (1:N)"
    merchant_staff ||--o{ redemptions_ledger : "verified by (1:N)"
    reels ||--o{ reel_views : "records (1:N)"
    merchant_staff ||--o{ reels : "uploads (cashier, optional)"
    merchants ||--o{ merchant_followers : "followed by"
    users ||--o{ merchant_followers : "follows"
    merchants ||--o{ merchant_ratings : "rated by"
    users ||--o{ merchant_ratings : "rates (1 per store)"
    merchants ||--o{ merchant_call_clicks : "receives call taps"
    users ||--o{ merchant_call_clicks : "taps call (optional)"
    users ||--o{ system_settings : "last updated by"
```

---

### 1.2 Table Definitions & Data Dictionaries

#### 1. `users`
Represents all system actors (Shoppers, Merchant Owners, Super Admins).
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(15) UNIQUE NOT NULL,            -- Formatted as +91XXXXXXXXXX
    full_name VARCHAR(100) NULL,
    email VARCHAR(255) NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'SHOPPER',  -- SHOPPER, MERCHANT, SUPER_ADMIN
    preferred_language VARCHAR(5) NOT NULL DEFAULT 'en', -- en, hi, mr
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### 2. `merchants`
Stores business profiles, physical store locations, and KYC verification records.
```sql
CREATE TABLE merchants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_name VARCHAR(150) NOT NULL,
    sector VARCHAR(30) NOT NULL,                  -- FOOD, FASHION, FOOTWEAR, ELECTRONICS, REAL_ESTATE
    address_text TEXT NOT NULL,
    city VARCHAR(50) NOT NULL,                    -- Nagpur, Mumbai
    latitude DOUBLE PRECISION NOT NULL,           -- e.g. 21.1458
    longitude DOUBLE PRECISION NOT NULL,          -- e.g. 79.0882
    gstin VARCHAR(20) NULL,
    kyc_doc_url VARCHAR(500) NOT NULL,            -- Cloudinary document URL
    kyc_status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED
    kyc_rejection_reason TEXT NULL,
    profile_video_url VARCHAR(500) NULL,          -- Permanent storefront video (never expires)
    profile_video_thumbnail_url VARCHAR(500) NULL,
    call_clicks_count INTEGER NOT NULL DEFAULT 0, -- Cached total of counted "Call store" taps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### 3. `merchant_staff`
Store cashier accounts for in-store QR code validation. Staff records have an explicit active/inactive lifecycle.
```sql
CREATE TABLE merchant_staff (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    staff_name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    pin_hash VARCHAR(255) NOT NULL,               -- Bcrypt hash of 6-digit staff PIN
    is_active BOOLEAN NOT NULL DEFAULT true,
    can_upload_reels BOOLEAN NOT NULL DEFAULT false, -- Owner-granted reel upload permission
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### 4. `reels`
Vertical 9:16 reels uploaded by merchants. Strictly raw camera audio or voiceovers.
```sql
CREATE TABLE reels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    duration_seconds INTEGER NOT NULL CHECK (duration_seconds BETWEEN 15 AND 60),
    video_url VARCHAR(500) NOT NULL,              -- Cloudinary direct MP4 delivery URL
    thumbnail_url VARCHAR(500) NOT NULL,          -- Cloudinary auto-extracted WebP thumbnail
    cloudinary_public_id VARCHAR(255) NULL,
    audio_type VARCHAR(20) NOT NULL DEFAULT 'CAMERA_MIC', -- CAMERA_MIC, VOICEOVER
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING_MODERATION', -- PENDING_MODERATION, APPROVED, REJECTED
    rejection_reason TEXT NULL,
    views_count INTEGER NOT NULL DEFAULT 0,
    allow_comments BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,                  -- Soft delete (owner, or auto after grace window)
    expires_at TIMESTAMPTZ NULL,                  -- Offer end; set when the reel goes live
    grace_period_until TIMESTAMPTZ NULL,          -- expires_at + 24h: last moment to extend
    is_expired BOOLEAN NOT NULL DEFAULT false,    -- Set by the lifecycle sweep
    created_by_staff_id UUID NULL REFERENCES merchant_staff(id) ON DELETE SET NULL -- Cashier uploader
);
```

#### 5. `coupon_templates`
Incentive definitions attached 1-to-1 to each reel. Enforces sector validity limits.
```sql
CREATE TABLE coupon_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    reel_id UUID UNIQUE NOT NULL REFERENCES reels(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    discount_type VARCHAR(20) NOT NULL,           -- PERCENTAGE, FLAT_AMOUNT, BOGO
    discount_value NUMERIC(10, 2) NOT NULL,
    min_order_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    validity_days INTEGER NOT NULL,               -- Constrained by sector limits
    terms TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    expires_at TIMESTAMPTZ NULL,                  -- Mirrors reels.expires_at; claims refused after it
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### 6. `user_coupons`
Shopper claims stored in the digital wallet. Holds the private cryptographic secret for dynamic TOTP QR codes.
```sql
CREATE TABLE user_coupons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coupon_template_id UUID NOT NULL REFERENCES coupon_templates(id),
    user_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'CLAIMED', -- CLAIMED, REDEEMED, EXPIRED
    totp_secret VARCHAR(64) NOT NULL,             -- Unique Base32 secret for dynamic QR
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    redeemed_at TIMESTAMPTZ NULL,
    backup_pin_used_at TIMESTAMPTZ NULL,
    redeemed_by_staff_id UUID NULL REFERENCES merchant_staff(id)
);
```

#### 7. `redemptions_ledger`
Immutable transaction ledger recording every physical in-store redemption with cashier GPS coordinates.
```sql
CREATE TABLE redemptions_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_coupon_id UUID UNIQUE NOT NULL REFERENCES user_coupons(id),
    merchant_id UUID NOT NULL REFERENCES merchants(id),
    staff_id UUID NULL REFERENCES merchant_staff(id),
    bill_amount NUMERIC(10, 2) NOT NULL,
    discount_applied NUMERIC(10, 2) NOT NULL,
    cashier_latitude DOUBLE PRECISION NULL,
    cashier_longitude DOUBLE PRECISION NULL,
    distance_from_shop_m INTEGER NULL,            -- Verified against 500m geofence perimeter
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### 8. `reel_views`
Records deduplicated authenticated or client-keyed views used to keep `reels.views_count` consistent.
```sql
CREATE TABLE reel_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reel_id UUID NOT NULL REFERENCES reels(id) ON DELETE CASCADE,
    user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    viewer_key VARCHAR(128) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### 9. `merchant_followers`
Shoppers following stores (client requirement 4).
```sql
CREATE TABLE merchant_followers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_merchant_follower UNIQUE (merchant_id, user_id)
);
CREATE INDEX ix_merchant_followers_merchant_id ON merchant_followers(merchant_id);
CREATE INDEX ix_merchant_followers_user_id ON merchant_followers(user_id);
```

#### 10. `merchant_call_clicks`
One row per counted "Call store" tap (client requirement 3). Taps by the same user/device within 60s count once.
```sql
CREATE TABLE merchant_call_clicks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    device_fingerprint VARCHAR(128) NULL,         -- App install id for anonymous de-duplication
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_call_clicks_merchant_created ON merchant_call_clicks(merchant_id, created_at);
```

#### 11. `merchant_ratings`
One 1-5 star rating per shopper per store; re-rating updates the row (client requirement 11).
```sql
CREATE TABLE merchant_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating SMALLINT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_merchant_user_rating UNIQUE (merchant_id, user_id)
);
CREATE INDEX ix_merchant_ratings_merchant_id ON merchant_ratings(merchant_id);
```

#### 12. `system_settings`
Runtime switches flipped by the Super Admin (client requirement 10).
```sql
CREATE TABLE system_settings (
    key VARCHAR(50) PRIMARY KEY,                  -- e.g. 'auto_approve_reels'
    value JSON NOT NULL,                          -- auto_approve_reels: true | false (default false)
    description VARCHAR(255) NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL
);
```
A missing row means "use the default" (`SETTING_DEFAULTS` in `app/models/system_settings.py`), so no seed step is needed.

#### Schema rollout (no Alembic)
New **tables** are created by `Base.metadata.create_all` at startup. New **columns** on existing tables are added by
`ensure_compatibility_schema()` in `app/core/database.py` (the `_COMPAT_COLUMNS` map, with SQLite and PostgreSQL DDL),
which runs once per process before the first request. Restarting the API is enough to upgrade an existing database.

---

### 1.3 Sector Validity Limits (Business Rule Engine)

| Sector | Max Coupon Validity | Rationale |
|---|---|---|
| **FOOD** | **2 to 5 Days** | Perishable inventory; prevents hoarding old food deals. |
| **FASHION** | **Max 15 Days** | Seasonal clearance and rotating fashion trends. |
| **FOOTWEAR** | **Max 15 Days** | Retail inventory cycles. |
| **ELECTRONICS** | **Max 15 Days** | Price volatility and distributor margins. |
| **REAL_ESTATE** | **Up to 60 Days** | Long decision cycle for site visits and token booking. |

The same ceilings cap offer extensions (`POST /reels/{id}/extend-validity`).

---

## 2. Backend Service Execution Flows

### Flow 1: Authentication & Staff POS Setup

```mermaid
sequenceDiagram
    autonumber
    actor User as Shopper / Merchant
    actor Staff as Store Cashier
    participant API as Fyndo FastAPI
    participant Redis as Redis / Cache
    participant DB as PostgreSQL DB

    Note over User, DB: 1. Shopper & Merchant OTP Login
    User->>API: POST /api/v1/auth/otp/send { phone: "+919876543210" }
    API->>Redis: Check Rate Limit (3 req / 10 min)
    API->>Redis: Store 6-digit OTP (TTL: 120s)
    API-->>User: 200 OK { expires_in_seconds: 120 }

    User->>API: POST /api/v1/auth/otp/verify { phone, otp, lang: "hi" }
    API->>Redis: Verify OTP match & delete
    API->>DB: Query or Create User record
    API-->>User: 200 OK { access_token (15m), user } + HttpOnly fyndo_refresh_token cookie

    Note over Staff, DB: 2. Cashier Terminal PIN Login
    Staff->>API: POST /api/v1/auth/staff-login { store_phone, pin: "123456" }
    API->>DB: Find Store by Owner Phone & Fetch Staff
    API->>API: Verify Bcrypt Hash (pin, staff.pin_hash)
    API-->>Staff: 200 OK { access_token (Role: ROLE_CASHIER, merchant_id) }
```

## 3. Issue-Driven API Contracts

- `PATCH /api/v1/merchants/profile` updates only the authenticated merchant's editable store fields.
- `PATCH /api/v1/merchants/kyc` accepts resubmission only while KYC is `REJECTED`; the existing rejection reason remains available until moderation.
- `GET /api/v1/admin/moderation/merchants` and
  `POST /api/v1/admin/moderation/merchants/{id}/decision` are restricted to `SUPER_ADMIN`.
- `POST /api/v1/reels` requires approved merchant KYC and accepts the store owner **or** a cashier with
  `can_upload_reels`. Shopper-facing reel queries hide offers past `expires_at`. `GET /api/v1/reels/mine`,
  `GET/PATCH/DELETE /api/v1/reels/{id}`, and `POST /api/v1/reels/{id}/view` provide
  merchant lifecycle, public retrieval, soft deletion, and deduplicated view tracking.
- `POST /api/v1/redemptions/verify` requires a positive `bill_amount`; percentage and
  flat discounts are capped at the bill amount and minimum-order rules are enforced.
  `POST /api/v1/redemptions/verify-pin` applies the same checks with rate-limited backup PINs.
- Refresh tokens are issued in an `HttpOnly` cookie with `SameSite=Lax` in development
  and `SameSite=Strict; Secure` in production. Clients should send requests with credentials.

---

### Flow 2: Merchant Studio & Cloudinary Ingestion Flow

```mermaid
sequenceDiagram
    autonumber
    actor Merchant as Merchant App
    participant API as Fyndo FastAPI
    participant Cloudinary as Cloudinary API / CDN
    participant DB as PostgreSQL DB

    Merchant->>API: POST /api/v1/media/sign-upload { folder: "reels", resource_type: "video" }
    API->>API: Compute SHA1/HMAC signature using CLOUDINARY_API_SECRET
    API-->>Merchant: 200 OK { signature, timestamp, api_key, upload_url, folder }

    Merchant->>Cloudinary: POST upload_url (Direct Video Binary + Signature)
    Cloudinary-->>Merchant: 200 OK { secure_url, public_id, duration }

    Merchant->>API: POST /api/v1/reels { title, video_url, thumbnail_url, duration, coupon }
    Note over Merchant, API: Caller = owner token, or cashier token with can_upload_reels (Flow 7)
    API->>API: Check store KYC is APPROVED
    API->>API: Validate Audio (CAMERA_MIC or VOICEOVER only)
    API->>API: Cap coupon validity to sector limit (e.g. FOOD <= 5 days)
    API->>DB: Read system_settings.auto_approve_reels
    alt auto-approve OFF (default)
        API->>DB: Insert Reel (status: PENDING_MODERATION, expires_at: NULL)
        API->>DB: Insert CouponTemplate (attached to reel_id)
        API-->>Merchant: 200 OK { reel_id, status: "PENDING_MODERATION" }
    else auto-approve ON
        API->>DB: Insert Reel (status: APPROVED, expires_at = now + validity, grace = +24h)
        API->>DB: Insert CouponTemplate (expires_at = reel.expires_at)
        API-->>Merchant: 200 OK { reel_id, status: "APPROVED" }
    end
```

---

### Flow 3: Super Admin Moderation Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Super Admin
    participant API as Fyndo FastAPI
    participant DB as PostgreSQL DB
    participant CDN as Feed Discovery

    Admin->>API: GET /api/v1/admin/moderation/reels
    API->>DB: Query Reels WHERE status = 'PENDING_MODERATION'
    API-->>Admin: 200 OK [ List of pending reels with video URLs and coupon details ]

    alt Admin Approves Reel
        Admin->>API: POST /api/v1/admin/moderation/reels/{id}/decision { decision: "APPROVE" }
        API->>DB: UPDATE reels SET status = 'APPROVED'
        API->>DB: Start offer clock: expires_at = now + validity_days, grace_period_until = +24h
        API->>DB: Inbox alert to store owner
        API-->>Admin: 200 OK { status: "APPROVED" }
        Note over CDN: Reel immediately surfaces in Proximity Discovery Feed
    else Admin Rejects Reel
        Admin->>API: POST /api/v1/admin/moderation/reels/{id}/decision { decision: "REJECT", rejection_reason: "Copyrighted music detected" }
        API->>DB: UPDATE reels SET status = 'REJECTED', rejection_reason = "..."
        API->>DB: Inbox alert to store owner
        API-->>Admin: 200 OK { status: "REJECTED" }
    end
```
> With auto-approve ON (Flow 8) new reels skip this queue. Reels already pending stay pending.

---

### Flow 4: Hyper-Local Keyset Proximity Feed & Wallet Claim

```mermaid
sequenceDiagram
    autonumber
    actor Shopper as Shopper Client
    participant API as Fyndo FastAPI
    participant DB as PostgreSQL DB

    Shopper->>API: GET /api/v1/reels/feed?lat=21.1460&lon=79.0880&radius_km=5&sector=FOOD
    API->>DB: Query APPROVED, not deleted, (expires_at IS NULL OR expires_at > now) reels in bounding box
    API->>API: Calculate Haversine / PostGIS ST_Distance
    API->>API: Filter to radius (<= 5000m) & sort ascending by distance
    API-->>Shopper: 200 OK [ List of reels with distance_meters & active coupon ]

    Shopper->>API: POST /api/v1/coupons/{template_id}/claim (Bearer Shopper Token)
    API->>API: Reject if template inactive (404) or offer ended (410)
    API->>DB: Check if user already holds active claim (409)
    API->>API: Generate unique Base32 TOTP Secret
    API->>DB: Insert UserCoupon (status: CLAIMED, totp_secret, expires_at)
    Note over API: Store is told instantly — see Flow 9
    API-->>Shopper: 200 OK { user_coupon_id, status: "CLAIMED", expires_at }

    Shopper->>API: GET /api/v1/coupons/wallet
    API->>DB: Query user_coupons for user_id with merchant details
    API-->>Shopper: 200 OK [ List of wallet coupons with status & expiry ]
```

---

### Flow 5: Anti-Fraud In-Store Dynamic TOTP Redemption Loop

```mermaid
sequenceDiagram
    autonumber
    actor Shopper as Shopper (In-Store)
    actor Cashier as Cashier (POS Terminal)
    participant API as Fyndo FastAPI
    participant DB as PostgreSQL DB

    Shopper->>API: GET /api/v1/coupons/{user_coupon_id}/dynamic-qr
    API->>DB: Verify coupon status is CLAIMED and not expired
    API->>API: Generate 60-second RFC 6238 TOTP token & Base64 payload
    API-->>Shopper: 200 OK { qr_payload, totp_token, time_step_remaining_seconds: 52 }
    Note over Shopper: App renders dynamic QR with live animated countdown ring

    Cashier->>Cashier: Scans customer QR using POS scanner
    Cashier->>API: POST /api/v1/redemptions/verify { qr_payload, cashier_lat, cashier_lon }
    API->>API: Decode Base64 payload -> extract claim_id & totp_token
    API->>DB: Fetch UserCoupon by claim_id
    API->>API: Check Anti-Double-Spend: Reject if status == 'REDEEMED' (409 Conflict)
    API->>API: Cryptographic TOTP Verification with ±1 window tolerance
    API->>API: Validate Store Geofence (Haversine distance <= 500m)
    API->>DB: UPDATE user_coupons SET status = 'REDEEMED', redeemed_at = NOW()
    API->>DB: INSERT INTO redemptions_ledger (user_coupon_id, merchant_id, staff_id, discount, location)
    API-->>Cashier: 200 OK { status: "VERIFIED_AND_REDEEMED", discount_applied, customer_name }

    Note over Shopper: Customer wallet status automatically reflects 'REDEEMED'
    Note over Cashier: Any re-scan attempt with same QR immediately fails (409 Conflict)
```

---

### Flow 6: Storefront — Profile Video, Follow, Call Tap & Rating
Client requirements 2, 3, 4, 11.

```mermaid
sequenceDiagram
    autonumber
    actor Owner as Store Owner
    actor Shopper as Shopper App
    participant API as Fyndo FastAPI
    participant Cloudinary as Cloudinary
    participant DB as PostgreSQL DB

    Note over Owner, DB: Permanent store video (never expires)
    Owner->>API: POST /api/v1/media/sign-upload { resource_type: "video" }
    API-->>Owner: 200 OK { signature, upload_url, ... }
    Owner->>Cloudinary: Upload store video
    Cloudinary-->>Owner: { secure_url }
    Owner->>API: PATCH /api/v1/merchants/me/profile-video { profile_video_url, profile_video_thumbnail_url }
    API->>DB: UPDATE merchants SET profile_video_url, profile_video_thumbnail_url
    API-->>Owner: 200 OK

    Note over Shopper, DB: Shopper opens the storefront
    Shopper->>API: GET /api/v1/merchants/{id} (token optional)
    API->>DB: Store + COUNT(followers) + is_following + AVG/COUNT(ratings)
    API-->>Shopper: 200 OK { profile_video_url, followers_count, is_following, rating_average, rating_count }

    Shopper->>API: POST /api/v1/merchants/{id}/follow
    alt not following yet
        API->>DB: INSERT merchant_followers (unique merchant_id+user_id)
        API-->>Shopper: { is_following: true, followers_count }
    else already following
        API->>DB: DELETE merchant_followers row
        API-->>Shopper: { is_following: false, followers_count }
    end

    Shopper->>API: POST /api/v1/merchants/{id}/track-call { device_fingerprint? }
    API->>DB: Same user/device tapped this store in last 60s?
    alt first tap in window
        API->>DB: INSERT merchant_call_clicks + merchants.call_clicks_count += 1 (atomic)
        API-->>Shopper: { counted: true }
    else repeat tap
        API-->>Shopper: { counted: false }
    end
    Shopper->>Shopper: Open phone dialer

    Shopper->>API: POST /api/v1/merchants/{id}/rate { rating: 4, review_text }
    API->>DB: Upsert merchant_ratings (one row per shopper per store)
    API-->>Shopper: 200 OK { rating, review_text, user_name }

    Owner->>API: GET /api/v1/merchants/me/insights
    API->>DB: followers, call taps (total + 7 days), SUM(reel views), rating avg/count
    API-->>Owner: 200 OK { followers_count, call_clicks_total, ... }
```
Owners cannot follow or rate their own store (`400`).

---

### Flow 7: Cashier Reel Upload Permission
Client requirements 6 & 7.

```mermaid
sequenceDiagram
    autonumber
    actor Owner as Store Owner
    actor Cashier as Cashier Terminal
    participant API as Fyndo FastAPI
    participant DB as PostgreSQL DB

    Owner->>API: PATCH /api/v1/merchants/staff/{staff_id}/permissions { can_upload_reels: true }
    API->>DB: Verify staff belongs to owner's store (404 otherwise)
    API->>DB: UPDATE merchant_staff SET can_upload_reels = true
    API-->>Owner: 200 OK { can_upload_reels: true }

    Cashier->>API: POST /api/v1/auth/staff-login { store_phone, pin }
    API-->>Cashier: { access_token (role: ROLE_CASHIER, merchant_id) }

    Cashier->>API: POST /api/v1/reels { ..., coupon } (Bearer cashier token)
    API->>DB: Load staff by token subject
    alt staff inactive or merchant_id claim mismatch
        API-->>Cashier: 401 Staff session is no longer valid
    else can_upload_reels = false
        API-->>Cashier: 403 Ask the store owner to allow you to upload reels
    else allowed
        API->>DB: Insert Reel (created_by_staff_id = staff.id) + CouponTemplate
        API-->>Cashier: 200 OK { reel_id, status }
    end
```
The permission is re-read from the database on every upload, so revoking it takes effect on the cashier's next attempt.
Cashiers cannot extend offers; only the owner can.

---

### Flow 8: Admin Auto-Approve Switch
Client requirement 10.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Super Admin
    participant Panel as HTML Admin Panel (/admin/)
    participant API as Fyndo FastAPI
    participant DB as PostgreSQL DB

    alt From the admin panel
        Admin->>Panel: Tick "Auto-approve reels" on the dashboard
        Panel->>API: POST /admin/settings/auto-approve (enabled=on, admin session cookie)
    else From the REST API
        Admin->>API: PATCH /api/v1/admin/settings { auto_approve_reels: true } (SUPER_ADMIN token)
    end
    API->>DB: Upsert system_settings('auto_approve_reels', true)
    API->>API: Audit log system_settings.update
    API-->>Admin: Saved

    Note over API, DB: Next POST /api/v1/reels is created APPROVED with its offer clock running (Flow 2)
```

---

### Flow 9: Real-Time "Coupon Claimed" Alert to the Store (WebSocket)
Client requirement 9.

```mermaid
sequenceDiagram
    autonumber
    actor Owner as Owner Dashboard
    actor Cashier as Cashier Terminal
    actor Shopper as Shopper App
    participant WS as WS /api/v1/ws/merchants/{id}
    participant Mgr as MerchantConnectionManager
    participant API as Coupon Claim API
    participant DB as PostgreSQL DB

    Owner->>WS: Connect ?token=OWNER_ACCESS_TOKEN
    WS->>DB: Token owner owns this merchant & is active?
    WS->>Mgr: connect(merchant_id, socket)
    WS-->>Owner: { event: "CONNECTED" }
    Cashier->>WS: Connect ?token=CASHIER_ACCESS_TOKEN
    WS->>DB: Staff active & belongs to this merchant?
    WS->>Mgr: connect(merchant_id, socket)
    WS-->>Cashier: { event: "CONNECTED" }

    Shopper->>API: POST /api/v1/coupons/{template_id}/claim
    API->>DB: Insert UserCoupon
    API->>DB: Inbox alert to shopper ("Coupon added to wallet")
    API->>DB: Inbox alert to owner ("New coupon claimed", event_type coupon_enrolled)
    API->>Mgr: broadcast_to_merchant(merchant_id, COUPON_ENROLLED)
    Mgr-->>Owner: { event: "COUPON_ENROLLED", data: { coupon_title, shopper_name, claimed_at, ... } }
    Mgr-->>Cashier: { event: "COUPON_ENROLLED", data: { ... } }
    API-->>Shopper: 200 OK

    Note over Owner, WS: Bad/foreign token -> socket closed with code 1008. "ping" -> "pong".
```
Delivery is best-effort: a failed broadcast never fails the claim, and dead sockets are dropped. If the owner was offline,
the inbox alert is still there. Connections live in one process; several API workers would need Redis pub/sub.

---

### Flow 10: Offer Expiry, 24-Hour Grace Window & Auto-Removal
Client requirements 8 & 12.

```mermaid
sequenceDiagram
    autonumber
    actor Owner as Store Owner
    actor Shopper as Shopper App
    participant API as Fyndo FastAPI
    participant Sweep as Lifecycle Sweep (every 300s)
    participant DB as PostgreSQL DB

    Note over API, DB: Reel goes live (admin approve or auto-approve)
    API->>DB: expires_at = now + validity_days, grace_period_until = expires_at + 24h, coupon.expires_at = expires_at

    Note over Shopper, DB: Offer end passes
    Shopper->>API: GET /reels/feed, GET /reels/{id}, POST /coupons/{id}/claim
    API->>DB: Filter expires_at > now
    API-->>Shopper: Reel hidden (404) / claim refused (410)

    Sweep->>DB: APPROVED reels with no expires_at -> start their clock
    Sweep->>DB: expires_at <= now AND NOT is_expired -> is_expired = true
    Sweep->>DB: Inbox alert to owner "Your offer has ended" (extend within 24h)

    Owner->>API: GET /api/v1/merchants/me/reels/expiring
    API-->>Owner: Reels inside the grace window

    alt Owner extends within 24h
        Owner->>API: POST /api/v1/reels/{id}/extend-validity { additional_days: 3 }
        API->>API: Cap days to sector limit, new expires_at = now + days
        API->>DB: is_expired = false, new grace_period_until, coupon.expires_at & validity_days updated
        API-->>Owner: 200 OK { expires_at, grace_period_until }
        Note over Shopper: Reel visible in feed again immediately
    else Grace window passes
        Sweep->>DB: is_expired AND grace_period_until <= now -> deleted_at = now, coupon.is_active = false
        Sweep->>DB: Inbox alert to owner "Offer removed"
        Owner->>API: POST /api/v1/reels/{id}/extend-validity
        API-->>Owner: 409 The 24-hour window to extend this offer has closed
    end
```
Coupons already in shoppers' wallets keep their own expiry and remain redeemable. The sweep runs inside the API
process (`REEL_LIFECYCLE_SWEEP_SECONDS`, `0` disables it); it is idempotent, so running it more often is safe.

---

## 3. Directory Code Structure

```text
backend/app/
├── api/
│   └── v1/
│       ├── api.py                    # Root v1 APIRouter registration
│       └── endpoints/
│           ├── admin.py              # Moderation queue & approve/reject decisions
│           ├── admin_settings.py     # Super Admin settings (auto_approve_reels)
│           ├── auth.py               # Mobile OTP & Cashier Staff PIN login
│           ├── coupons.py            # Coupon claim & dynamic TOTP QR generator
│           ├── health.py             # Liveness & readiness probes
│           ├── media.py              # Direct Cloudinary signed upload generator
│           ├── merchant_engagement.py # Profile video, follow, call taps, ratings, cashier permission, insights
│           ├── merchants.py          # Store onboarding, staff assignment, public storefront
│           ├── redemptions.py        # In-store POS cashier scanner validation
│           ├── reel_publishing.py    # Create reel (owner/cashier), extend offer, expiring list
│           ├── reels.py              # Proximity feed, reel detail, merchant reel management
│           └── ws.py                 # WebSocket channel for store screens
├── core/
│   ├── config.py                 # Pydantic v2 application settings
│   ├── database.py               # Async SQLAlchemy engine & DB session dependency
│   ├── redis.py                  # Async Redis client with fakeredis fallback
│   └── security.py               # Bcrypt PIN hashing & PyJWT token generator
├── models/
│   ├── coupon.py                 # CouponTemplate, UserCoupon, RedemptionsLedger
│   ├── merchant.py               # Merchant, MerchantStaff
│   ├── merchant_engagement.py    # MerchantFollower, MerchantCallClick, MerchantRating
│   ├── reel.py                   # Reel model (+ offer lifecycle columns)
│   ├── system_settings.py        # SystemSetting + defaults
│   └── user.py                   # User model
├── schemas/
│   ├── admin.py                  # Moderation decision & admin reel schemas
│   ├── auth.py                   # OTP & Staff login schemas
│   ├── common.py                 # Standard Success/Error ResponseEnvelope
│   ├── coupon.py                 # Dynamic QR, wallet item & redemption schemas
│   ├── media.py                  # Cloudinary signature request/response schemas
│   ├── merchant.py               # Onboarding & staff creation schemas
│   ├── merchant_engagement.py    # Follow, rating, call-tap, profile video, insights schemas
│   └── reel.py                   # Reel submission & proximity feed schemas
├── services/
│   ├── cloudinary_service.py     # HMAC upload signature generation
│   ├── coupon_alerts.py          # Owner inbox alert + COUPON_ENROLLED broadcast on claim
│   ├── merchant_engagement_service.py # Follow / call-tap / rating / insights logic
│   ├── otp.py                    # 6-digit OTP dispatch & rate-limiting
│   ├── reel_lifecycle_service.py # Offer clock, extension, expiry/grace sweep
│   ├── settings_service.py       # Read/write system_settings
│   ├── socket_service.py         # In-process WebSocket connection manager
│   └── totp.py                   # RFC 6238 60s dynamic QR generator & validator
└── utils/
    └── geo.py                    # Haversine distance calculator
```
