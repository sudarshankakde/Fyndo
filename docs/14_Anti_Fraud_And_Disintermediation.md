# 14 - Anti-Fraud & Disintermediation Strategy

> **Context**: Hyper-local voucher platforms frequently fail due to off-platform bypassing ("Uber driver problem"), coupon screenshot leaking, and merchant-customer collusion.

---

## 1. Disintermediation Defense: The "Uber Driver Problem"

### The Threat
Customers and shopkeepers realize they can strike deals directly, bypassing the platform to save transaction fees or avoid checkout friction.

### Fyndo Countermeasures
1. **100% Free Platform in Beta (Phase 1)**:
   - Zero commissions charged to merchants for the first 3 months.
   - Because the merchant pays ₹0, there is **zero financial incentive** to transact off-platform.
2. **Shopper-Side Reward Incentive Loop**:
   - The shopper only unlocks **Fyndo Reward Coins / Digital Scratch Cards** when the cashier completes an official in-app QR scan.
   - If the merchant offers a manual off-platform discount, the shopper misses out on their platform loyalty streak and cashback.
3. **Store Foot-Traffic Analytics Value**:
   - Merchants only receive detailed footfall metrics, customer return rates, and video reach analytics for customers scanned through the platform.

---

## 2. Dynamic TOTP QR: Anti-Screenshot Architecture

### The Threat
A customer takes a screenshot of a voucher or shares a voucher code across a WhatsApp group, allowing 20 friends to use the same discount code.

### Fyndo Countermeasures
1. **60-Second Cryptographic Rotation**:
   - The redemption QR does not contain a static voucher string.
   - It encodes a time-based TOTP hash (RFC 6238) derived from the user's secret key and current Unix epoch divided by 60.
   - Any screenshot shared to WhatsApp becomes cryptographically invalid within 60 seconds.
2. **Screen Brightness & OS Security**:
   - On mobile apps, the screen disables screenshot capture (`FLAG_SECURE` on Android).
   - Web PWA applies a watermarked shifting canvas animation over the QR code.
3. **Atomic Single-Use Settlement**:
   - Once a cashier terminal scans a coupon, an atomic transaction marks the coupon as `REDEEMED` in PostgreSQL and sets a Redis lock on `claim_id`.
   - Any subsequent scan returns `HTTP 409 Conflict: Already Redeemed`.

---

## 3. Location Geofence & Collusion Prevention

### The Threat
A merchant or friend claims coupons from their own home and redeems them remotely to fraudulently inflate redemption numbers or claim shopper rewards.

### Fyndo Countermeasures
1. **Cashier GPS Verification**:
   - When the cashier scans the QR, the POS scanner submits device coordinates.
   - The API calculates distance between cashier coordinates and registered shop coordinates:
     ```sql
     ST_Distance(cashier_coords, shop_coords) <= 200 meters
     ```
   - If greater than 200m, redemption is flagged or rejected.
2. **Shopper Velocity Limits**:
   - Strict cap of **1 active claim per merchant per customer per 24-hour window**.
   - Maximum 5 active coupon claims across all merchants simultaneously per shopper.
3. **Abuse Heuristics & Anomaly Detection**:
   - Flag accounts if >10 redemptions occur within 5 minutes at a single small merchant terminal.
   - Super Admin fraud alerts triggered for sudden velocity spikes.
