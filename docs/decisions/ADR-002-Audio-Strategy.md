# ADR-002: Audio Strategy & Copyright Elimination

## Status
**Accepted**

## Context
Short-video platforms like Instagram Reels and TikTok rely heavily on licensed commercial audio libraries. However, commercial synchronization licenses for commercial merchant advertising are prohibitively expensive and expose an early-stage startup to copyright infringement claims and takedown notices.

## Decision
Fyndo strictly allows **only two audio sources** for merchant video uploads:
1. **Raw Camera Microphone Audio**: Ambient in-store sounds, shopowner dialogue, street ambiance.
2. **Recorded In-App Voiceovers**: The merchant narrates their offer or describes dishes/products.

**Third-party commercial music overlays are explicitly disabled** in the Reel Studio and rejected during Admin Moderation.

## Alternatives Considered
- **Royalty-Free Audio Library (Epidemic / AudioJungle)**: High licensing fee per active business video; generic stock elevator music diminishes authenticity of local shops.
- **Unrestricted Audio Upload**: High legal risk of copyright infringement.

## Consequences
- Zero copyright liability for Fyndo and participating merchants.
- Higher authenticity: Local shoppers hear the genuine shopkeeper explaining their craft in Hindi, Marathi, or English.
- Moderation queue includes explicit audio listening verification.
