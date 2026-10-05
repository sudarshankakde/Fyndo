# UI_COPY.md — Fyndo Master UI Copy Catalog

> **Purpose**: The canonical dictionary of approved UI strings. Developers and AI agents must choose from this catalog rather than inventing ad-hoc copy in code.

---

## 1. Global Navigation & Branding

| Key / Purpose | Approved Copy (EN) | Approved Copy (HI) | Approved Copy (MR) |
|---|---|---|---|
| **App Title** | Fyndo | फायन्दो | फायन्दो |
| **Merchant Hub** | Store Manager | स्टोर मैनेजर | स्टोअर मॅनेजर |
| **Counter Terminal** | Counter Scanner | काउंटर स्कैनर | काउंटर स्कॅनर |
| **Super Admin Desk** | Admin Desk | एडमिन डेस्क | अ‍ॅडमिन डेस्क |
| **Shopper App Switch** | Shopper App | ग्राहक ऐप | ग्राहक अ‍ॅप |
| **Login Action** | Log in | लॉग इन करें | लॉग इन करा |
| **Logout Action** | Log out | लॉग आउट करें | लॉग आउट करा |

---

## 2. Common Action Buttons

| Key / Purpose | Approved Button Label | Usage Rule |
|---|---|---|
| **Create Store** | `Register Your Store` | Onboarding trigger |
| **Upload Reel** | `Post Store Video & Offer` | Video upload modal trigger |
| **Setup Staff PIN** | `Create Counter PIN` | Cashier PIN modal trigger |
| **Verify Coupon** | `Scan & Apply Discount` | In-store POS button |
| **Claim Coupon** | `Save to My Coupons` | Shopper reel action |
| **Show Coupon** | `Show at Counter` | Shopper wallet action |
| **Save Changes** | `Save Details` | Forms & profiles |
| **Cancel Action** | `Cancel` | Dismissing dialogs |
| **Confirm Action** | `Confirm` | Committing actions |

---

## 3. Operational & Financial Metrics

| Technical Metric | Approved Customer Label | Helper / Explanation |
|---|---|---|
| `walkin_count` | Walk-in Customers | Verified in-store visits today |
| `disbursed_savings` | Customer Savings | Total rupee discounts given |
| `active_claims` | Saved in Wallets | Shoppers who saved your coupon |
| `video_views` | Video Views | Shoppers who watched your store video |
| `scanner_status: true` | Counter Ready | Ready to scan customer coupons |
| `scanner_status: false` | Scanner Offline | Tap to reconnect scanner |

---

## 4. Status Badges & Lifecycle

| Internal Code | Approved User-Facing Status | Color Semantic |
|---|---|---|
| `PENDING_REVIEW` | Under Review (takes ~2 hrs) | Amber / Warm Stone |
| `APPROVED` / `ACTIVE` | Live | Emerald / Green |
| `REJECTED` | Needs Edit | Red / Destructive |
| `CLAIMED` | Saved to Wallet | Amber / Neutral |
| `REDEEMED` | Redeemed at Counter | Emerald / Green |
| `EXPIRED` | Expired | Stone / Muted |

---

## 5. Standard Empty States

| Context | Heading | Subtext & Action |
|---|---|---|
| **Empty Wallet** | No saved coupons yet | "Explore nearby store videos to save on your next shopping trip." |
| **Empty Offers** | You haven't posted any offers | "Post a 15–60s video of your shop to attract nearby customers." |
| **Empty POS History** | No redemptions today | "Customer coupon redemptions will appear here in real time." |
| **Empty Moderation** | All caught up! | "No merchant videos currently waiting for review." |

---

## 6. Feedback & Notifications (Toasts)

| Event | Toast Message |
|---|---|
| **Store Created** | "Store profile saved! You can now publish your first store video." |
| **Reel Uploaded** | "Video uploaded! We review videos within 2 hours to keep the feed trustworthy." |
| **PIN Saved** | "Counter PIN saved. Give this 6-digit PIN to your cashier." |
| **Coupon Redeemed** | "Success! ₹{amount} discount applied for {customer}." |
| **Coupon Expired** | "This coupon has expired. Please ask the customer for an active coupon." |
| **Network Error** | "Couldn't connect. Please check your internet connection." |
