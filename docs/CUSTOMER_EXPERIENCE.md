# CUSTOMER_EXPERIENCE.md — Fyndo Customer Experience Specification

> **Core Philosophy**: **The user should experience a finished product, not the development process behind it.**  
> **Target Audience**: Local Retail Merchants, In-Store Shoppers, Counter Staff/Cashiers, Platform Admins  
> **Launch Cities**: Nagpur & Mumbai, India

---

## 1. Prime Directive: Customer Reality vs. Engineering Reality

Engineering systems require abstractions, protocols, database states, and security handshakes. **None of these belong in the customer's mental model.**

```text
ENGINEERING REALITY (Docs, Code, Logs, DB)
├── Webhook event: qr_totp_cycle_verification
├── RBAC check: role.has_permission(STORE_OWNER)
├── HTTP 403 Forbidden: geofence_radius_exceeded
└── DB State: REEL_PENDING_SUPERADMIN_MODERATION

                    ↓↓↓ TRANSLATION WALL ↓↓↓

CUSTOMER REALITY (UI, Messages, Buttons, Voice)
├── "Coupon verified. Apply ₹100 discount."
├── "Only store owners can edit store details."
├── "You're a bit too far from the shop. Please visit the store to claim."
└── "Video uploaded! We review videos within 2 hours to keep the feed trustworthy."
```

---

## 2. The Five-Lens Quality Review

Before any screen, component, or flow is marked complete, it must pass five distinct evaluations:

```text
1. PRODUCT LENS
   "Does this directly solve the shopkeeper's or shopper's real-world problem?"

2. UX LENS
   "Can a busy shopkeeper or first-time smartphone user use this without training?"

3. VISUAL LENS
   "Does it feel tactile, purposeful, and free of generic AI-generated aesthetic clutter?"

4. CONTENT LENS
   "Does every single word sound human, direct, respectful, and locally natural?"

5. TECHNICAL LENS
   "Is the underlying architecture secure, resilient, fast (<300 LOC), and tested?"
```

---

## 3. Experience Pillars by Persona

### A. The Local Shopkeeper (Merchant Owner)
* **Context**: Managing foot traffic, inventory, suppliers, and billing in Sitabuldi (Nagpur) or Dadar (Mumbai). Often has 1–2 minutes between customers.
* **Emotional State**: Wants more customers walking into the physical store; skeptical of complicated software or hidden commissions.
* **Experience Mandate**:
  - Immediate clarity: Show walk-in customers and revenue generated.
  - Zero tech jargon: No mentions of "TOTP", "geofencing algorithms", "REST API", or "database transactions".
  - Reassurance: Emphasize that the platform is 100% free with zero commission during the pilot.

### B. The Cashier / Counter Staff
* **Context**: Standing at the checkout billing desk with customers waiting in line.
* **Emotional State**: Needs speed (sub-3-second redemption) and clear confirmation so they never misapply discounts.
* **Experience Mandate**:
  - Simple 6-digit staff PIN access. No complex login with passwords or 2FA.
  - Instant visual feedback: Large green "VERIFIED & APPLIED" confirmation with exact rupee savings.
  - Fail-safe guidance: If coupon is expired or already used, show clear human instructions: *"This coupon has already been redeemed."*

### C. The Local Shopper
* **Context**: Browsing short videos on mobile while traveling or relaxing, looking for genuine local bargains nearby.
* **Emotional State**: Wants entertainment, discovery, and instant savings without spam or bait-and-switch.
* **Experience Mandate**:
  - Vertical video first (full screen 9:16).
  - Clear distance indicator: *"450m away in Sitabuldi"*, not coordinates or GPS telemetry.
  - Effortless wallet: Tap "Claim", show rotating coupon QR at the counter, get instant savings.

### D. The Super Admin
* **Context**: Reviewing merchant KYC, auditing reels for copyright and community guidelines.
* **Experience Mandate**:
  - Fast keyboard shortcuts and unambiguous Approve/Reject actions with pre-set human feedback reasons.

---

## 4. Anti-Slop Content Principles

1. **Be Direct, Not Wordy**: Delete fluff. Say what happened and what to do next.
2. **Never Blame the User**: Instead of *"You entered an invalid phone number"*, write *"Enter a 10-digit mobile number."*
3. **Respect Local Vernacular**: Ensure Hindi (हिंदी) and Marathi (मराठी) translations use natural spoken phrasing, not literal machine translation.
4. **No Artificial Excitement**: Avoid exclamations and generic SaaS hype (*"Unlock limitless growth with our cutting-edge AI engine!"*). Say: *"Post a video of your store offer."*
