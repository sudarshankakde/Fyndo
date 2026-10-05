# 08 - Authentication & Authorization Specification

> **Platform**: Fyndo  
> **Security Standards**: OAuth 2.0 / JWT (RFC 7519), Redis-backed OTP validation, PBKDF2/Argon2id staff PIN hashing.

---

## 1. Role-Based Access Control (RBAC) Matrix

| Resource / Action | Shopper | Merchant Owner | Cashier / Staff | Super Admin |
|---|:---:|:---:|:---:|:---:|
| **Browse Proximity Feed** | ✅ | ✅ | ❌ | ✅ |
| **Claim Coupon** | ✅ | ❌ | ❌ | ❌ |
| **View Own Wallet & TOTP QR** | ✅ | ❌ | ❌ | ❌ |
| **Onboard Merchant & Upload KYC** | ❌ | ✅ | ❌ | ❌ |
| **Upload Reel & Configure Offer** | ❌ | ✅ | ❌ | ❌ |
| **Assign / Reset Staff PIN** | ❌ | ✅ | ❌ | ❌ |
| **Scan Dynamic QR (POS Terminal)**| ❌ | ✅ | ✅ | ❌ |
| **View Daily Redemption Stats** | ❌ | ✅ | ✅ (Today only) | ✅ |
| **Approve / Reject Video Reels** | ❌ | ❌ | ❌ | ✅ |
| **Verify Merchant KYC** | ❌ | ❌ | ❌ | ✅ |
| **Manage City Geo-Fences** | ❌ | ❌ | ❌ | ✅ |

---

## 2. Authentication Workflows

### 2.1 Shopper & Merchant OTP Authentication
1. **Request Phase**:
   - Client sends Indian mobile number (`+91XXXXXXXXXX`).
   - Rate limit verified in Redis: `rate:otp:<phone>` (Max 3 sends / 10 minutes).
   - Generates random 6-digit numeric OTP.
   - Stored in Redis: `otp:<phone>` with 120-second TTL.
   - Dispatched via SMS Gateway (Twilio / Gupshup) or WhatsApp Business API.
2. **Verification Phase**:
   - Client submits `{ phone, otp }`.
   - Redis hash validated. On success, OTP key is immediately deleted to prevent replay.
   - User looked up or upserted into `users` table.
   - JWT Access Token (15 min) and Refresh Token (30 days) issued.

### 2.2 Cashier / Staff POS Authentication
- **Design Objective**: High friction-free login at checkout counter with strict separation from business settings.
- **Quota**: Strictly 1 staff account per merchant.
- **Credentials**: Merchant phone number + 6-digit cashier PIN.
- **Token Claims**:
  ```json
  {
    "sub": "a93bc410-staff-uuid",
    "role": "ROLE_CASHIER",
    "merchant_id": "8f90-merchant-uuid",
    "permissions": ["redemptions:scan", "redemptions:read_today"]
  }
  ```

### 2.3 Super Admin Authentication
- MFA required: Admin password + Google Authenticator / Authy TOTP token.
- Admin sessions capped at 8 hours of inactivity before re-authentication.

---

## 3. Token Architecture & Refresh Rotation

### Access Token (JWT)
- **Algorithm**: `RS256` (Asymmetric Private/Public key pair) or `HS256` with strong 256-bit secret.
- **Expiration**: 15 minutes.
- **Payload**:
  ```json
  {
    "sub": "user-uuid",
    "role": "SHOPPER",
    "phone": "+919876543210",
    "iat": 1728130000,
    "exp": 1728130900
  }
  ```

### Refresh Token & Revocation
- Opaque random 64-character token stored in Redis: `refresh:<token_hash> -> user_id` with 30-day TTL.
- Calling `/auth/refresh` rotates the refresh token (old token invalidated, new pair generated).
- Logging out invalidates the refresh token immediately in Redis.
