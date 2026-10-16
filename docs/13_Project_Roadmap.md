# 13 - Project Roadmap & Vertical Slices

> **Platform**: Fyndo  
> **Approach**: Strict Vertical Slice delivery (DB -> Backend API -> Tests -> Frontend UI -> E2E Validation)

---

## 1. Milestone Overview

| Phase | Milestone | Scope | Status |
|---|---|---|---|
| Phase | Milestone | Scope | Status |
|---|---|---|---|
| **Phase 0** | Foundation & Infrastructure | Docker Compose, PostGIS DB, Redis, Repo Scaffolding | 🟢 Complete (Full Stack) |
| **Phase 1** | Auth, Profiles & Staff Setup | Shopper OTP, Merchant Onboarding, Staff PIN | 🟢 Complete (Full Stack) |
| **Phase 2** | Reel Studio & Coupon Engine | Direct MP4 Upload, Video Delivery, Sector Coupon Builder | 🟢 Complete (Full Stack) |
| **Phase 3** | Admin Moderation Pipeline | Video Review Desk, Audio Policy, KYC Verification | 🟢 Complete (Full Stack) |
| **Phase 4** | Discovery Feed & Map Engine | PostGIS 2/5/10km Geo-feed, 9:16 Video Player, Wallet Claim | 🟢 Complete (Full Stack) |
| **Phase 5** | Anti-Fraud In-Store Redemption | 60s Dynamic TOTP QR, Cashier Scanner POS, Scratch Cards | 🟢 Complete (Full Stack) |
| **Phase 6** | Beta Hardening & Single-City Rollout | Nagpur / Mumbai Pilot, Load Testing, Bug Bashes | 🔄 In Progress |

---

## 2. Detailed Vertical Slices

### Phase 0: Foundation & Infrastructure
- [x] Master Requirements & Architecture Documentation (`docs/01` - `docs/14`).
- [x] Initialize `docker-compose.yml` with PostgreSQL 16 (PostGIS) and Redis 7.
- [x] Setup `backend/` Python 3.13 / FastAPI project with Uvicorn, Pytest, and Async DB/Redis fallback.
- [x] Setup `frontend/` React 18+ / TypeScript / Vite scaffold with Tailwind CSS (v3.4), shadcn/ui, TanStack Query v5, and Redux Toolkit.

### Phase 1: Authentication & User Management (Vertical Slice 1)
- [x] DB: `users`, `merchants`, `merchant_staff` models & tables.
- [x] Backend: Redis OTP service, JWT issue/refresh endpoints, Staff PIN login (FastAPI).
- [x] Frontend: `AUTH-01` (Language & Phone), `AUTH-02` (OTP Input with dev auto-fill), Staff Terminal Login.
- [x] Tests: OTP generation rate-limiting, token rotation tests (Pytest + HTTPX).

### Phase 2: Merchant Studio & Coupon Engine (Vertical Slice 2)
- [x] DB: `reels`, `coupon_templates` tables and sector validity rules (Food <= 5d, etc.).
- [x] Backend: Cloudinary signed upload generator for direct video & KYC uploads (`/media/sign-upload`).
- [x] Frontend: `MERCH-02` Dashboard, `MERCH-03` Video upload & Voiceover selector, `MERCH-04` Sector Coupon Builder.
- [x] Tests: Sector validity constraints (Food max 5d, Fashion max 15d), Cloudinary signature generation verification.

### Phase 3: Super Admin Moderation Queue (Vertical Slice 3)
- [x] Backend: Admin moderation API endpoints (`/admin/moderation/*`).
- [x] Tests: Approved reels become visible in feed; rejected reels receive rejection notes.
- [x] Frontend: `ADMIN-01` Video review player with approve/reject reasons.

### Phase 4: Shopper Discovery Feed (Vertical Slice 4)
- [x] Backend: Proximity search with radius filters (2 km, 5 km, 10 km) and shopper wallet endpoints.
- [x] Tests: Distance calculation accuracy, coupon claim and wallet queries.
- [x] Frontend: `FEED-01` 9:16 vertical reel feed with auto-scroll, distance badges, and "Claim Coupon" button with confetti.
- [x] Mobile (React Native / Expo): Glacier Minimal 9:16 discovery feed with hardware video playback, spinning vinyl audio disc, frosted filter switcher, and floating voucher CTA.

### Phase 5: Anti-Fraud Redemption Loop (Vertical Slice 5)
- [x] DB: `user_coupons`, `redemptions_ledger` tables.
- [x] Backend: RFC 6238 TOTP engine (60s rotation), cashier verification endpoint with geofence check.
- [x] Tests: Replay rejection, expired QR failure, double-spend prevention.
- [x] Frontend: `WALLET-02` In-Store Dynamic QR with 60s countdown ring, `POS-01` Cashier Scanner Terminal.
- [x] Mobile (React Native / Expo): High-speed Cashier POS QR scanner with animated laser reticle, 4-digit counter code keypad, instant server verification, and Merchant Creator Studio with sector validity builder.

