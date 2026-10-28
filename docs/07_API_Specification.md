# 07 - API Specification

> **Base URL**: `https://api.fyndo.in/api/v1` (Dev: `http://localhost:5000/api/v1`)  
> **Protocol**: HTTPS / RESTful JSON  
> **Headers**: `Authorization: Bearer <JWT_ACCESS_TOKEN>`, `Content-Type: application/json`

---

## 1. Global Response Standards

### Success Response Envelope
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully"
}
```

### Error Response Envelope
```json
{
  "success": false,
  "error": {
    "code": "INVALID_OTP",
    "message": "The 6-digit OTP entered is incorrect or expired.",
    "details": []
  }
}
```

### Standard HTTP Status Codes
| Code | Meaning | Use Case |
|---|---|---|
| `200 OK` | Success | Read / update actions |
| `201 Created` | Created | Resource creation (claim, upload, account) |
| `400 Bad Request` | Client Error | Schema validation failure, invalid sector expiry |
| `401 Unauthorized` | Auth Required | Missing or expired JWT token |
| `403 Forbidden` | Access Denied | Shopper accessing merchant route; Cashier accessing owner route |
| `404 Not Found` | Not Found | Reel, coupon, or merchant not found |
| `409 Conflict` | Conflict | Coupon already claimed or already redeemed |
| `410 Gone` | Expired | Dynamic TOTP QR code expired |
| `413 Payload Too Large` | Too Large | Upload exceeds the configured media/request ceiling |
| `429 Too Many Requests`| Rate Limited | Rate limit tripped |

---

## 2. Authentication Endpoints

### 2.1 Send Mobile OTP
- **Endpoint**: `POST /auth/otp/send`
- **Auth**: Public (Rate-limited: 3 req / 10 min)
- **Request Body**:
```json
{
  "phone": "+919876543210",
  "channel": "SMS" // "SMS" or "WHATSAPP"
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "phone": "+919876543210",
    "expires_in_seconds": 120
  },
  "message": "OTP sent successfully"
}
```

### 2.2 Verify Mobile OTP
- **Endpoint**: `POST /auth/otp/verify`
- **Auth**: Public
- **Request Body**:
```json
{
  "phone": "+919876543210",
  "otp": "482910",
  "preferred_language": "hi" // "en" | "hi" | "mr"
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "def5020...",
    "user": {
      "id": "c1f7a360-1e5b-4682-a8c6-189679f2ea3a",
      "phone": "+919876543210",
      "role": "SHOPPER",
      "preferred_language": "hi"
    }
  }
}
```

### 2.3 Staff PIN Login
- **Endpoint**: `POST /auth/staff-login`
- **Auth**: Public (POS Terminal)
- **Request Body**:
```json
{
  "store_phone": "+919876543210",
  "pin": "123456"
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "Bearer",
    "staff_id": "a93bc410-staff-uuid",
    "staff_name": "Ramesh (Cashier)",
    "can_upload_reels": true,
    "can_manage_content": true,
    "merchant_id": "8f90-merchant-uuid",
    "business_name": "Royal Bakers"
  },
  "message": "Staff terminal authenticated"
}
```

### 2.4 Super Admin Login
- **Endpoint**: `POST /auth/admin-login`
- **Auth**: Public (Admin Portal)
- **Request Body**:
```json
{
  "identifier": "sudarshanakakde1111@gmail.com",
  "password": "Qweasdzx@1#",
  "mfa_code": "123456"
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "Bearer",
    "user": {
      "id": "admin-uuid",
      "phone": "+919999900000",
      "email": "sudarshanakakde1111@gmail.com",
      "full_name": "Regional Desk Admin",
      "role": "SUPER_ADMIN",
      "preferred_language": "en"
    }
  },
  "message": "Super Admin authenticated"
}
```

### 2.5 Token Refresh Rotation
- **Endpoint**: `POST /auth/refresh`
- **Auth**: Public (Refresh Token Bearer)
- **Request Body**:
```json
{
  "refresh_token": "eyJhbGciOi..."
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "Bearer"
  },
  "message": "Token refreshed successfully"
}
```

### 2.6 Session Logout & Revocation
- **Endpoint**: `POST /auth/logout`
- **Auth**: Public / Optional Bearer
- **Request Body**:
```json
{
  "refresh_token": "eyJhbGciOi..."
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "logged_out": true
  },
  "message": "Logged out successfully"
}
```

### 2.7 Get Current Authenticated Profile
- **Endpoint**: `GET /auth/me`
- **Auth**: Bearer Token (`Authorization: Bearer <access_token>`)
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "id": "c1f7a360-1e5b-4682-a8c6-189679f2ea3a",
    "phone": "+919876543210",
    "full_name": "Haldiram's Sitabuldi",
    "email": "store@haldirams.com",
    "role": "MERCHANT",
    "preferred_language": "mr",
    "merchant_id": "8f90-merchant-uuid",
    "business_name": "Haldiram's Sitabuldi",
    "kyc_status": "APPROVED"
  }
}
```

