# 15 - Mobile Application Architecture & Operator Runbook

> **Application**: Fyndo Mobile App  
> **Repository**: `e:\MyProjects\fyndo-mobile`  
> **Framework**: React Native 0.88 + Expo SDK 58 (TypeScript 5.8)  
> **State Management**: Redux Toolkit (Client state) + TanStack React Query v5 (Server cache)  
> **Design Theme**: Glacier Minimal / Obsidian Midnight (Stitch Project `6900660431147625086`)

---

## 1. Executive Summary & Purpose

Fyndo Mobile is the primary consumer and merchant staff interface for the Fyndo hyper-local video and coupon redemption ecosystem. It delivers three dedicated personas in a unified codebase:
1. **Shoppers**: Discover 9:16 vertical video reels of verified local merchants, explore flash discounts within 2/5/10 km radius, claim vouchers into their personal digital wallet, unveil dynamic anti-tamper QR passes at store checkout, and reveal instant scratch rewards.
2. **Cashier / POS Staff**: High-speed QR scanner terminal with animated laser reticle, manual 4-digit counter code fallback, and instant cryptographic server verification to redeem vouchers and prevent coupon reuse.
3. **Merchant Creators**: Mobile Studio dashboard with store performance insights, video reel upload with original audio policy enforcement, and sector-based coupon builder.

---

## 2. Technology Stack & Libraries

| Capability | Library / Engine | Configuration & Rationale |
|---|---|---|
| **Core Runtime** | React Native `0.88.0` / Expo SDK `58.0.0` | Modern React 19 architecture with New Architecture support |
| **Language** | TypeScript `5.8.3` | Strict type checking (`noEmit` validation, zero `any` tolerance) |
| **Client State** | Redux Toolkit `^2.5.0` | Global user session (`authSlice`), GPS radius (`locationSlice`), loyalty coins (`rewardsSlice`) |
| **Server State** | TanStack React Query `v5` | Automatic background caching, query invalidation, and optimistic mutations |
| **Video Engine** | `expo-video` | Hardware-accelerated native vertical 9:16 reel playback |
| **Camera & Barcode** | `expo-camera` (`CameraView`) | Real-time QR / barcode scanning with torch and animated scan line |
| **Security & Privacy** | `expo-screen-capture` & `expo-brightness` | Blocks screenshots of active QR codes; boosts screen brightness to 100% |
| **Icons & Aesthetics** | `lucide-react-native` | Cohesive line icons styled to Glacier Minimal palette |
| **Safe Areas** | `react-native-safe-area-context` | Dynamic edge insets for notches, punch-holes, and gesture navigation bars |
| **Internationalization**| `i18next` + `react-i18next` | English (`en`), Hindi (`hi`), Marathi (`mr`) |

---

## 3. Glacier Minimal Design System

Inspired by Stitch Project `6900660431147625086`:

```text
┌────────────────────────────────────────────────────────┐
│  Obsidian Void Background:       #0A0E1A               │
│  Surface Deep Container:         #0F1524 (Glass 75%)   │
│  Surface Elevated Container:     #141C2E (Glass 90%)   │
│  Surface Subtle Variant:         #1A2438               │
│  Glacier Cyan Primary:           #7DD3FC               │
│  Verified Emerald Status:        #00E599               │
│  Alert Coral / Error:            #FF6B6B               │
│  VIP Lavender Accent:            #C8A0F0               │
│  Text Primary High-Contrast:     #E0E8F0               │
│  Text Secondary Subtle:          #A0B4C4               │
└────────────────────────────────────────────────────────┘
```

---

## 4. Screen Architecture & Stitch Asset Mapping

