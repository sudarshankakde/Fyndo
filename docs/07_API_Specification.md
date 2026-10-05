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
  "identifier": "+919999900000",
  "password": "AdminFyndo@2026",
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
      "email": "admin@fyndo.in",
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
- **Auth**: Required (`ROLE_MERCHANT`)
- **Request Body**:
```json
{
  "title": "Exclusive Festive Saree Clearance",
  "cloudinary_public_id": "fyndo/reels/e42790bd",
  "video_url": "https://res.cloudinary.com/fyndo-cloud/video/upload/q_auto,f_auto/v1/fyndo/reels/e42790bd.mp4",
  "thumbnail_url": "https://res.cloudinary.com/fyndo-cloud/video/upload/so_0,w_720,ar_9:16,c_fill/v1/fyndo/reels/e42790bd.webp",
  "duration_seconds": 45,
  "audio_type": "VOICEOVER",
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
- **Response `201 Created`**:
```json
{
  "success": true,
  "data": {
    "reel_id": "e42790bd-...",
    "status": "PENDING_MODERATION",
    "message": "Reel submitted successfully and queued for admin moderation."
  }
}
```

---

## 4. Coupon Wallet & Redemption Endpoints

### 4.1 Claim Reel Coupon
- **Endpoint**: `POST /coupons/:coupon_template_id/claim`
- **Auth**: Required (`ROLE_SHOPPER`)
- **Response `201 Created`**:
```json
{
  "success": true,
  "data": {
    "user_coupon_id": "8120fa49-...",
    "status": "CLAIMED",
    "claimed_at": "2026-10-05T14:30:00Z",
    "expires_at": "2026-10-08T14:30:00Z"
  }
}
```

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

### 4.3 Cashier Redemption Verification (POS Scan)
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