### 2.8 Update Profile Information
- **Endpoint**: `PATCH /auth/profile`
- **Auth**: Bearer Token (`Authorization: Bearer <access_token>`)
- **Request Body**:
```json
{
  "full_name": "Rohan Deshmukh",
  "email": "rohan@example.com",
  "preferred_language": "hi"
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "id": "user-uuid",
    "phone": "+919876543210",
    "full_name": "Rohan Deshmukh",
    "email": "rohan@example.com",
    "role": "SHOPPER",
    "preferred_language": "hi"
  },
  "message": "Profile updated successfully"
}
```

### 2.9 Fast-Lane Development Token Generator
- **Endpoint**: `POST /auth/dev-token`
- **Auth**: Public (Development Environment Only)
- **Request Body**:
```json
{
  "role": "MERCHANT" // "SHOPPER" | "MERCHANT" | "ROLE_CASHIER" | "SUPER_ADMIN"
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "Bearer",
    "role": "MERCHANT",
    "user": { ... }
  },
  "message": "Development token generated for MERCHANT"
}
```

---

## 3. Reel Discovery & Video Endpoints

### 3.1 Proximity-Based Feed
- **Endpoint**: `GET /reels/feed`
- **Auth**: Optional / Shopper
- **Query Parameters**:
  - `lat` (required): `21.1458`
  - `lon` (required): `79.0882`
  - `radius_km` (optional, default `5`): `2 | 5 | 10`
  - `sector` (optional): `FOOD | FASHION | FOOTWEAR | ELECTRONICS | REAL_ESTATE`
  - `cursor` (optional): UUID of last item for keyset pagination
  - `limit` (optional, default `10`): `10`
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "reels": [
      {
        "id": "e42790bd-128a-4d2c-a0e2-6d27ca54c301",
        "title": "Fresh Sourdough & Brownies 50% Off",
        "video_url": "https://cdn.fyndo.in/videos/e42790bd.mp4",
        "thumbnail_url": "https://cdn.fyndo.in/thumbnails/e42790bd.webp",
        "duration_seconds": 28,
        "views_count": 1420,
        "merchant": {
          "id": "8f90...",
          "business_name": "The Crust Bakery",
          "sector": "FOOD",
          "distance_meters": 650,
          "address": "Shop 4, Dharampeth, Nagpur"
        },
        "coupon": {
          "id": "3b12...",
          "title": "Flat 50% Off on Bakery Items",
          "discount_type": "PERCENTAGE",
          "discount_value": 50.00,
          "min_order_amount": 200.00,
          "validity_days": 3
        }
      }
    ],
    "next_cursor": "e42790bd-..."
  }
}
```

### 3.2 Request Signed Cloudinary Upload Parameters
- **Endpoint**: `POST /media/sign-upload`
- **Auth**: Required (`ROLE_MERCHANT`)
- **Request Body**:
```json
{
  "folder": "reels", // "reels" | "kyc"
  "resource_type": "video" // "video" | "image" | "auto"
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "cloud_name": "fyndo-cloud",
    "api_key": "981273918273918",
    "timestamp": 1728130000,
    "signature": "c89b2f489f02938478d3840...",
    "folder": "fyndo/reels",
    "upload_url": "https://api.cloudinary.com/v1_1/fyndo-cloud/video/upload"
  }
}
```

### 3.3 Create Reel & Attach Coupon
- **Endpoint**: `POST /reels`
- **Auth**: Required, either of:
  - **Store owner** (`ROLE_MERCHANT` access token), or
  - **Cashier** (`ROLE_CASHIER` token from `POST /auth/staff-login`) whose owner has switched on
    `can_upload_reels` (see [7.8](#78-grant--revoke-cashier-reel-upload)).
- **Rules**
  - The store's KYC must be `APPROVED`.
  - Every reel is created together with exactly **one** coupon (`coupon` is mandatory).
  - `coupon.validity_days` is silently capped by the sector limit (FOOD 5, FASHION/FOOTWEAR/ELECTRONICS 15, REAL_ESTATE 60).
  - Starting status depends on the Super Admin **auto-approve** switch ([5.6](#56-platform-settings--auto-approve-reels)):

    | `auto_approve_reels` | Reel `status` on create | Offer clock |
    |---|---|---|
    | `false` (default) | `PENDING_MODERATION` | Starts when an admin approves ([5.2](#52-approve--reject-reel)) |
    | `true` | `APPROVED` (live in feed immediately) | Starts now |

  - When a cashier uploads, `reels.created_by_staff_id` records who did it.
- **Request Body**:
```json
{
  "title": "Exclusive Festive Saree Clearance",
  "cloudinary_public_id": "fyndo/reels/e42790bd",
  "video_url": "https://res.cloudinary.com/fyndo-cloud/video/upload/q_auto,f_auto/v1/fyndo/reels/e42790bd.mp4",
  "thumbnail_url": "https://res.cloudinary.com/fyndo-cloud/video/upload/so_0,w_720,ar_9:16,c_fill/v1/fyndo/reels/e42790bd.webp",
  "duration_seconds": 45,
  "audio_type": "VOICEOVER",
  "allow_comments": true,
  "coupon": {
    "title": "Flat ₹500 Off on Silk Sarees",
    "discount_type": "FLAT_AMOUNT",
    "discount_value": 500.00,
    "min_order_amount": 2500.00,
    "validity_days": 15,
    "terms": "Valid in-store only. 1 coupon per customer."
  }
}
```
- **Response `200 OK`** (auto-approve off):
```json
{
  "success": true,
  "data": { "reel_id": "e42790bd-...", "status": "PENDING_MODERATION" },
  "message": "Reel created and submitted for admin review."
}
```
- **Response `200 OK`** (auto-approve on):
```json
{
  "success": true,
  "data": { "reel_id": "e42790bd-...", "status": "APPROVED" },
  "message": "Reel is live for shoppers."
}
```
- **Errors**

  | Status | When |
  |---|---|
  | `400` | No thumbnail and no server default thumbnail configured |
  | `401` | Missing/expired token, or cashier deactivated / token's store no longer matches |
  | `403` | Caller has no store; store KYC not approved; cashier without upload permission ("Ask the store owner to allow you to upload reels.") |
  | `422` | Body validation failed (e.g. `duration_seconds` outside 5–180, missing `coupon`) |

### 3.4 Reel Engagement — Views, Likes & Comments
- **`POST /reels/{reel_id}/view`** — Auth: Optional. Records a deduplicated daily view and atomically increments `views_count`. Rate-limited (600 / min).
  - **Response `200 OK`**: `{ "success": true, "data": { "views_count": 1421, "counted": true } }` (`counted=false` when the viewer already watched today).
- **`POST /reels/{reel_id}/like`** — Auth: Required (`ROLE_SHOPPER`). Toggles the caller's like. Rate-limited (120 / min).
  - **Response `200 OK`**: `{ "success": true, "data": { "liked": true, "likes_count": 87 } }`
- **`GET /reels/{reel_id}/comments`** — Auth: Public. Oldest first, capped at 200. Rate-limited (240 / min).
- **`POST /reels/{reel_id}/comments`** — Auth: Required. Rate-limited (30 / min).
  - **Response `201 Created`**: creates a comment; returns `403` when `allow_comments` is disabled on the reel.

### 3.5 Media Pipeline Configuration
- **Endpoint**: `GET /media/config`
- **Auth**: Required
- **Response `200 OK`**: Exposes the active upload ceilings so clients can pre-validate files.
```json
{
  "success": true,
  "data": {
    "max_video_mb": 60,
    "max_image_mb": 8,
    "reels_folder": "reels",
    "kyc_folder": "kyc"
  }
}
```
> Uploads exceeding these ceilings are rejected with `413 Payload Too Large` by the request-body guard before reaching the handler.

### 3.6 System Health Probe
- **Endpoint**: `GET /health`
- **Auth**: Public
- **Response `200 OK`**: Probes the database (`SELECT 1`) and Redis (`PING`).
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "service": "Fyndo Core API",
    "environment": "development",
    "database": "connected",
    "cache": "connected"
  }
}
```
> `status` degrades to `degraded` when the database is unreachable; cache outages are reported per-dependency.

