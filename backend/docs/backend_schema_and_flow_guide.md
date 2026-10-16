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
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL
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

---

### 1.3 Sector Validity Limits (Business Rule Engine)

| Sector | Max Coupon Validity | Rationale |
|---|---|---|
| **FOOD** | **2 to 5 Days** | Perishable inventory; prevents hoarding old food deals. |
| **FASHION** | **Max 15 Days** | Seasonal clearance and rotating fashion trends. |
| **FOOTWEAR** | **Max 15 Days** | Retail inventory cycles. |
| **ELECTRONICS** | **Max 15 Days** | Price volatility and distributor margins. |
| **REAL_ESTATE** | **Up to 60 Days** | Long decision cycle for site visits and token booking. |

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
- `POST /api/v1/reels` requires approved merchant KYC. `GET /api/v1/reels/mine`,
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
    API->>API: Validate Audio (CAMERA_MIC or VOICEOVER only)
    API->>API: Validate Sector Expiry (e.g. FOOD <= 5 days)
    API->>DB: Insert Reel (status: PENDING_MODERATION)
    API->>DB: Insert CouponTemplate (attached to reel_id)
    API-->>Merchant: 201 Created { reel_id, status: "PENDING_MODERATION" }
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
        API-->>Admin: 200 OK { status: "APPROVED" }
        Note over CDN: Reel immediately surfaces in Proximity Discovery Feed
    else Admin Rejects Reel
        Admin->>API: POST /api/v1/admin/moderation/reels/{id}/decision { decision: "REJECT", rejection_reason: "Copyrighted music detected" }
        API->>DB: UPDATE reels SET status = 'REJECTED', rejection_reason = "..."
        API-->>Admin: 200 OK { status: "REJECTED" }
    end
```

---

### Flow 4: Hyper-Local Keyset Proximity Feed & Wallet Claim

```mermaid
sequenceDiagram
    autonumber
    actor Shopper as Shopper Client
    participant API as Fyndo FastAPI
    participant DB as PostgreSQL DB

    Shopper->>API: GET /api/v1/reels/feed?lat=21.1460&lon=79.0880&radius_km=5&sector=FOOD
    API->>DB: Query approved reels with merchant coordinates
    API->>API: Calculate Haversine / PostGIS ST_Distance
    API->>API: Filter to radius (<= 5000m) & sort ascending by distance
    API-->>Shopper: 200 OK [ List of reels with distance_meters & active coupon ]

    Shopper->>API: POST /api/v1/coupons/{template_id}/claim (Bearer Shopper Token)
    API->>DB: Check if user already holds active claim
    API->>API: Generate unique Base32 TOTP Secret
    API->>DB: Insert UserCoupon (status: CLAIMED, totp_secret, expires_at)
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

## 3. Directory Code Structure

```text
backend/app/
├── api/
│   └── v1/
│       ├── api.py                    # Root v1 APIRouter registration
│       └── endpoints/
│           ├── admin.py              # Moderation queue & approve/reject decisions
│           ├── auth.py               # Mobile OTP & Cashier Staff PIN login
│           ├── coupons.py            # Coupon claim & dynamic TOTP QR generator
│           ├── health.py             # Liveness & readiness probes
│           ├── media.py              # Direct Cloudinary signed upload generator
│           ├── merchants.py          # Store onboarding & staff assignment
│           ├── redemptions.py        # In-store POS cashier scanner validation
│           └── reels.py              # Proximity feed & video submission
├── core/
│   ├── config.py                 # Pydantic v2 application settings
│   ├── database.py               # Async SQLAlchemy engine & DB session dependency
│   ├── redis.py                  # Async Redis client with fakeredis fallback
│   └── security.py               # Bcrypt PIN hashing & PyJWT token generator
├── models/
│   ├── coupon.py                 # CouponTemplate, UserCoupon, RedemptionsLedger
│   ├── merchant.py               # Merchant, MerchantStaff
│   ├── reel.py                   # Reel model
│   └── user.py                   # User model
├── schemas/
│   ├── admin.py                  # Moderation decision & admin reel schemas
│   ├── auth.py                   # OTP & Staff login schemas
│   ├── common.py                 # Standard Success/Error ResponseEnvelope
│   ├── coupon.py                 # Dynamic QR, wallet item & redemption schemas
│   ├── media.py                  # Cloudinary signature request/response schemas
│   ├── merchant.py               # Onboarding & staff creation schemas
│   └── reel.py                   # Reel submission & proximity feed schemas
├── services/
│   ├── cloudinary_service.py     # HMAC upload signature generation
│   ├── otp.py                    # 6-digit OTP dispatch & rate-limiting
│   └── totp.py                   # RFC 6238 60s dynamic QR generator & validator
└── utils/
    └── geo.py                    # Haversine distance calculator
```
