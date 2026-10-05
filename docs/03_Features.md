# 03 - Feature Specifications

> **System**: Fyndo (Hyper-Local Video Discovery & In-Store Digital Coupon Platform)  
> **Target Beta**: Nagpur & Mumbai, India | **Languages**: English, Hindi, Marathi

---

## 1. Authentication & Onboarding Features

### FEAT-AUTH-01: Shopper Mobile OTP Authentication
- **Actor**: Shopper (Consumer)
- **Preconditions**: Device has active cellular or internet connection.
- **Input**: 10-digit Indian Mobile Number (`+91`), preferred language (`EN`, `HI`, `MR`), location permission.
- **Process**:
  1. User enters mobile number on the login/claim screen.
  2. System verifies rate limit (max 3 requests per 10 minutes per IP/number) and dispatches 6-digit OTP via SMS/WhatsApp.
  3. User enters 6-digit OTP within 120 seconds.
  4. Backend verifies hash against Redis cache.
  5. System generates JWT access token (15m validity) and refresh token (30d validity).
- **Success Criteria**: User session initialized; profile created or loaded; language preference stored.
- **Failure Modes**:
  - Invalid OTP: "Incorrect OTP. 2 attempts remaining."
  - Expired OTP: "OTP expired. Tap 'Resend'."
  - Rate limit tripped: "Too many attempts. Please try again after 15 minutes."

---

### FEAT-AUTH-02: Merchant Business Registration & KYC Submission
- **Actor**: Merchant (Shop Owner)
- **Preconditions**: Verified mobile number; valid Indian business.
- **Input**: Shop Name, Trade Category (Food, Fashion, Footwear, Electronics, Real Estate), Physical Address, GPS Pin, GSTIN or Shop & Establishment License (Gumasta) PDF/Image.
- **Process**:
  1. Merchant inputs store details and pins location on map.
  2. Uploads KYC document directly to Cloudinary using secure signed upload.
  3. System saves store with status `PENDING_VERIFICATION`.
  4. Notification queued for Super Admin review.
- **Success Criteria**: Store created in staging state; merchant directed to onboarding status screen.
- **Failure Modes**: Missing required fields, GPS location outside active beta cities (Nagpur/Mumbai).

---

### FEAT-AUTH-03: Staff PIN-Based POS Login
- **Actor**: Store Cashier / Floor Manager
- **Preconditions**: Shop Owner has registered staff member (strictly max 1 staff per merchant in Beta).
- **Input**: Store Registered Mobile Number, 6-digit Staff Scanner PIN.
- **Process**:
  1. Staff selects "Staff Terminal" on login screen.
  2. Enters store mobile number and assigned 6-digit PIN.
  3. System validates hashed PIN against `merchant_staff` record.
  4. Issues restricted JWT with `ROLE_CASHIER` scoped solely to `/api/v1/redemptions/*`.
- **Success Criteria**: Cashier enters dedicated high-speed QR camera scanner interface directly.
- **Failure Modes**: Invalid PIN; account deactivated by owner; locked out after 5 consecutive wrong attempts.

---

## 2. Hyper-Local Video Feed Features

### FEAT-FEED-01: Proximity-Based Vertical Reel Feed
- **Actor**: Shopper
- **Preconditions**: Shopper location (GPS coordinates) provided or city center selected.
- **Input**: Latitude, Longitude, Radius Filter (2 km, 5 km, 10 km), Category Filter (Optional).
- **Process**:
  1. Client sends coordinates and active distance radius.
  2. Backend performs spatial query using PostGIS (`ST_DWithin`) filtering for `status = 'APPROVED'`.
  3. Results returned paginated (10 reels per page), sorted by distance ascending.
  4. Client preloads video via optimized direct MP4 stream from Cloudinary CDN.
- **Success Criteria**: Continuous vertical scroll feed displaying 15–60s videos with merchant name, distance badge (e.g. "1.2 km away"), and floating "Claim Coupon" button.
- **Failure Modes**: Location denied: falls back to city-center default feed with location prompt banner.

---

### FEAT-FEED-02: Merchant Reel Studio & Upload Pipeline (Cloudinary Direct)
- **Actor**: Merchant Owner
- **Preconditions**: Verified merchant account; within monthly upload quota (1–5 reels/month).
- **Input**: 15–60s MP4/MOV vertical video (9:16), audio selection (Camera mic OR live voiceover), caption (max 150 chars).
- **Process**:
  1. Merchant records in-app or uploads video from gallery.
  2. Audio policy enforced: no background copyrighted music library allowed.
  3. Client-side video metadata validation: aspect ratio (9:16) and duration (15–60s) verified before upload.
  4. Client fetches upload signature from backend and uploads directly to Cloudinary.
  5. Cloudinary automatically extracts poster WebP thumbnail and generates optimized delivery URL.
  6. Reel tagged immediately with status `PENDING_ADMIN_MODERATION`.