### 3.7 Offer Validity, 24-Hour Grace Window & Auto-Removal

Each reel's offer has a lifetime. The coupon template mirrors the reel's end date.

```text
 reel goes live            expires_at                 grace_period_until
 (approve / auto-approve)  (= live + validity_days)   (= expires_at + 24h)
 ───────●──────────────────────────●──────────────────────────●──────────────▶
        │      LIVE                │   ENDED – GRACE WINDOW   │   REMOVED
        │ shown in feed            │ hidden from shoppers     │ deleted_at set
        │ coupon claimable         │ claims refused (410)     │ coupon is_active=false
        │ owner may extend         │ owner may extend         │ cannot extend (409)
```

| State | `is_expired` | `deleted_at` | Feed / `GET /reels/{id}` | Claim | Extend |
|---|---|---|---|---|---|
| Pending moderation | `false` | `null` | Hidden | — | `409` "not live yet" |
| Live | `false` | `null` | Shown | Allowed | Allowed |
| Ended (grace window) | `true` | `null` | Hidden (`404`) | `410` | Allowed |
| Removed | `true` | set | Hidden (`404`) | `404` (inactive) | `409` |

- **Hiding is immediate**: every shopper-facing query filters `expires_at IS NULL OR expires_at > now`, so an ended
  offer disappears at the exact second it ends, even before the background sweep runs.