| Stitch Screen Asset | Mobile Implementation File | Subcomponents | Key Features |
|---|---|---|---|
| **Screen 1**: Notifications & Activity | `src/screens/shopper/NotificationsScreen.tsx` | `NotificationItem.tsx`<br/>`NotificationFilterBar.tsx`<br/>`NotificationRatingCard.tsx` | Category filters (*All, Deals, Updates, Radar*), expiring pass alerts, 5-star rating widget, scratch card CTA. |
| **Screen 2**: Storefront | `src/screens/shopper/StorefrontScreen.tsx` | `StorefrontHeaderCard.tsx`<br/>`StorefrontPassCard.tsx` | Store banner, verified avatar ring, open hours pulse, address, direct pass claiming. |
| **Screen 3**: Profile & Saved Passes | `src/screens/shopper/ProfileScreen.tsx` | `ProfileHeaderBlock.tsx`<br/>`ProfileStatsGrid.tsx`<br/>`ProfileSettingsPanel.tsx` | Frosted avatar aura, verified badge, real-time Fyndo Coins balance, pass history, language switcher. |
| **Screen 4**: Voucher Pass | `src/screens/shopper/WalletScreen.tsx` | `CounterCodeModal.tsx`<br/>`CouponCard.tsx`<br/>`WalletPassHeader.tsx`<br/>`WalletPassQrPad.tsx`<br/>`WalletTicketNotch.tsx`<br/>`WalletPrivilegeStrip.tsx` | Apple Wallet-style ticket notches, dashed tear line, 60s dynamic TOTP QR code, backup 4-digit code, screen capture prevention. |
| **Screen 5 & 6**: Search & Flash Offers | `src/screens/shopper/ExploreScreen.tsx` | `ExploreHeroDeal.tsx`<br/>`TrendingTagsList.tsx`<br/>`CuratedStoreCard.tsx` | Frosted search bar, flash deal countdown timer, trending tags, curated 4.9-rated merchant cards. |
| **Screen 7**: Auth & Onboarding | `src/screens/auth/LoginScreen.tsx` | `AuthHeader.tsx`<br/>`NeighborhoodSpotCarousel.tsx`<br/>`PhoneOtpForm.tsx`<br/>`StaffPinForm.tsx` | Glowing brand icon mark with pulsing indicator, live neighborhood spot pills, Indian flag `+91` input, staff PIN switcher. |
| **Screen 8**: Vertical Reels Stream | `src/screens/shopper/FeedScreen.tsx` | `FeedHeader.tsx`<br/>`ReelItem.tsx`<br/>`ReelOverlay.tsx`<br/>`ReelMerchantInfo.tsx`<br/>`ReelVoucherPill.tsx`<br/>`RightActionRail.tsx` | 1:1 vertical snapping feed, hardware-accelerated video playback, spinning vinyl audio disc, frosted For You vs Nearby filter, floating voucher pill CTA. |
| **POS Terminal**: Cashier Scanner | `src/screens/cashier/ScannerScreen.tsx` | `ScannerCameraView.tsx`<br/>`ManualCodeInputModal.tsx`<br/>`ScanResultModal.tsx`<br/>`RecentScansDrawer.tsx` | Real-time barcode camera with animated laser line, 4-digit keypad modal, instant verification result modal, shift history drawer. |
| **Merchant Studio**: Creator Hub | `src/screens/merchant/MerchantStudioScreen.tsx` | `MerchantInsightsGrid.tsx`<br/>`SectorCouponBuilder.tsx`<br/>`CreateReelModal.tsx` | 4-metric glass insights, video picker, original audio reminder, sector validity ceilings (Food: max 5d, Fashion: max 15d). |

---

## 5. Architectural Principles

1. **Strict File Line Limit (<300 lines)**:
   - Every source file in `src/` must remain strictly under 300 lines (hard limit: 400 for exceptional edge cases).
   - Proactive modular decomposition into dedicated presentational subcomponents under `src/components/<feature>/`.
2. **Separation of Concerns**:
   - Presentation components contain zero direct HTTP network fetching.
   - All network calls are encapsulated in `src/services/` and consumed via TanStack Query hooks in `src/hooks/`.
3. **Zero Jargon Rule**:
   - Customer-facing UI text uses warm, human-centric Indian market phrasing (e.g. *"Pass"*, *"Verified Store"*, *"Discount at Counter"*, *"Secret Club Drop"*).
   - Engineering implementation details (*TOTP, API, RBAC, Geofence algorithm, JSON, HTTP 403/500, Database, Beta*) are strictly prohibited in user-facing views.
