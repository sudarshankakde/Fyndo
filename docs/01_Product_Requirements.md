# 01 - Product Requirements Document (PRD)

## 1. Project Overview
- **Project Name**: Fyndo ("Reel & Redeem")
- **Product Type**: Hyper-Local Video Discovery & In-Store Digital Coupon Redemption Platform
- **Target Launch Scope**: Single-City Beta (Nagpur / Mumbai, India)
- **Primary Objective**: Bridge online local video discovery and in-person foot traffic redemptions for neighborhood retailers, fashion boutiques, shoe stores, electronics hubs, eateries, and property developers.

---

## 2. Problem Statement
1. **Local Merchant Invisibility**: Small and mid-size local shopkeepers struggle to reach nearby shoppers. Traditional print flyers and generic listings yield poor conversion and no measurable foot-traffic attribution.
2. **Shopper Discovery Friction**: Consumers spend hours scrolling social feeds showing generic global content rather than exclusive deals within a 2–10 km radius of where they are currently located.
3. **Coupon Screenshot Fraud & Leakage**: Conventional static voucher codes are leaked online, screenshotted, or shared across WhatsApp groups without in-store verification.
4. **Off-Platform Disintermediation ("Uber Driver Problem")**: Customers and merchants may attempt to bypass app redemptions to avoid friction or fees, depriving the platform of data and engagement loops.

---

## 3. Product Vision & Value Proposition
- **For Shoppers**: Discover vertical 15–60s video reels of nearby stores, instant map navigation, dynamic one-tap coupons, and gamified loyalty rewards for verifying in-store redemptions.
- **For Merchants**: Simple in-app reel recording with authentic voiceovers, zero copyright liability, custom coupon builder tailored to business type, and real-time QR redemption scanner for checkout counters.
- **For Admins**: End-to-end moderation queue ensuring quality, compliance, and verified merchant KYC prior to reel publication.

---

## 4. Target Merchant Sectors & Rule Configurations

| Sector | Target Merchant Types | Max Offer Validity | Typical Promotion Models |
|---|---|---|---|
| **Food & Dining** | Cafes, Restaurants, Bakeries, Sweet Shops | **2 to 5 days** | Flash discounts, Happy hour BOGO, Minimum bill ₹300 off |
| **Clothes & Fashion** | Boutiques, Ethnic wear, Daily apparel | **15 days** | Flat 20% off new arrivals, Festive clearance |
| **Shoes & Footwear** | Branded dealers, Casual & athletic footwear | **15 days** | Flat ₹500 off on ₹2,500 bill, Buy 1 Get 1 on socks/accessories |
| **Electronics** | Mobile stores, Appliance showrooms, Repair | **15 days** | Free tempered glass with service, ₹1,000 off appliances |
| **Property & Real Estate**| Builders, Plot developers, Flat promoters | **60 days (2 months)**| Free site visit voucher, ₹50,000 booking discount token |

---

## 5. User Roles & Account Architecture

### 5.1 Shopper (Consumer)
- **Role**: End user discovering deals and visiting local stores.
- **Auth**: Mobile Phone OTP (SMS/WhatsApp) with secondary Google Sign-In & Apple ID.
- **Key Capabilities**: Geo-located vertical reel feed, category filters, interactive shop map, one-tap coupon save to wallet, TOTP dynamic QR code display for in-store redemption, multilingual UI toggle (English, Hindi, Marathi).

### 5.2 Merchant (Shop Owner)
- **Role**: Business owner registered on Fyndo.
- **Auth**: Mobile Phone OTP + Business Verification (GSTIN or Shop & Establishment License).
- **Key Capabilities**: Manage shop profile, record & upload 15–60s reels (1–5 reels/month in Beta), configure coupon terms & category constraints, view store foot-traffic analytics, invite 1 store manager/accountant.

### 5.3 Cashier / Staff (Manager / Accountant)
- **Role**: Checkout operator at physical store (limited access).
- **Quota**: Strictly 1 owner + 1 manager/accountant per business.
- **Auth**: Merchant-assigned 6-digit Staff PIN / phone login.
- **Key Capabilities**: Built-in camera QR scanner to scan and validate customer's dynamic QR coupon, instant green/red status, daily redemption count log. Cannot edit business profile or delete reels.

### 5.4 Super Admin
- **Role**: Platform administrator.
- **Auth**: Multi-Factor Authentication (MFA) Web Dashboard.
- **Key Capabilities**: Video reel review & moderation queue, merchant KYC approval/rejection, fraud alert dashboard, category-level rule parameters, city geo-fence management.

---

## 6. Business & Monetization Model

### Phase 1: Launch & Market Penetration (Beta)
- **Platform Fee**: **100% Free** for both merchants and shoppers for the first 3 months.
- **Rationale**: Eliminates merchant reluctance to scan coupons and removes any incentive for off-platform evasion during user acquisition.
- **Upload Limit**: 1 to 5 approved video reels per merchant per month.

### Phase 2: Tiered Subscriptions & Promotions
1. **Tiered Monthly Subscriptions**:
   - *Free Tier*: 2 reels/month, standard listing.
   - *Pro Merchant*: 15 reels/month, detailed footfall analytics, priority moderation.
2. **Featured Reel Boosts**:
   - Hyper-local sponsored placement pushing reels to top of feed within selected 2–10 km radius.
3. **Performance Fee / Commission Per Redemption**:
   - Small flat fee (e.g. ₹15–₹25 per verified redemption) introduced only after measurable ROI and customer traffic is established.