- **Background sweep** (`REEL_LIFECYCLE_SWEEP_SECONDS`, default `300`, `0` disables) runs inside the API process and:
  1. starts the clock for any `APPROVED` reel that has none (e.g. approved by editing the row in the HTML admin panel),
  2. marks reels past `expires_at` as `is_expired=true` and sends the owner an inbox alert
     (`event_type: reel_offer_expired`, "Your offer has ended"),
  3. soft-deletes reels past `grace_period_until`, deactivates the coupon and alerts the owner
     (`event_type: reel_offer_removed`, "Offer removed").
- Coupons already in shoppers' wallets keep their own `user_coupons.expires_at` and stay redeemable until then.
- Feed and reel-detail coupon objects now include `"expires_at"` so the app can show a countdown.

#### 3.7.1 Extend Offer Validity
- **Endpoint**: `POST /reels/{reel_id}/extend-validity`
- **Auth**: Required (store owner only — cashiers cannot extend)
- **Rules**: new end date = **now + `additional_days`**, capped by the sector limit. Allowed while the offer is live
  or inside the 24-hour grace window. Extending resets `is_expired=false`, sets a new `grace_period_until`, and updates
  `coupon_templates.expires_at` and `validity_days`. The reel reappears in the feed immediately.
- **Request Body**:
```json
{ "additional_days": 3 }
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "reel_id": "e42790bd-...",
    "expires_at": "2026-10-22T18:30:00Z",
    "grace_period_until": "2026-10-23T18:30:00Z"
  },
  "message": "Offer extended."
}
```
- **Errors**

  | Status | Message |
  |---|---|
  | `403` | "Only store owners can extend offers." |
  | `404` | "Reel not found." (not this store's reel) |
  | `409` | "This offer is not live yet." / "The 24-hour window to extend this offer has closed." / "This offer has already been removed." / "The new end date must be later than the current one." |
  | `422` | `additional_days` outside 1–60 |

#### 3.7.2 List Offers Awaiting Extension
- **Endpoint**: `GET /merchants/me/reels/expiring`
- **Auth**: Required (store owner)
- **Returns** reels whose offer has ended but are still inside the grace window, soonest removal first.
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": [
    {
      "id": "e42790bd-...",
      "title": "Weekend Special",
      "status": "APPROVED",
      "views_count": 312,
      "expires_at": "2026-10-19T12:00:00Z",
      "grace_period_until": "2026-10-20T12:00:00Z",
      "is_expired": true,
      "created_by_staff_id": null,
      "video_url": "...", "thumbnail_url": "...", "duration_seconds": 30,
      "allow_comments": true, "created_at": "...", "updated_at": "...", "deleted_at": null
    }
  ]
}
```
- `GET /reels/mine` returns the same lifecycle fields (`expires_at`, `grace_period_until`, `is_expired`, `created_by_staff_id`) for every reel.

---

## 4. Coupon Wallet & Redemption Endpoints

### 4.1 Claim Reel Coupon
- **Endpoint**: `POST /coupons/:coupon_template_id/claim`
- **Auth**: Required (`ROLE_SHOPPER`)
- **Rules**: the coupon must be active and its offer must not have ended (`coupon_templates.expires_at`). One active claim per shopper per coupon.
- **Side effects** (client requirement 9):
  1. Shopper gets an inbox alert "Coupon added to wallet".
  2. Store owner gets an inbox alert "New coupon claimed" (`event_type: coupon_enrolled`).
  3. Every open store screen (owner dashboard + cashier terminal) receives a live `COUPON_ENROLLED` event over the
     WebSocket channel ([8](#8-real-time-store-channel-websocket)).
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "user_coupon_id": "8120fa49-...",
    "status": "CLAIMED",
    "claimed_at": "2026-10-05T14:30:00Z",
    "expires_at": "2026-10-08T14:30:00Z"
  },
  "message": "Coupon claimed to wallet successfully!"
}
```
- **Errors**: `404` coupon not found / inactive · `409` already holds an active claim · `410` "This offer has ended."