4. **Dynamic Safe Area Margins & Zero-Drift Geometry**:
   - Dynamic top header offset: `top: Math.max(insets.top, 16) + 4`.
   - Floating bottom tab bar height: `tabHeight = 58 + Math.max(insets.bottom, 8)`.
   - Reel feed exact container measurement (`onLayout`): `FeedScreen` dynamically measures container `width` and `height`, passing exact pixel bounds (`feedHeight`) to each `ReelItem`.
   - Pure Native Paging (`pagingEnabled={true}`): Eliminates `snapToInterval` conflicts on Android, guaranteeing zero layout shifts, zero cumulative drift, and zero multi-reel peeking.
   - Smooth Vignette Gradients (`expo-linear-gradient`): Uses hardware-accelerated linear gradients (`rgba(10, 14, 26, 0.75)` to transparent at top, transparent to `rgba(10, 14, 26, 0.98)` at bottom) replacing hard rectangular boxes.
   - Dynamic Overlay Heights: `ReelOverlay` sits at `paddingBottom: tabHeight + 10` and `RightActionRail` sits at `bottom: tabHeight + 16` so all interactive elements float crisply above the bottom navigation bar.
   - Constrained Pill Dimensions: Category filter bars (`NotificationFilterBar`, `ExploreScreen`) use fixed-height containers (`height: 46`, `height: 34`) and `alignItems: 'center'` to guarantee pills never stretch vertically into cards on Android flexbox.
   - Scroll views include `paddingBottom: 110` so content scrolls clear of floating system navigation bars.

---

## 6. Anti-Fraud & In-Store Redemption Engine (ADR-004)

1. **Dynamic RFC 6238 TOTP Tokens**:
   - Every claimed coupon generates a unique cryptographic base32 secret.
   - When the customer taps "View QR Pass", `/api/v1/coupons/:id/dynamic-qr` delivers a base64 payload containing `{ claim_id, totp, uid, ts }` refreshed every 60 seconds.
   - Static screenshots forwarded over WhatsApp or social media expire within 60 seconds.
2. **Geofenced Verification**:
   - Cashier scanner checks store GPS coordinates; cashier location must be within 500 meters of the registered shop perimeter.
3. **Double-Spend Rejection**:
   - Once verified, the coupon transitions to `REDEEMED` status and commits an immutable record to `redemptions_ledger`.
   - Re-scanning immediately returns `409 Conflict` (*"Voucher already redeemed at 08:23"*).
4. **Shopper Scratch Card Reward Hook**:
   - Upon verified redemption, customer unlocks a digital scratch card (`ScratchRewardModal.tsx`) awarding `+50 Fyndo Coins` to incentivize shoppers to insist on counter scans.

---

## 7. Developer Quickstart & Runbook

### Prerequisites
- Node.js `v20+` or `v22+`
- Expo CLI (`npx expo`)
- Python 3.13 virtual environment with FastAPI running backend on port 5000

### Installation
```bash
cd e:\MyProjects\fyndo-mobile
npm install
```

### Type Checking & Code Line Audit
```bash
# Verify 100% TypeScript type safety
npx tsc -p tsconfig.json --noEmit

# Audit that all source files remain strictly under 300 lines
node C:\Users\sudar\.gemini\antigravity-ide\brain\5dd58dcb-5070-41e8-a422-8fd4f088b75e\scratch\audit_lines.js
```

### Running Locally on Physical Mobile Device or Emulator
```bash
# Start Metro bundler with LAN IP auto-detection
npx expo start
```
Scan the generated QR code with **Expo Go** on Android or iOS.

### Connecting to Backend from Physical Devices
In `src/services/apiClient.ts`, configure your local Wi-Fi IP address:
```typescript
const LOCAL_WIFI_IP = '192.168.1.2'; // Your computer's Wi-Fi IP
const BASE_URL = `http://${LOCAL_WIFI_IP}:5000/api/v1`;
```
Start Uvicorn listening on all network interfaces (`0.0.0.0`):
```bash
cd e:\MyProjects\Fyndo\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 5000
```

### Test Credentials

| Role | Mobile Number / Identifier | PIN / Code | Associated Entity |
|---|---|---|---|
| **Shopper** | Any Indian phone (e.g. `9876543210`) | Auto-logged in console (`123456` fallback) | Personal Shopper Wallet |
| **Cashier (Haldiram's)** | Store: `+919822011111` or Staff: `+919822099991` | `123456` | Haldiram's Sweets & Namkeen (Sitabuldi) |
| **Cashier (Mahal Saree)** | Store: `+919822022222` or Staff: `+919822099992` | `123456` | Mahal Saree & Ethnic Hub |
| **Cashier (Metro Shoes)**| Store: `+919822033333` or Staff: `+919822099993` | `123456` | Metro Footwear & Sneaker Lounge |
| **Super Admin** | `+919999900000` / `sudarshanakakde1111@gmail.com` | Master password configured in `.env` | Operations Desk (`/admin`) |
