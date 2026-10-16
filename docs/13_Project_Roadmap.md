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
| **Phase 6** | Hardening, Anti-Cheating Loop & Full Stitch UI | Nagpur / Mumbai Pilot, Notifications Screen, Scratch Cards | 🟢 Complete (Full Stack) |
| **Phase 7** | Operations Desk, Admin Data Hub & Mobile Runbook | Store Onboarding, PIN Management, Mobile Architecture Docs | 🟢 Complete (Full Stack) |

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
- [x] Mobile (Expo / React Native): Stitch Screen 7 Glacier Minimal Auth & Onboarding with live neighborhood preview pills, +91 phone shell, social auth pills, and Staff PIN login.
- [x] Tests: OTP generation rate-limiting, token rotation tests (Pytest + HTTPX).

### Phase 2: Merchant Studio & Coupon Engine (Vertical Slice 2)
- [x] DB: `reels`, `coupon_templates` tables and sector validity rules (Food <= 5d, etc.).
- [x] Backend: Cloudinary signed upload generator for direct video & KYC uploads (`/media/sign-upload`).
- [x] Frontend: `MERCH-02` Dashboard, `MERCH-03` Video upload & Voiceover selector, `MERCH-04` Sector Coupon Builder.
- [x] Mobile (Expo / React Native): Merchant Creator Studio (`MerchantStudioScreen`) with 4-metric glass insights, sector validity constraints, and direct reel picker.
- [x] Tests: Sector validity constraints (Food max 5d, Fashion max 15d), Cloudinary signature generation verification.

### Phase 3: Super Admin Moderation Queue (Vertical Slice 3)
- [x] Backend: Admin moderation API endpoints (`/admin/moderation/*`).
- [x] Tests: Approved reels become visible in feed; rejected reels receive rejection notes.
- [x] Frontend: `ADMIN-01` Video review player with approve/reject reasons.

### Phase 4: Shopper Discovery Feed (Vertical Slice 4)
- [x] Backend: Proximity search with radius filters (2 km, 5 km, 10 km) and shopper wallet endpoints.
- [x] Tests: Distance calculation accuracy, coupon claim and wallet queries.
- [x] Frontend: `FEED-01` 9:16 vertical reel feed with auto-scroll, distance badges, and "Claim Coupon" button with confetti.
- [x] Mobile (React Native / Expo): Glacier Minimal 9:16 discovery feed (`FeedScreen`, Stitch Screen 8) with hardware video playback, spinning vinyl audio disc, frosted filter switcher, and floating voucher CTA.
- [x] Mobile Search & Explore (`ExploreScreen`, Stitch Screens 5 & 6) with "Happening Now" flash deal countdown, category pills, and trending tags.

### Phase 5: Anti-Fraud Redemption Loop (Vertical Slice 5)
- [x] DB: `user_coupons`, `redemptions_ledger` tables.
- [x] Backend: RFC 6238 TOTP engine (60s rotation), cashier verification endpoint with geofence check.
- [x] Tests: Replay rejection, expired QR failure, double-spend prevention.
- [x] Frontend: `WALLET-02` In-Store Dynamic QR with 60s countdown ring, `POS-01` Cashier Scanner Terminal.
- [x] Mobile (React Native / Expo): High-speed Cashier POS QR scanner (`ScannerScreen`) with animated laser reticle, 4-digit counter code keypad, and instant server verification.
- [x] Mobile In-Store Pass Wallet (`WalletScreen` & `CounterCodeModal`, Stitch Screen 4) with 60s dynamic TOTP QR code and 100% brightness boost.

### Phase 6: Hardening, Anti-Cheating Reward Loop & Full Stitch UI
- [x] Mobile Notifications & Activity (`NotificationsScreen`, Stitch Screen 1) with category filter pills ("All", "Deals & Passes", "Store Updates", "Neighborhood Radar"), "Expiring Soon" alerts, "New Spot Unlocked" cards, and 5-star experience ratings.
- [x] Anti-Cheating Interactive Digital Scratch Cards (`ScratchRewardModal.tsx` & `rewardsSlice.ts`, ADR-004) with metallic foil reveal, sound/haptic celebration, and instant Fyndo Coin credits.
- [x] Shopper Profile & Saved Passes (`ProfileScreen`, Stitch Screen 3) with real-time Fyndo Coins balance and privilege badges.
- [x] Single-City pilot live endpoints running on port 5000 with seed data for Nagpur & Mumbai merchants.
- [x] 100% TypeScript type safety (`tsc --noEmit` pass) and strict <300 line-of-code audit across all 75 mobile source files.

### Phase 7: Operations Desk, Admin Data Hub & Mobile Runbook
- [x] Backend Admin CRUD APIs: `AdminService` with platform overview stats (`/admin/stats`), merchant store creation & updates (`/admin/merchants`), cashier staff 6-digit PIN management (`/admin/merchants/:id/staff`), and direct reel/coupon publishing (`/admin/reels`).
- [x] Frontend Operations Desk (`AdminPage.tsx`): 4-tab control center with `AdminStatsOverview.tsx`, `AdminModerationDesk.tsx`, `AdminMerchantsDesk.tsx`, and `AdminReelsDesk.tsx`.
- [x] Comprehensive Mobile Documentation (`docs/15_Mobile_App_Architecture_And_Runbook.md` & `fyndo-mobile/README.md`): Architectural guide, Glacier Minimal design tokens, safe area formulas, network client configuration, and operator runbook.