### 4.2 Generate Dynamic In-Store TOTP QR
- **Endpoint**: `GET /coupons/:user_coupon_id/dynamic-qr`
- **Auth**: Required (`ROLE_SHOPPER`)
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "qr_payload": "eyJjbGFpbV9pZCI6IjgxMjBmYTQ5Li4iLCJ0b2tlbiI6IjU4MjkwMSIsInRzIjoxNzI4MTMwMjAwfQ==",
    "totp_token": "582901",
    "time_step_remaining_seconds": 48,
    "backup_offline_pin": "8902"
  }
}
```

### 4.3 Cashier QR Pre-Validation & Preview
- **Endpoint**: `POST /redemptions/preview`
- **Auth**: Required (`ROLE_CASHIER` or `ROLE_MERCHANT`)
- **Request Body**:
```json
{
  "qr_payload": "eyJjbGFpbV9pZCI6IjgxMjBmYTQ5Li4iLCJ0b2tlbiI6IjU4MjkwMSIsInRzIjoxNzI4MTMwMjAwfQ=="
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "user_coupon_id": "8120fa49-...",
    "coupon_title": "Flat ₹500 Off",
    "discount_type": "FLAT_AMOUNT",
    "discount_value": 500.0,
    "min_order_amount": 1500.0,
    "customer_name": "Rahul M.",
    "customer_phone": "+919876543210"
  },
  "message": "Voucher verified successfully for this store."
}
```
- **Errors**:
  - `400 Bad Request`: Unrecognized or malformed QR code.
  - `403 Forbidden`: Wrong store (e.g. coupon belongs to a different merchant).
  - `409 Conflict`: Coupon already redeemed earlier.
  - `410 Gone`: Coupon expired or 60s dynamic TOTP token expired.

### 4.4 Cashier Redemption Verification (POS Scan)
- **Endpoint**: `POST /redemptions/verify`
- **Auth**: Required (`ROLE_CASHIER` or `ROLE_MERCHANT`)
- **Request Body**:
```json
{
  "qr_payload": "eyJjbGFpbV9pZCI6IjgxMjBmYTQ5Li4iLCJ0b2tlbiI6IjU4MjkwMSIsInRzIjoxNzI4MTMwMjAwfQ==",
  "cashier_lat": 21.1458,
  "cashier_lon": 79.0882
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "redemption_id": "7fa201b...",
    "status": "VERIFIED_AND_REDEEMED",
    "discount_applied": 500.00,
    "customer_name": "Rahul M.",
    "coupon_title": "Flat ₹500 Off",
    "timestamp": "2026-10-05T14:32:10Z"
  },
  "message": "Coupon successfully redeemed!"
}
```

---

## 5. Admin Moderation Endpoints

### 5.1 List Pending Reels
- **Endpoint**: `GET /admin/moderation/reels`
- **Auth**: Required (`ROLE_SUPER_ADMIN`)
- **Response `200 OK`**: Returns array of reels pending review with video stream URL and coupon terms.

### 5.2 Approve / Reject Reel
- **Endpoint**: `POST /admin/moderation/reels/:id/decision`
- **Auth**: Required (`ROLE_SUPER_ADMIN`)
- **Request Body**:
```json
{
  "decision": "APPROVE", // "APPROVE" | "REJECT"
  "rejection_reason": null // required if REJECT
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "message": "Reel approved and pushed to live discovery feed."
}
```
- Approving starts the offer clock: `expires_at = now + coupon.validity_days`, `grace_period_until = expires_at + 24h` (see 3.7).
  The owner gets an inbox alert for both approve and reject.

### 5.3 Platform Health & Overview Stats
- **Endpoint**: `GET /admin/stats`
- **Auth**: Required (`ROLE_SUPER_ADMIN`)
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "total_merchants": 24,
    "total_users": 150,
    "total_reels": 30,
    "total_redemptions": 48,
    "total_discount_applied": 14200.00,
    "pending_moderation_count": 2
  }
}
```

### 5.4 Admin Merchants Management
- **Endpoints**:
  - `GET /admin/merchants`: List all stores with KYC status, owner phone, staff credentials, and reels count.
  - `POST /admin/merchants`: Direct onboarding of store with owner account and cashier PIN.
  - `PUT /admin/merchants/:id`: Update business details, GPS coordinates, address, and KYC status.
  - `PUT /admin/merchants/:id/staff`: Set or reset cashier name, phone, and 6-digit scanner PIN.

### 5.5 Admin Reels & Offers Desk
- **Endpoints**:
  - `GET /admin/reels?status=ALL|APPROVED|PENDING_MODERATION|REJECTED`: List all platform video reels.
  - `POST /admin/reels`: Direct publication of an approved reel with attached coupon template.

### 5.6 Platform Settings — Auto-Approve Reels
Client requirement 10. Default is **off** (every reel goes through moderation).