- **Success Criteria**: Reel queued in Super Admin Moderation dashboard; merchant notified of pending review.
- **Failure Modes**: Duration <15s or >60s rejected; unsupported aspect ratio warned.

---

## 3. Dynamic Coupon & Anti-Fraud Redemption Features

### FEAT-CPN-01: Sector-Governed Coupon Creation
- **Actor**: Merchant Owner
- **Preconditions**: Merchant has active account; attached to an uploaded reel.
- **Input**: Discount Type (Percentage Off, Flat ₹ Off, BOGO), Minimum Order Value, Offer Terms, Expiry Duration.
- **Process**:
  1. Merchant configures offer terms.
  2. System enforces hard validity limits based on sector:
     - **Food & Dining**: 2 to 5 days maximum.
     - **Clothes, Shoes, Electronics**: 15 days maximum.
     - **Property & Real Estate**: Up to 60 days maximum.
  3. System validates constraints and links coupon template to reel ID.
- **Success Criteria**: Coupon template saved; displayed as sticker/overlay on approved reel.
- **Failure Modes**: Attempting to set expiration exceeding sector limit triggers validation error.

---

### FEAT-CPN-02: Shopper One-Tap Claim & Wallet Management
- **Actor**: Shopper
- **Preconditions**: Authenticated shopper viewing live reel.
- **Input**: Tap on "Claim Coupon" button.
- **Process**:
  1. Client sends coupon claim request.
  2. Server checks shopper claim limit (max 1 active claim per merchant per day).
  3. Record inserted in `user_coupons` with status `CLAIMED` and computed `expires_at`.
  4. Coupon added to Shopper In-App Wallet with live countdown clock.
- **Success Criteria**: Instant claim animation; badge count updated in wallet; countdown timer started.
- **Failure Modes**: Duplicate claim attempt returns "Coupon already in your wallet".

---

### FEAT-CPN-03: In-Store Anti-Screenshot Dynamic QR Redemption
- **Actor**: Shopper & Cashier / Owner
- **Preconditions**: Shopper present at physical store; coupon in `CLAIMED` status.
- **Input**:
  - Shopper: Taps "Redeem at Counter" in wallet.
  - Cashier: Scans QR code using Fyndo Staff Terminal.
- **Process**:
  1. Shopper app generates a dynamic TOTP QR code that cryptographically refreshes every **60 seconds**.
  2. Screen brightness is maxed out; screenshot prevention flag enabled on Android/iOS.
  3. Cashier scans QR code containing `{ coupon_claim_id, totp_token, timestamp }`.
  4. Backend verifies:
     - TOTP token matches current or previous 60s window.
     - Coupon is `CLAIMED` and not `EXPIRED` or `REDEEMED`.
     - Requesting cashier belongs to the specific merchant owning the coupon.
     - Cashier device GPS matches store geo-fence (within 200m).
  5. Transaction committed: status updated to `REDEEMED`, `redeemed_at` timestamp recorded.
  6. Shopper receives instant reward (reward coins / digital scratch card).
- **Success Criteria**: Cashier screen displays green checkmark with bill discount amount; shopper screen displays confetti + reward scratch card.
- **Failure Modes**:
  - Expired QR / screenshot: "Code expired. Please ask customer to refresh QR."
  - Already redeemed: "Voucher already redeemed at 14:22 PM."
  - Wrong store: "This coupon belongs to a different merchant."

---

## 4. Moderation & Administration Features

### FEAT-ADM-01: Admin Video & KYC Moderation Queue
- **Actor**: Super Admin
- **Preconditions**: Authenticated via MFA on Admin Web Console.
- **Input**: Approval or Rejection with structured reason tags.
- **Process**:
  1. Admin inspects pending reels: checks video content, verifies raw voiceover compliance, audits coupon claims.
  2. Admin inspects pending merchant KYCs: verifies GSTIN/Gumasta document.
  3. Admin submits decision: `APPROVE` or `REJECT` (with canned reason + custom notes).
  4. If approved: Reel immediately published to PostGIS feed index.
  5. If rejected: Push notification sent to merchant with actionable feedback.
- **Success Criteria**: Reel status updated; audit log entry recorded with Admin ID and timestamp.
- **Failure Modes**: Incomplete rejection reason blocks submission.
