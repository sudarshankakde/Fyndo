# AGENTS.md — Fyndo AI Agent Master Instructions

> **Project**: Fyndo (Hyper-Local Short Video & Coupon Redemption Platform)  
> **Launch Scope**: Single-City Beta (Nagpur / Mumbai, India)  
> **Target Audience**: Local Shoppers, Local Merchants, Cashiers/Store Managers, Super Admins  
> **Languages**: English, Hindi (हिंदी), Marathi (मराठी)

---

## 1. Prime Directives for AI Coding Agents

1. **Source of Truth First**: Always inspect `/docs` before proposing or generating any code. Requirements in `/docs/01_Product_Requirements.md` through `/docs/14_Anti_Fraud_And_Disintermediation.md` are canonical.
2. **Never Invent Requirements**: If a requirement, database column, or API parameter is ambiguous or unspecified, consult docs or ask for clarification.
3. **Database Integrity**: Never modify database models or schema migrations without updating [06_Database_Design.md](file:///e:/MyProjects/Fyndo/docs/06_Database_Design.md).
4. **API Contract Integrity**: Never modify or add endpoints without updating [07_API_Specification.md](file:///e:/MyProjects/Fyndo/docs/07_API_Specification.md).
5. **Strict File Line Limit**: Keep all source code files strictly under **300 lines of code** (hard cap at 400 lines for edge cases). Modularize and decompose proactively.
6. **Strict Architecture & Separation of Concerns**:
   - **UI Components** (`src/components/`): Pure presentational components. Single responsibility only.
   - **Services Layer** (`src/services/`): All HTTP, API, and network communication. Never fetch inside UI components.
   - **Custom Hooks** (`src/hooks/`): Complex state, device APIs, and UI lifecycle logic.
   - **Utilities & Helpers** (`src/utils/`): Pure transformation, date/currency formatting, geo-distance calculations.
7. **Approved AI Models**: Default to `gemini-3.5-flash`. Use `gemini-3.5-flash-lite` for lightweight sub-tasks and `gemini-3.1-flash-lite` as fallback. Never use legacy/deprecated models.
8. **Vertical Slice Implementation**: Always implement one vertical slice at a time (DB schema -> Backend Service/API -> Tests -> Frontend Component -> Integration verification).
9. **User-Facing Content Rule (Hard Requirement)**:
   - **The user must experience a finished product, not the development process behind it.**
   - Never expose internal technical or architecture terms (e.g. `API`, `RBAC`, `entity`, `TOTP`, `geofence algorithm`, `workflow state`, `JSON`, `HTTP 403/500`, `PWA`, `database`, `LLM`, `AI-generated`) in customer-facing screens, buttons, labels, error messages, empty states, or notifications.
   - Consult `docs/CUSTOMER_EXPERIENCE.md`, `docs/CONTENT_GUIDELINES.md`, and `docs/UI_COPY.md` as canonical specifications for all UI text.
   - Every feature must pass the 5-step loop:
     `IMPLEMENT` → `FUNCTIONAL TEST` → `UI/UX REVIEW` → `CONTENT REVIEW` → `FINAL USER PERSPECTIVE REVIEW`.
   - Ask: *"Would a regular shopkeeper or customer in Nagpur/Mumbai naturally understand this?"* If not, rewrite it.

---

## 2. System Overview & Core Business Rules

| Entity / Topic | Core Specification |
|---|---|
| **Video Content** | 15–60 second vertical reels (9:16 aspect ratio). 1–5 reels/month per merchant in Beta. |
| **Audio Strategy** | Raw camera audio & voiceovers ONLY. No copyrighted music overlay allowed. |
| **Moderation** | **Mandatory Admin Moderation**. Reels remain in `PENDING_REVIEW` until approved by Super Admin. |
| **Merchant Roles** | 2 roles per merchant: **Owner** (full profile & offer control) and **Accountant/Manager/Cashier** (PIN-based POS scanner). |
| **Offer Validity** | Sector-governed: **Food (2–5 days)**, **Clothes/Shoes/Electronics (max 15 days)**, **Property/Plots (up to 60 days)**. |
| **Redemption Security** | Dynamic TOTP-backed QR code refreshing every 60 seconds to prevent screenshot sharing. |
| **Anti-Cheating Policy** | Platform is 100% free for merchants in Phase 1. Shoppers receive rewards/cashback only upon verified in-app scan to counter off-platform cheating. |

---

## 3. Directory Layout

```text
Fyndo/
├── .env.example
├── README.md
├── AGENTS.md
├── docker-compose.yml
├── docs/
│   ├── 01_Product_Requirements.md
│   ├── 02_User_Flows.md
│   ├── 03_Features.md
│   ├── 04_UI_UX_Specification.md
│   ├── 05_System_Architecture.md
│   ├── 06_Database_Design.md
│   ├── 07_API_Specification.md
│   ├── 08_Authentication_Authorization.md
│   ├── 09_Technical_Standards.md
│   ├── 10_Testing_Strategy.md
│   ├── 11_Deployment.md
│   ├── 12_AI_Development_Rules.md
│   ├── 13_Project_Roadmap.md
│   ├── 14_Anti_Fraud_And_Disintermediation.md
│   └── decisions/
│       ├── ADR-001-Tech-Stack.md
│       ├── ADR-002-Audio-Strategy.md
│       ├── ADR-003-Video-Moderation-Workflow.md
│       └── ADR-004-Anti-Cheating-Mechanisms.md
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI APIRouters (v1)
│   │   ├── core/         # DB session, JWT security, config
│   │   ├── models/       # SQLAlchemy 2.0 + GeoAlchemy2 models
│   │   ├── schemas/      # Pydantic v2 schemas
│   │   ├── services/     # Business logic (TOTP, sector limits, OTP)
│   │   ├── workers/      # (Deferred for Beta: Celery FFmpeg transcoding)
│   │   └── utils/        # Pure helpers
│   ├── alembic/          # Database migrations
│   └── tests/            # Pytest integration & unit test suite
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── ui/           # shadcn/ui accessible primitives (Radix UI)
│   │   │   ├── common/       # Shared presentation components
│   │   │   ├── feed/         # 9:16 vertical reel feed components
│   │   │   ├── coupon/       # Dynamic TOTP QR & wallet components
│   │   │   └── merchant/     # Merchant studio & POS scanner components
│   │   ├── hooks/            # TanStack Query hooks & device hooks (Camera, GPS)
│   │   ├── i18n/             # Multilingual dictionaries (EN, HI, MR)
│   │   ├── pages/            # View routing screens
│   │   ├── services/         # API HTTP client layer
│   │   ├── store/            # Redux Toolkit store & feature slices
│   │   ├── types/            # TypeScript interfaces & API contracts
│   │   └── utils/            # Pure functions & cn() class merger
│   └── tests/
└── scripts/
```

---

## 4. Development Workflow for AI Agents

1. **Step 1: Inspect Docs**: Read the target feature specification, data model, and API contract.
2. **Step 2: Propose Changes**: List target files to touch before writing code.
3. **Step 3: Vertical Slice Build**:
   - Write DB schema / migration.
   - Implement backend service and controller.
   - Implement frontend service, custom hook, and modular components (<300 lines each).
4. **Step 4: Test & Verify**: Run unit & integration tests; verify edge cases (e.g. expired coupons, invalid QR, unmoderated reels).
5. **Step 5: Document**: Update roadmap status in [13_Project_Roadmap.md](file:///e:/MyProjects/Fyndo/docs/13_Project_Roadmap.md) and record decisions in `docs/decisions/`.