#### `GET /admin/settings`
- **Auth**: Required (`ROLE_SUPER_ADMIN`)
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": [
    {
      "key": "auto_approve_reels",
      "value": false,
      "description": "Publish new merchant reels instantly without admin review.",
      "updated_at": null
    }
  ]
}
```

#### `PATCH /admin/settings`
- **Auth**: Required (`ROLE_SUPER_ADMIN`)
- **Request Body** (omit a field to leave it unchanged):
```json
{ "auto_approve_reels": true }
```
- **Response `200 OK`**: the full settings list (same shape as GET) with `"message": "Settings saved."`
- Every change is written to the audit log (`system_settings.update`).
- **Errors**: `403` non-admin caller.

#### HTML admin panel
The dashboard at `/admin/` shows a **Reel publishing → Auto-approve reels** switch. Ticking it posts to
`POST /admin/settings/auto-approve` (form field `enabled=on`) and takes effect for the next reel created.
Reels already waiting in moderation are **not** auto-approved retroactively.

---

## 6. Notification Inbox & Push Endpoints

All endpoints require a valid user access token. Alerts are written automatically as a side effect of
domain events (coupon claimed/redeemed, merchant KYC decided, reel moderated); clients only read the
inbox and manage their push registration.

### 6.1 List Inbox
- **Endpoint**: `GET /notifications`
- **Auth**: Required
- **Query Parameters**: `category` (`ALL|DEALS|UPDATES|RADAR|SYSTEM`), `unread_only` (bool), `limit` (1–100, default 30), `cursor` (opaque keyset cursor)
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "b1f0c9d2-...",
        "category": "DEALS",
        "event_type": "coupon_claimed",
        "title": "Coupon added to wallet",
        "body": "“Flat 20% off” is ready. Show the QR at the store to redeem.",
        "image_url": null,
        "action_type": "COUPON",
        "action_ref": "0c7d...",
        "payload": null,
        "is_read": false,
        "created_at": "2026-10-17T09:12:44Z",
        "expires_at": null
      }
    ],
    "unread_count": 3,
    "next_cursor": "MTc2MDY5...",
    "has_more": true
  }
}
```

### 6.2 Unread Badge Count
- **Endpoint**: `GET /notifications/unread-count`
- **Auth**: Required
- **Response `200 OK`**: `{ "success": true, "data": { "unread_count": 3 } }`

### 6.3 Mark One Alert Read
- **Endpoint**: `POST /notifications/:id/read`
- **Auth**: Required
- **Response `200 OK`**: `{ "success": true, "data": { "notification_id": "b1f0...", "is_read": true } }`
- **Errors**: `404` when the alert does not belong to the caller.

### 6.4 Mark All Alerts Read
- **Endpoint**: `POST /notifications/read-all`
- **Auth**: Required
- **Response `200 OK`**: `{ "success": true, "data": { "updated": 3 } }`

### 6.5 Register Push Device
- **Endpoint**: `POST /notifications/device-token`
- **Auth**: Required
- **Request Body**:
```json
{
  "token": "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
  "platform": "ANDROID"
}
```
- **Response `201 Created`**: `{ "success": true, "data": { "id": "...", "platform": "ANDROID", "is_active": true } }`
- **Behaviour**: re-registering an existing token reactivates it and re-assigns it to the current user.

### 6.6 Unregister Push Device
- **Endpoint**: `POST /notifications/device-token/unregister`
- **Auth**: Required
- **Request Body**: `{ "token": "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]" }`
- **Response `200 OK`**: `{ "success": true, "data": { "removed": true } }`
- **Behaviour**: idempotent — `removed` is `false` when the token was already inactive. Called on sign-out.

---

## 7. Storefront Engagement Endpoints

Literal paths (`/merchants/me/...`, `/merchants/following`) are registered before `/merchants/{merchant_id}`.
Public endpoints only see stores whose KYC is `APPROVED`; others return `404 "Store not found."`.

### 7.1 Public Storefront (extended)
- **Endpoint**: `GET /merchants/{merchant_id}`
- **Auth**: Optional (when signed in, `is_following` reflects the caller)
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "id": "8f90...",
    "business_name": "The Crust Bakery",
    "sector": "FOOD",
    "address_text": "Shop 4, Dharampeth, Nagpur",
    "city": "Nagpur",
    "latitude": 21.1458,
    "longitude": 79.0882,
    "profile_video_url": "https://res.cloudinary.com/.../store.mp4",
    "profile_video_thumbnail_url": "https://res.cloudinary.com/.../store.webp",
    "followers_count": 128,
    "is_following": true,
    "rating_average": 4.5,
    "rating_count": 36
  }
}
```

### 7.2 Set Permanent Store Video
Client requirement 2. Unlike reels, this video never expires and has no coupon.
- **Endpoint**: `PATCH /merchants/me/profile-video`
- **Auth**: Required (store owner)
- **Flow**: get an upload signature from `POST /media/sign-upload` (`resource_type: "video"`), upload to Cloudinary,
  then save the returned URLs here. Calling it again replaces the video.
- **Request Body**:
```json
{
  "profile_video_url": "https://res.cloudinary.com/fyndo-cloud/video/upload/v1/fyndo/stores/8f90.mp4",
  "profile_video_thumbnail_url": "https://res.cloudinary.com/fyndo-cloud/video/upload/so_0/v1/fyndo/stores/8f90.webp"
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "merchant_id": "8f90...",
    "profile_video_url": "https://.../8f90.mp4",
    "profile_video_thumbnail_url": "https://.../8f90.webp"
  },
  "message": "Store video updated."
}
```
- `GET /merchants/profile` (owner) also returns `profile_video_url`, `profile_video_thumbnail_url`, `call_clicks_count`.
- **Errors**: `403` caller has no store · `422` URL missing / longer than 500 chars.

### 7.3 Track "Call Store" Tap
Client requirement 3. Call this **just before** opening the phone dialer.
- **Endpoint**: `POST /merchants/{merchant_id}/track-call`
- **Auth**: Optional. Signed-in shoppers are de-duplicated by user; anonymous visitors should send a stable
  `device_fingerprint` (an app-generated install id).
- **De-duplication**: repeat taps from the same user (or same fingerprint) on the same store within **60 seconds** are not counted.
  Anonymous taps without a fingerprint are always counted.
- **Request Body** (optional):
```json
{ "device_fingerprint": "install-3f1c2a9e" }
```
- **Response `200 OK`**:
```json
{ "success": true, "data": { "counted": true } }
```
- **Errors**: `404` store not found / not approved.

### 7.4 Follow / Unfollow Store
Client requirement 4. A single toggle endpoint.
- **Endpoint**: `POST /merchants/{merchant_id}/follow`
- **Auth**: Required (shopper)
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": { "merchant_id": "8f90...", "is_following": true, "followers_count": 129 },
  "message": "Following this store."
}
```
  Calling again returns `"is_following": false` and `"message": "Unfollowed this store."`.
