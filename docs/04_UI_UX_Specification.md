# 04 - UI/UX Specification & Screen Inventory

> **Platform**: Fyndo | **Target Display**: Mobile-First Responsive PWA & Native WebView  
> **Aesthetic Principles**: Sleek dark mode, vibrant neon accents (#FF4B4B Coral Red, #00E676 Emerald Green), tactile micro-animations, glassmorphism overlays.

---

## 1. Screen Inventory

| Screen ID | Screen Name | Target Persona | Priority |
|---|---|---|---|
| `AUTH-01` | Language Selection & Phone Input | Shopper / Merchant | 🔴 P0 |
| `AUTH-02` | 6-Digit OTP Verification | Shopper / Merchant | 🔴 P0 |
| `FEED-01` | Full-Screen Proximity Reel Feed | Shopper | 🔴 P0 |
| `FEED-02` | Location & Distance Filter Sheet | Shopper | 🔴 P0 |
| `WALLET-01`| My Coupons & Wallet | Shopper | 🔴 P0 |
| `WALLET-02`| In-Store Dynamic TOTP QR Modal | Shopper | 🔴 P0 |
| `WALLET-03`| Post-Redemption Scratch & Reward Modal | Shopper | 🟠 P1 |
| `STORE-01` | Merchant Public Profile & Directions | Shopper | 🟠 P1 |
| `MERCH-01` | Merchant Business Onboarding & KYC | Merchant Owner | 🔴 P0 |
| `MERCH-02` | Merchant Studio & Performance Dashboard | Merchant Owner | 🔴 P0 |
| `MERCH-03` | Reel Camera / Upload & Voiceover Studio | Merchant Owner | 🔴 P0 |
| `MERCH-04` | Sector-Governed Coupon Builder | Merchant Owner | 🔴 P0 |
| `MERCH-05` | Staff PIN Allocation (Max 1 Staff) | Merchant Owner | 🟠 P1 |
| `POS-01`   | High-Speed Camera QR Scanner Terminal | Cashier / Owner | 🔴 P0 |
| `ADMIN-01` | Reel Video & KYC Moderation Queue | Super Admin | 🔴 P0 |

---

## 2. Detailed Screen Specifications

### `FEED-01`: Full-Screen Proximity Reel Feed
- **Purpose**: Primary discovery surface for hyper-local video deals.
- **Components**:
  - Full-screen 9:16 vertical video player with auto-play on scroll.
  - Top Glass Bar: Location indicator ("Sitabuldi, Nagpur • 2 km"), Language switcher pill (`EN|HI|MR`).
  - Bottom Overlay: Merchant name, sector badge, distance tag (e.g. `📍 850m away`), offer teaser banner.
  - Floating Action Button (FAB): "Claim Coupon" with pulsating glow effect.
  - Side Actions: Save to bookmarks, Share to WhatsApp, View Store Profile.
- **Interactions**:
  - Swipe up/down: Snaps to next/previous reel with seamless MP4 video preloading.
  - Tap screen: Toggle pause/play with centered fade animation.
  - Double tap: Like reel / heart micro-animation.
- **States**:
  - **Loading**: Translucent skeleton card with shimmering gradient.
  - **Empty**: "No reels within 2 km. Expand radius to 5 km or 10 km." with quick radius toggle.
  - **Error**: Retry card with "Unable to load nearby deals. Check GPS connection."
- **Responsive Behavior**:
  - Mobile: Immersive 100vh full-screen feed.
  - Desktop: Centered 9:16 aspect ratio smartphone container with blurred ambient background.

---

### `WALLET-02`: In-Store Dynamic TOTP QR Modal
- **Purpose**: Display tamper-proof, non-screenshottable redemption code to cashier.
- **Components**:
  - High-contrast central QR code container.
  - 60-Second Circular Progress Ring showing remaining validity with ticking seconds counter.
  - 4-Digit Emergency Offline Backup Code beneath QR.
  - Store Verification Card: Store Name, Address, and Offer details.
  - Safety Warning: "Do not screenshot. Refreshes every 60 seconds."
- **Interactions**:
  - Automatic screen brightness boost to 100% on modal open.
  - QR regenerates silently every 60 seconds via Speakeasy/crypto TOTP algorithm.
  - Polling / WebSocket listener waits for redemption confirmation event from cashier.
- **States**:
  - **Loading**: Generating fresh cryptographic token.
  - **Expired**: Code fades with red overlay and "Tap to refresh" button.
  - **Success**: Modal automatically morphs into `WALLET-03` Celebration Screen upon cashier scan.
- **Security Constraint**: Window blur / screenshot detection triggers anti-fraud watermark overlay.

---

### `POS-01`: High-Speed Camera QR Scanner Terminal
- **Purpose**: Fast checkout cashier tool for 1-second coupon redemption.
- **Components**:
  - Real-time video viewfinder with targeting reticle and torch/flash toggle.
  - Header: Merchant Store Name, Cashier Name, and Today's Verified Scan Count badge.
  - Bottom Drawer: Recent 5 scanned redemptions with timestamps.
  - Manual Entry Drawer: 4-digit offline backup PIN input keypad.
- **Interactions**:
  - Point camera at customer's dynamic QR code.
  - Instant audio beep & haptic feedback upon read.
  - Sub-second API verification against server.
- **States**:
  - **Success State (Green)**: Full-screen emerald overlay, audio chime, displays:
    `✅ REDEEMED: Flat ₹500 OFF (Customer: Rahul M.)`.
  - **Error State (Red)**: Full-screen red alert, buzzer sound, displays:
    `❌ INVALID / EXPIRED QR CODE (Screenshot detected or expired)`.
  - **Already Redeemed State (Yellow)**: `⚠️ COUPON ALREADY USED AT 14:15 PM`.

---

### `MERCH-03`: Reel Camera / Upload & Voiceover Studio
- **Purpose**: Allow local shop owners to easily shoot or upload short showcase reels.
- **Components**:
  - Viewfinder with 9:16 aspect ratio guides and 15s/60s duration indicator.
  - Audio Source Selector: "Original Mic Audio" or "Record Voiceover".
  - Audio Policy Notice: "Copyrighted music overlays are disabled to protect your business."
  - Trim Slider: Dual-handle video timeline trimmer.
  - "Attach Offer" Button: Opens `MERCH-04` modal.
- **States**:
  - **Recording**: Pulsing red record ring with progress ring filling up to 60s.
  - **Uploading**: Progress bar showing direct upload percentage to Cloudinary.
  - **Success**: Redirects to Dashboard with status "Pending Admin Moderation (est. 2 hours)".

---

### `MERCH-04`: Sector-Governed Coupon Builder
- **Purpose**: Configure discount terms strictly within platform sector limits.
- **Components**:
  - Sector locked display (e.g., "Food & Dining").
  - Discount Type Radio: Flat Discount (₹), Percentage Off (%), Buy 1 Get 1.
  - Minimum Purchase Field (₹).
  - Expiry Duration Slider:
    - Automatically bounded by sector (e.g., Max 5 days for Food; Max 15 days for Fashion; Max 60 days for Property).
    - Slider displays informative tooltip: "Food sector safety policy caps offers at 5 days."
  - Terms & Conditions Checklist: "Valid for dine-in only", "Not valid with other offers".
- **Validation**:
  - Disallows negative numbers or discounts exceeding 90%.
  - Disallows expiration exceeding sector ceiling.

---

### `ADMIN-01`: Reel Video & KYC Moderation Queue
- **Purpose**: Admin console to ensure high visual quality and 100% compliance.
- **Components**:
  - Dual Split View:
    - Left: HTML5 Video Player with playback controls, audio waveform, and duration inspector.
    - Right: Merchant KYC summary, Attached Coupon details, and Sector rules check.
  - Action Bar:
    - `Approve & Publish` (Emerald green button).
    - `Reject` (Coral red button with dropdown: "Copyrighted music detected", "Blurry video", "Misleading discount", "Inappropriate content").
- **States**:
  - Empty: "All caught up! Zero pending reels in the moderation queue."
  - Loading: Skeleton table with batch stats.
