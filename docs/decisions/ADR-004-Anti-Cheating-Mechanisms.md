# ADR-004: Anti-Cheating & Disintermediation Mechanisms

## Status
**Accepted**

## Context
Hyper-local coupon systems encounter two classic failure modes:
1. **Screenshot Leaking**: A customer shares a screenshot of a voucher code with friends or WhatsApp groups, depleting merchant stock or bypassing user limits.
2. **Platform Disintermediation ("The Uber Driver Problem")**: Once a shopper discovers a store, merchant and customer transact directly off-platform to avoid platform fees.

## Decision
We implement a multi-layered security architecture:
1. **Dynamic TOTP QR Code**: Vouchers are displayed as time-based rotating QR codes (RFC 6238) that refresh every 60 seconds. Static screenshots become invalid within 60s.
2. **100% Free Platform in Phase 1**: Zero merchant fees or commissions during Beta eliminates the financial incentive for shopkeepers to transact off-platform.
3. **Shopper-Only In-App Reward Hook**: Shoppers earn loyalty coins and instant digital scratch cards only when the merchant's POS scanner commits a verified redemption to the cloud ledger.
4. **Geofenced Verification**: Cashier scanner validates GPS distance against registered shop coordinates (must be within 200 meters).

## Alternatives Considered
- **Static Numeric Voucher Codes (e.g. FYNDO50)**: Highly vulnerable to leaked screenshots and WhatsApp forwarding.
- **Immediate Merchant Commission**: Induces merchants to ask customers to pay cash directly and ignore the app.

## Consequences
- Requires continuous clock synchronization between client device and backend (with a ±1 time step tolerance window).
- Eliminates coupon screenshot abuse entirely.
- Preserves customer loyalty retention loop.