- **Errors**: `400` "You cannot follow your own store." · `404` store not found.

### 7.5 List Followed Stores
- **Endpoint**: `GET /merchants/following`
- **Auth**: Required (shopper). Most recently followed first.
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": [
    {
      "id": "8f90...",
      "business_name": "The Crust Bakery",
      "sector": "FOOD",
      "city": "Nagpur",
      "address_text": "Shop 4, Dharampeth, Nagpur",
      "profile_video_thumbnail_url": "https://.../8f90.webp",
      "followed_at": "2026-10-19T10:15:00Z"
    }
  ]
}
```

### 7.6 Rate Store
Client requirement 11. One rating per shopper per store; posting again **updates** the existing rating.
- **Endpoint**: `POST /merchants/{merchant_id}/rate`
- **Auth**: Required (shopper)
- **Request Body**:
```json
{ "rating": 4, "review_text": "Fresh bread and quick billing." }
```
  `rating` 1–5 (required). `review_text` optional, max 1000 chars; blank text is stored as `null`.
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "id": "c1d2...",
    "rating": 4,
    "review_text": "Fresh bread and quick billing.",
    "user_name": "Sudarshan",
    "updated_at": "2026-10-19T10:20:00Z"
  },
  "message": "Thanks for rating this store!"
}
```
- **Errors**: `400` "You cannot rate your own store." · `404` store not found · `422` rating outside 1–5.

### 7.7 Store Ratings Summary & Reviews
- **Endpoint**: `GET /merchants/{merchant_id}/ratings?limit=20`
- **Auth**: Optional (when signed in, `my_rating` is the caller's own stars)
- **Query**: `limit` 1–100, default 20 (latest reviews first)
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "merchant_id": "8f90...",
    "average": 4.5,
    "count": 36,
    "breakdown": { "1": 0, "2": 1, "3": 2, "4": 12, "5": 21 },
    "my_rating": 4,
    "reviews": [
      { "id": "c1d2...", "rating": 4, "review_text": "Fresh bread...", "user_name": "Sudarshan", "updated_at": "..." }
    ]
  }
}
```
  `average` is rounded to 1 decimal; `0.0` when there are no ratings. Reviewers without a name show as "Fyndo shopper".

### 7.8 Grant / Revoke Cashier Reel Upload
Client requirements 6 & 7.
- **Endpoint**: `PATCH /merchants/staff/{staff_id}/permissions`
- **Auth**: Required (store owner of that staff member)
- **Request Body**:
```json
{ "can_upload_reels": true }
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": { "id": "5a7b...", "staff_name": "Ravi", "phone": "+919800000000", "is_active": true, "can_upload_reels": true },
  "message": "Staff can now upload reels."
}
```
- Takes effect immediately — the permission is re-checked on every upload, so revoking it blocks the cashier's
  very next attempt without a new login. `GET /merchants/staff` also returns `can_upload_reels`.
- **Errors**: `403` caller has no store · `404` staff member not in caller's store.

### 7.8.1 Remove Staff Member
- **Endpoint**: `DELETE /merchants/staff/{staff_id}`
- **Auth**: Required (store owner)
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": { "deleted_id": "5a7b..." },
  "message": "Staff member removed successfully."
}
```
- **Errors**: `403` caller has no store · `404` staff member not found in caller's store.

### 7.9 Store Insights
Gives the owner the numbers behind requirements 3, 4, 5 and 11.
- **Endpoint**: `GET /merchants/me/insights`
- **Auth**: Required (store owner)
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "followers_count": 128,
    "call_clicks_total": 54,
    "call_clicks_last_7_days": 9,
    "reel_views_total": 12840,
    "rating_average": 4.5,
    "rating_count": 36
  }
}
```
- Per-reel view counts (requirement 5) are on each item of `GET /reels/mine` (`views_count`); views are recorded with
  `POST /reels/{reel_id}/view` (one per viewer per day, see 3.4).

---

## 8. Real-Time Store Channel (WebSocket)

Client requirement 9.

- **Endpoint**: `WS /ws/merchants/{merchant_id}?token=<access token>`
  (dev: `ws://localhost:5000/api/v1/ws/merchants/{merchant_id}?token=...`, prod: `wss://api.fyndo.in/api/v1/ws/...`)
