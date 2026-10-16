# Fyndo Authentication API — Frontend Developer Guide

> **Target Audience**: Frontend Engineers, Mobile Developers, and QA Engineers  
> **Backend Base URL (Dev)**: `http://localhost:5000/api/v1`  
> **Interactive Swagger UI**: [`http://localhost:5000/docs`](http://localhost:5000/docs)  
> **OpenAPI JSON Spec**: `http://localhost:5000/api/v1/openapi.json`  
> **Interactive Redoc**: [`http://localhost:5000/redoc`](http://localhost:5000/redoc)

---

## 1. Global Request & Response Format

All API endpoints follow a unified response envelope.

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
    "code": "HTTP_400",
    "message": "The 6-digit OTP entered is incorrect or expired."
  }
}
```

### Standard Headers
| Header | Value | Requirement |
|---|---|---|
| `Content-Type` | `application/json` | All `POST` / `PATCH` requests |
| `Authorization` | `Bearer <JWT_ACCESS_TOKEN>` | Required on authenticated routes (`/auth/me`, `/auth/profile`, etc.) |

---

## 2. Pre-Configured Dev Credentials & Test Data

In `development` mode, you don't need real SMS gateways. The backend returns `test_otp` in the send response, and you can also use these fixed test accounts:

| Role | Mobile Number / Identifier | Password / PIN | Description |
|---|---|---|---|
| **Shopper** | `+919876543210` | Dev OTP from send response | Regular shopper discovery & coupon claims |
| **Merchant Owner** | `+919876543210` | Dev OTP from send response | Store owner managing reels and staff |
| **Counter Staff (POS)** | `+919876543210` (Store phone) | PIN: `123456` | Dedicated counter scanner terminal |
| **Super Admin** | `+919999900000` or `sudarshanakakde1111@gmail.com` | `Qweasdzx@1#` | Video moderation desk & KYC approval |

---

## 3. Endpoints Quick Reference

| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `POST` | `/auth/otp/send` | Public | Send 6-digit OTP via SMS or WhatsApp |
| `POST` | `/auth/otp/verify` | Public | Verify OTP, issue Access + Refresh JWT tokens |
| `POST` | `/auth/staff-login` | Public | 6-digit PIN login for cashier counter scanners |
| `POST` | `/auth/admin-login` | Public | Password login for Super Admin portal |
| `POST` | `/auth/refresh` | Public | Rotate 30-day refresh token & issue fresh access token |
| `POST` | `/auth/logout` | Optional Bearer | Invalidate active refresh session in Redis |
| `GET` | `/auth/me` | Bearer Token | Fetch authenticated profile (Shopper, Merchant, Cashier, Admin) |
| `PATCH` | `/auth/profile` | Bearer Token | Update user's name, email, or language |
| `POST` | `/auth/dev-token` | Dev Mode Only | Instant token generator for rapid UI prototyping |

---

## 4. Endpoint Specifications

### 4.1 Send Mobile OTP
- **Endpoint**: `POST /api/v1/auth/otp/send`
- **Rate Limit**: Max 3 requests per 10 minutes per mobile number.
- **Request Body**:
```json
{
  "phone": "+919876543210",
  "channel": "SMS" 
}
```
*(Channel can be `"SMS"` or `"WHATSAPP"`)*

- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "phone": "+919876543210",
    "expires_in_seconds": 120,
    "test_otp": "482910"
  },
  "message": "OTP sent successfully (Dev Mock Mode)"
}
```
> **Note**: `test_otp` is provided in dev mode so you can auto-fill or display it in your test UI.

---

### 4.2 Verify Mobile OTP (Shopper / Store Owner Login)
- **Endpoint**: `POST /api/v1/auth/otp/verify`
- **Request Body**:
```json
{
  "phone": "+919876543210",
  "otp": "482910",
  "preferred_language": "hi"
}
```
*(Languages: `"en"` | `"hi"` | `"mr"`)*

- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "user": {
      "id": "c1f7a360-1e5b-4682-a8c6-189679f2ea3a",
      "phone": "+919876543210",
      "full_name": "Haldiram's Sitabuldi",
      "email": "sitabuldi@haldirams.com",
      "role": "MERCHANT",
      "preferred_language": "hi",
      "merchant_id": "8f90-merchant-uuid",
      "business_name": "Haldiram's Sitabuldi",
      "kyc_status": "APPROVED"
    }
  },
  "message": "Authentication successful"
}
```

---

### 4.3 Counter Staff PIN Login (POS Terminal)
- **Endpoint**: `POST /api/v1/auth/staff-login`
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
    "staff_name": "Ramesh (Counter 1)",
    "merchant_id": "8f90-merchant-uuid",
    "business_name": "Haldiram's Sitabuldi"
  },
  "message": "Staff terminal authenticated"
}
```

---

### 4.4 Super Admin Login
- **Endpoint**: `POST /api/v1/auth/admin-login`
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

---

### 4.5 Token Refresh (Silent Rotation)
- **Endpoint**: `POST /api/v1/auth/refresh`
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
> **Security Note**: This endpoint rotates refresh tokens. Once used, the old refresh token is immediately invalidated in Redis. Always update your local storage with the new `refresh_token`.

---

### 4.6 User Logout & Revocation
- **Endpoint**: `POST /api/v1/auth/logout`
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

---

### 4.7 Get Current Authenticated Profile
- **Endpoint**: `GET /api/v1/auth/me`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "id": "c1f7a360-1e5b-4682-a8c6-189679f2ea3a",
    "phone": "+919876543210",
    "full_name": "Haldiram's Sitabuldi",
    "email": "sitabuldi@haldirams.com",
    "role": "MERCHANT",
    "preferred_language": "mr",
    "merchant_id": "8f90-merchant-uuid",
    "business_name": "Haldiram's Sitabuldi",
    "kyc_status": "APPROVED"
  }
}
```

