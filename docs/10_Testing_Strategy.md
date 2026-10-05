# 10 - Testing Strategy

> **Platforms**: Pytest & HTTPX AsyncClient (Backend API/Unit), Vitest (Frontend Unit), Playwright (E2E)  
> **Coverage Goal**: >80% coverage on core financial, redemption, and security logic.

---

## 1. Testing Pyramid & Tooling

```text
       ▲
      / \        E2E Tests (Playwright)
     /   \       - Complete Shopper Claim to Cashier Scan Loop
    /-----\      
   /       \     Integration Tests (Pytest + HTTPX AsyncClient + Test DB)
  /         \    - FastAPI route contracts, DB constraints, PostGIS spatial queries
 /-----------\   
/             \  Unit Tests (Pytest / pytest-asyncio / Vitest)
/---------------\ - TOTP calculation, Pydantic validators, Distance calc
```

---

## 2. Business-Critical Test Scenarios

### 2.1 Dynamic TOTP & Anti-Fraud Redemption Tests
- [ ] **Valid Scan**: Fresh TOTP token (<60s) for active claimed coupon successfully marks coupon as `REDEEMED`.
- [ ] **Drift Tolerance**: TOTP token generated 75s ago (1 step drift) accepted; token from 180s ago rejected with `HTTP 410 Gone`.
- [ ] **Screenshot Replay Attack**: Attempting to reuse an already redeemed TOTP token immediately rejected with `HTTP 409 Conflict`.
- [ ] **Concurrent Double-Spend**: Two simultaneous cashier scans for the same coupon trigger atomic database lock; only one succeeds, second returns error.
- [ ] **Cross-Merchant Rejection**: Cashier from Store B attempting to scan a coupon belonging to Store A receives `HTTP 403 Forbidden`.

### 2.2 Sector-Governed Offer Validity Tests
- [ ] **Food Cap**: Attempting to create a Food coupon with 6 days validity throws validation exception.
- [ ] **Fashion / Footwear / Electronics Cap**: Attempting to set 16 days validity throws validation exception.
- [ ] **Property Cap**: Validates up to 60 days validity.

### 2.3 PostGIS Proximity Feed Tests
- [ ] Shopper at Sitabuldi (Nagpur) with 2 km radius filter receives only stores within 2000 meters.
- [ ] Soft-deleted or unapproved reels (`PENDING_MODERATION`) are excluded from feed queries.

---

## 3. Mocking & Isolation Strategy
- **SMS Gateway**: Mocked in test environment with fixed test numbers returning OTP `123456`.
- **Media Storage**: In-memory mock returning deterministic Cloudinary signed upload signatures and mock delivery URLs.
- **Database**: Ephemeral Docker PostgreSQL container with PostGIS enabled.