- **Auth**: the token goes in the query string because browsers cannot set headers on WebSockets. Accepted tokens:
  - the store owner's access token, or
  - an **active** cashier token belonging to that store.

  Anything else (no token, expired token, a shopper, another store's owner) is closed immediately with code **`1008`** (policy violation).
- **Server → client messages** (JSON):

  | `event` | When | `data` |
  |---|---|---|
  | `CONNECTED` | Right after a successful handshake | `{ "merchant_id": "..." }` |
  | `COUPON_ENROLLED` | A shopper claimed one of this store's coupons | see below |

```json
{
  "event": "COUPON_ENROLLED",
  "data": {
    "coupon_template_id": "3b12...",
    "user_coupon_id": "8120fa49-...",
    "reel_id": "e42790bd-...",
    "coupon_title": "Flat 20% OFF",
    "shopper_name": "Sudarshan",
    "claimed_at": "2026-10-19T18:35:00Z"
  }
}
```
  `shopper_name` falls back to the username, then "A shopper".
- **Client → server**: send the text `ping` (e.g. every 25s) and the server answers `pong`; other text is ignored.
- **Reconnect**: on close (other than `1008`), reconnect with backoff (1s, 2s, 5s, max 30s). After an access-token
  refresh, reconnect with the new token. Events missed while disconnected are still in the owner's inbox
  (`GET /notifications`, `event_type: coupon_enrolled`).
- **Scaling note**: connections are held in the API process. Running more than one worker needs a shared broker
  (e.g. Redis pub/sub) in front of the broadcast.

**Minimal browser client**
```js
const ws = new WebSocket(`${WS_BASE}/api/v1/ws/merchants/${merchantId}?token=${accessToken}`);
ws.onmessage = ({ data }) => {
  if (data === "pong") return;
  const msg = JSON.parse(data);
  if (msg.event === "COUPON_ENROLLED") showToast(`${msg.data.shopper_name} claimed ${msg.data.coupon_title}`);
};
const keepAlive = setInterval(() => ws.readyState === 1 && ws.send("ping"), 25000);
ws.onclose = (e) => { clearInterval(keepAlive); if (e.code !== 1008) scheduleReconnect(); };
```

---

## 9. Client Requirements → API Map

| # | Requirement | Endpoints / mechanism |
|---|---|---|
| 1 | Nearby deals by allowing location | `GET /reels/feed?lat&lon&radius_km` (3.1) — only live, unexpired offers |
| 2 | Permanent store profile video | `PATCH /merchants/me/profile-video` (7.2), shown on `GET /merchants/{id}` (7.1) |
| 3 | Track call clicks | `POST /merchants/{id}/track-call` (7.3), totals in `GET /merchants/me/insights` (7.9) |
| 4 | Follow shops | `POST /merchants/{id}/follow` (7.4), `GET /merchants/following` (7.5) |
| 5 | Reel view tracking | `POST /reels/{id}/view` (3.4), `views_count` in `GET /reels/mine`, total in insights |
| 6 | Owner gives cashier upload access | `PATCH /merchants/staff/{staff_id}/permissions` (7.8) |
| 7 | Cashier uploads reels | `POST /reels` with a cashier token (3.3) |
| 8 | Reels removed when offer ends, 24h to extend | Lifecycle sweep + `POST /reels/{id}/extend-validity` + `GET /merchants/me/reels/expiring` (3.7) |
| 9 | Notify merchant on coupon claim (web sockets) | `WS /ws/merchants/{id}` `COUPON_ENROLLED` (8) + inbox alert (4.1) |
| 10 | Auto-approve toggle in admin panel | `GET/PATCH /admin/settings` (5.6) + dashboard switch |
| 11 | Shoppers rate shops | `POST /merchants/{id}/rate` (7.6), `GET /merchants/{id}/ratings` (7.7) |
| 12 | Every reel has a coupon | `coupon` is mandatory on `POST /reels`; 1:1 `coupon_templates.reel_id UNIQUE` (3.3) |

---

## 10. Error Envelope Reference

All errors from these endpoints use the global envelope; `code` is `HTTP_<status>` and `message` is the text listed above:
```json
{
  "success": false,
  "error": { "code": "HTTP_409", "message": "The 24-hour window to extend this offer has closed." }
}
```
Validation failures (`422`) use `"code": "VALIDATION_ERROR"`, `"message": "Request validation failed."` and
`details: [{ "field": "rating", "message": "...", "type": "..." }]`.