---

### 4.8 Update User Profile
- **Endpoint**: `PATCH /api/v1/auth/profile`
- **Headers**: `Authorization: Bearer <access_token>`
- **Request Body**:
```json
{
  "full_name": "Rohan Deshmukh",
  "email": "rohan@example.com",
  "preferred_language": "mr"
}
```

- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "id": "c1f7a360-1e5b-4682-a8c6-189679f2ea3a",
    "phone": "+919876543210",
    "full_name": "Rohan Deshmukh",
    "email": "rohan@example.com",
    "role": "SHOPPER",
    "preferred_language": "mr"
  },
  "message": "Profile updated successfully"
}
```

---

### 4.9 Fast-Lane Development Token Generator
- **Endpoint**: `POST /api/v1/auth/dev-token`
- **Description**: Enabled only in `development`. Instantly mints a valid, signed JWT access and refresh token pair for any role without sending SMS.
- **Request Body**:
```json
{
  "role": "MERCHANT" 
}
```
*(Allowed roles: `"SHOPPER"`, `"MERCHANT"`, `"ROLE_CASHIER"`, `"SUPER_ADMIN"`)*

- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "Bearer",
    "role": "MERCHANT",
    "user": {
      "id": "...",
      "phone": "+919876543210",
      "role": "MERCHANT"
    }
  },
  "message": "Development token generated for MERCHANT"
}
```

---

## 5. Ready-To-Use Frontend Service (`authService.ts`)

In `frontend/src/services/authService.ts`, all methods are already wired:

```typescript
import { authService } from '@/services/authService'

// 1. Send OTP
const { test_otp } = await authService.sendOtp('+919876543210', 'SMS')

// 2. Verify OTP
const session = await authService.verifyOtp('+919876543210', '482910', 'hi')
console.log(session.accessToken, session.user)

// 3. Staff Counter Login
const staffSession = await authService.staffLogin('+919876543210', '123456')

// 4. Admin Login
const adminSession = await authService.adminLogin({
  identifier: 'sudarshanakakde1111@gmail.com',
  password: 'Qweasdzx@1#'
})

// 5. Refresh Tokens
const newTokens = await authService.refreshToken(session.refreshToken!)

// 6. Logout
await authService.logout(session.refreshToken)

// 7. Get Me
const myProfile = await authService.getMe()

// 8. Instant Dev Token
const devSession = await authService.getDevToken('MERCHANT')
```

---

## 6. Axios Silent Token Refresh Pattern

To automatically renew tokens when an access token expires (HTTP 401), use this standard Axios response interceptor:

```typescript
import axios from 'axios'

let isRefreshing = false
let failedQueue: Array<{ resolve: (token: string) => void; reject: (err: any) => void }> = []

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token!)
    }
  })
  failedQueue = []
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem('fyndo_refresh_token')
      if (!refreshToken) {
        // Redirect to login
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            return apiClient(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const res = await axios.post('http://localhost:5000/api/v1/auth/refresh', {
          refresh_token: refreshToken,
        })
        const { access_token, refresh_token: newRefreshToken } = res.data.data

        localStorage.setItem('fyndo_token', access_token)
        localStorage.setItem('fyndo_refresh_token', newRefreshToken)

        apiClient.defaults.headers.common.Authorization = `Bearer ${access_token}`
        processQueue(null, access_token)

        originalRequest.headers.Authorization = `Bearer ${access_token}`
        return apiClient(originalRequest)
      } catch (refreshErr) {
        processQueue(refreshErr, null)
        localStorage.clear()
        window.location.href = '/'
        return Promise.reject(refreshErr)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)
```

---

## 7. Error Handling Dictionary

| HTTP Code | Error Message | Solution / Frontend Handling |
|---|---|---|
| `400 Bad Request` | `The 6-digit OTP entered is incorrect or expired.` | Prompt user to re-enter code or click "Resend Code" |
| `401 Unauthorized` | `Authentication credentials were not provided.` | Route to Login screen |
| `401 Unauthorized` | `Invalid 6-digit staff PIN.` | Display inline error on PIN input field |
| `401 Unauthorized` | `Invalid administrator credentials.` | Prompt admin to check credentials |
| `401 Unauthorized` | `Session expired or token revoked.` | Clear local storage & prompt user to sign in |
| `403 Forbidden` | `Account deactivated or suspended.` | Show account status alert |
| `404 Not Found` | `Store account not found for this mobile number.` | Prompt counter cashier to confirm store mobile number |
| `429 Too Many Requests` | `Too many OTP requests. Please wait 10 minutes.` | Show countdown timer and disable Resend button |
