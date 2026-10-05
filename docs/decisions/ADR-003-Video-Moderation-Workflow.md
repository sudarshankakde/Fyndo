# ADR-003: Video Moderation Workflow

## Status
**Accepted**

## Context
Hyper-local discovery feeds must maintain high aesthetic and informational standards. Unmonitored user-generated content from merchants could lead to low-quality blurry videos, deceptive discount claims, or inappropriate/offensive content.

## Decision
All reels remain in `PENDING_ADMIN_MODERATION` status after automated FFmpeg transcoding. 
- A video is **never made public** in the discovery feed until a Super Admin approves it via the Admin Console.
- Admin verifies: visual clarity, audio compliance (no copyrighted music), and coupon terms legitimacy.
- Service Level Agreement (SLA): Maximum 2-hour review turnaround between 9:00 AM and 9:00 PM IST.

## Alternatives Considered
- **Post-Publication Community Flagging**: Fast for merchants, but risks reputational damage if a scam or inappropriate video reaches local consumers.
- **Automated AI Video Moderation Only**: Costly per minute of video and prone to false negatives with regional languages (Hindi/Marathi voiceovers).

## Consequences
- Requires an active Super Admin review desk.
- Merchant UI must clearly show "Pending Review" progress with estimated approval time.
- Guarantees 100% curated, safe, and compliant discovery feed for consumers.
