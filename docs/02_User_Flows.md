# 02 - User Flows & Workflows

## 1. Shopper Journey

### 1.1 Discovery & Coupon Claim
```
[App Launch]
    ↓
[Language Selection: EN / HI / MR]
    ↓
[Location Permission Granted (Nagpur/Mumbai)]
    ↓
[Hyper-Local Video Feed (2km / 5km / 10km Filter)]
    ↓
[Watch Reel (15-60s Vertical Video)]
    ↓
[Tap "Claim Coupon" Button]
    ↓
[Is User Logged In?]
  ├── NO  ──> [Mobile Number -> SMS/WhatsApp OTP -> Quick Profile]
  └── YES ──> [Save to Shopper Wallet]
                  ↓
              [Display Expiration Countdown Clock]
```

### 1.2 In-Store Redemption Loop (Anti-Fraud)
```
[Shopper Visits Physical Shop]
    ↓
[Opens Fyndo Wallet -> Selects Active Coupon]
    ↓
[Taps "Redeem at Counter"]
    ↓
[Dynamic QR Code Generated with 60s TOTP Token + 4-digit Backup Code]
    ↓
[Cashier/Owner Scans QR using Fyndo Merchant App]
    ↓
[Cloud Validation: Valid, Not Expired, Within Geofence?]
  ├── NO  ──> [Red Alert on Merchant App: Invalid/Already Used]
  └── YES ──> [Green Alert on Merchant & Shopper Screen]
                  ↓
              [Merchant Grants Discount on Bill]
                  ↓
              [Shopper Receives Fyndo Reward Coins / Digital Scratch Card]
```

---

## 2. Merchant Journey

### 2.1 Onboarding & Verification
```
[Download Fyndo Business]
    ↓
[Enter Mobile Phone -> Verify OTP]
    ↓
[Business Profile Setup]
  - Shop Name & Category (Food, Clothes, Shoes, Electronics, Property)
  - Exact Location (GPS Pin + Address)
  - Operating Hours
  - KYC Document Upload (GSTIN certificate or Gumasta to Cloudinary)
    ↓
[Status: PENDING_VERIFICATION]
    ↓
[Admin Reviews & Approves KYC]
    ↓
[Merchant Account Activated]
```

### 2.2 Reel Studio & Coupon Publishing
```
[Tap "Create Reel"]
    ↓
[Option: Record In-App (15-60s) OR Select Pre-Edited Video from Gallery]
    ↓
[Audio Source: Raw Camera Audio OR Record Voiceover (No Copyright Music)]
    ↓
[Trim Video & Preview 9:16 Aspect Ratio]
    ↓
[Attach Coupon Engine]
  - Select Discount Type (% Off, Flat ₹ Off, BOGO)
  - Min Purchase Requirement (optional)
  - Validity Duration (Enforced by Sector: Food 2-5d, Fashion/Shoes/Electronics ≤15d, Property ≤60d)
    ↓
[Direct Signed Upload to Cloudinary (Auto-generates Poster WebP)]
    ↓
[Status: PENDING_ADMIN_MODERATION (Direct review for Beta)]
    ↓
[Super Admin Approves Reel]
    ↓
[Reel Live in Local User Feeds (Sorted by Distance)]
```

### 2.3 Staff Setup & Management
```
[Merchant Owner Opens Settings -> Staff Management]
    ↓
[Max Allocation: 1 Manager / Accountant Role]
    ↓
[Enter Staff Name, Mobile, and Assign 6-digit Scanner PIN]
    ↓
[Staff Logs into App with Shop Mobile + Scanner PIN]
    ↓
[Staff Access Restricted: QR Scanner & Daily Redemption Summary ONLY]
```

---

## 3. Super Admin Journey

### 3.1 Reel Moderation Pipeline
```
[Admin Logs In (MFA)]
    ↓
[Moderation Queue: Sorted by Submission Time]
    ↓
[Inspect Reel Preview]
  - Video content & visual quality
  - Audio check (strictly raw audio/voiceover, no illicit tracks)
  - Associated coupon text, terms, and expiry appropriateness
    ↓
[Decision]
  ├── APPROVE ──> [Reel Status: LIVE, Push Notification to Merchant, Distributed to Feed]
  └── REJECT  ──> [Select Reason: Inappropriate Audio, Misleading Offer, Low Video Quality]
                      ↓
                  [Notification with Feedback Sent to Merchant Studio]
```

---

## 4. Alternative & Error Paths

| Scenario | System Reaction | User Experience |
|---|---|---|
| **Expired Coupon** | Validation API returns `HTTP 410 Gone` | Merchant app beeps error; Shopper wallet tags coupon as "Expired". |
| **Screenshot Reuse** | Dynamic TOTP token expires after 60s | Scanned token rejected as invalid; merchant alerted to ask customer to refresh QR. |
| **No Internet in Shop**| Fallback 4-digit cryptographically hashed daily offline PIN | Staff enters offline code; queue syncs upon reconnect. |
| **Customer denies GPS**| App prompts: "Location required to find nearby deals" | Shows city-center default feed with a persistent banner requesting location. |
