# ADR-001: Core Technology Stack Selection

## Status
**Accepted**

## Context
Fyndo requires:
1. High-speed mobile video feed browsing and dynamic QR scanning at checkout.
2. Hyper-local geospatial indexing (2 km, 5 km, 10 km radiuses) with PostGIS.
3. Low friction merchant onboarding and rapid cashier POS scanning.
4. Background video processing (FFmpeg transcoding to HLS).
5. Robust request/response schema validation and high-concurrency async I/O.

## Decision
We select the following core stack:
- **Backend API**: Python 3.11+ / 3.12 with **FastAPI**, Uvicorn, and Pydantic v2.
- **ORM & Migrations**: SQLAlchemy 2.0 (Async) + GeoAlchemy2 + asyncpg with Alembic migrations.
- **Database**: PostgreSQL 16 with the **PostGIS** extension for geospatial queries.
- **Cache**: Redis 7 (used for session tokens, OTP TTL, and rate limiting).
- **Media Storage & CDN (Beta Scope)**: **Cloudinary** for video and image storage, automatic poster thumbnail generation, on-the-fly transformations (e.g., `f_auto`, `q_auto`, `ar_9:16`), and global CDN delivery. Using Cloudinary signed client uploads eliminates AWS S3/CloudFront infrastructure overhead and manual FFmpeg servers for Beta.
- **Frontend Architecture & Platform Segregation**:
  - **Web Application (`frontend/`)**: Exclusively tailored as the **Fyndo Business & Admin Portal** for **Merchant Store Owners** (Studio, Reel & Sector Coupon Publisher, Analytics, Cashier PIN setup), **Store Cashiers** (POS billing counter terminal), and **Super Admins** (Video moderation desk).
  - **Mobile Application**: Exclusively for **Shoppers & End-Users** (Full-screen 9:16 vertical video reel feed, hyper-local proximity discovery, and 60-second dynamic TOTP QR in-store redemptions).
  - **Web Visitor Gateway**: Shoppers visiting the web application are greeted by an interactive **Mobile App Showcase & Install Gateway** (`/app`) directing them to install the mobile app for live deal discovery and coupon redemptions.
  - **Styling & UI**: **Tailwind CSS** (v3.4) + **shadcn/ui** (accessible Radix UI component primitives).
  - **Server State Management**: **TanStack Query v5** (`useQuery`, `useMutation`) for caching, optimistic updates, and background re-fetching.
  - **Client Global State**: **Redux Toolkit** (`@reduxjs/toolkit` + `react-redux`) for auth credentials, language preferences, active filter sheets, and POS scanner terminal session.
- **Containerization**: Docker Compose for local development and unified staging.

## Alternatives Considered
- **AWS S3 + CloudFront**: Replaced by Cloudinary for Beta. Cloudinary eliminates the heavy operational burden of AWS IAM roles, bucket policies, CloudFront distribution cache invalidations, and manual video thumbnail generation.
- **Immediate Celery / FFmpeg HLS Worker**: Deferred. Cloudinary handles direct upload, thumbnail extraction, and dynamic video optimizations natively without requiring background worker containers.
- **Node.js / Express**: Fast I/O, but FastAPI offers superior automatic OpenAPI/Swagger generation, strict runtime validation via Pydantic v2, native asynchronous concurrency, and deep synergy with Python's rich data and media ecosystems.
- **MongoDB with 2dsphere**: Rejected because coupon claims and redemption ledgers require ACID transactions and relational foreign keys to prevent double-spending.
- **Next.js Full-Stack**: Rejected to maintain strict decoupling between the customer/cashier mobile clients and the backend API & worker services.
- **Vanilla CSS / Ad-hoc Styling**: Replaced by Tailwind CSS + shadcn/ui to maximize accessible component reusability, consistent theming, and rapid delivery across web and mobile.

## Consequences
- Ultra-lean Beta infrastructure: No Celery worker container, Redis queue broker configuration, or FFmpeg system binaries required for initial launch.
- Direct upload-to-publish workflow: Uploaded reels transition directly to `PENDING_ADMIN_MODERATION` without transcoding lag.
- Clean separation between server state (TanStack Query) and UI client state (Redux Toolkit).
- Consistent, accessible UI design system powered by Tailwind utility classes and shadcn/ui primitives.
- Requires Python 3.11+ and virtual environment / poetry / pip-tools in `backend/`.
- Requires PostgreSQL PostGIS extension and GeoAlchemy2 for spatial types.
- Strict code splitting and component decomposition ensure files stay strictly under 300 LOC.

