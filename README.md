# Fyndo ("Reel & Redeem")

> **Hyper-Local Video Discovery & In-Store Digital Coupon Platform**  
> *Target Launch: Single-City Beta (Nagpur / Mumbai, India)*  
> *Languages: English, Hindi (हिंदी), Marathi (मराठी)*

---

## ⚡ Quick Start: Run Everything at Once

You can launch both the **Backend API** and the **Frontend Web App** concurrently with a single command from the project root:

### Option 1: Using Python (Recommended & Zero-Dependency)
```bash
python run_dev.py
```
*(Automatically uses your backend virtual environment, spawns both services, and aggregates color-coded logs in one terminal).*

### Option 2: Using NPM
```bash
npm start
# or
npm run dev
```

### Option 3: Windows Batch Script (Double-Click or CLI)
```cmd
start-dev.bat
```

---

## 🌐 Service URLs & Ports

Once started, the following services will be live:

| Service | URL / Port | Description |
|---|---|---|
| **Frontend Web App** | [`http://localhost:3000`](http://localhost:3000) | Shopper Reels, Store Manager, POS Terminal & Admin Desk |
| **Backend Core API** | [`http://localhost:5000`](http://localhost:5000) | FastAPI RESTful API server |
| **Interactive Swagger Docs** | [`http://localhost:5000/docs`](http://localhost:5000/docs) | Interactive OpenAPI documentation & live sandbox |
| **Interactive ReDoc** | [`http://localhost:5000/redoc`](http://localhost:5000/redoc) | Human-readable API specifications |
| **PostgreSQL 16 (Optional)** | `localhost:5432` | PostGIS geospatial database (via Docker) |
| **Redis 7 (Optional)** | `localhost:6379` | Token & OTP cache (via Docker / auto-falls back to FakeRedis) |

---

## 🐳 Infrastructure Services (PostgreSQL + Redis via Docker)

To run dedicated containerized PostgreSQL with PostGIS and Redis:

```bash
# Start background database and cache containers
docker compose up -d

# Stop infrastructure containers
docker compose down
```

> **Note**: In local development, the backend automatically uses SQLite (`fyndo_dev.db`) and in-memory `FakeRedis` if standalone Docker services are not running, so you can develop immediately without installing Docker.

---

## 🔧 Running Services Individually (Manual Terminal Mode)

If you prefer running services in separate terminal windows:

### Terminal 1: Backend API
```bash
cd backend

# Windows PowerShell:
.venv\Scripts\python -m uvicorn app.main:app --reload --port 5000

# macOS / Linux:
source .venv/bin/activate
uvicorn app.main:app --reload --port 5000
```

### Terminal 2: Frontend Web App
```bash
cd frontend
npm run dev
```

---

## 🧪 Testing & Verification

```bash
# Run backend pytest suite (all 11 integration tests)
npm run test:backend
# or: cd backend && pytest -v

# Verify frontend TypeScript build
npm run build:frontend
# or: cd frontend && npm run build
```

---

## 📖 Documentation Suite (Source of Truth)

All architectural, feature, and database contracts are strictly documented in [`/docs`](file:///e:/MyProjects/Fyndo/docs):

- **[Frontend Auth API Guide](file:///e:/MyProjects/Fyndo/docs/FRONTEND_AUTH_API_GUIDE.md)** *(API contracts for frontend & mobile devs)*
- [01 - Product Requirements Document](file:///e:/MyProjects/Fyndo/docs/01_Product_Requirements.md)
- [02 - User Flows & Workflows](file:///e:/MyProjects/Fyndo/docs/02_User_Flows.md)
- [03 - Feature Specifications](file:///e:/MyProjects/Fyndo/docs/03_Features.md)
- [04 - UI/UX Specification & Screen Inventory](file:///e:/MyProjects/Fyndo/docs/04_UI_UX_Specification.md)
- [05 - System Architecture Document](file:///e:/MyProjects/Fyndo/docs/05_System_Architecture.md)
- [06 - Database Design & Schema](file:///e:/MyProjects/Fyndo/docs/06_Database_Design.md)
- [07 - API Specification & Contracts](file:///e:/MyProjects/Fyndo/docs/07_API_Specification.md)
- [08 - Authentication & Authorization](file:///e:/MyProjects/Fyndo/docs/08_Authentication_Authorization.md)
- [09 - Technical Standards & Coding Conventions](file:///e:/MyProjects/Fyndo/docs/09_Technical_Standards.md)
- [10 - Testing Strategy](file:///e:/MyProjects/Fyndo/docs/10_Testing_Strategy.md)
- [11 - Deployment & Infrastructure](file:///e:/MyProjects/Fyndo/docs/11_Deployment.md)
- [12 - AI Development Rules & Constitution](file:///e:/MyProjects/Fyndo/docs/12_AI_Development_Rules.md)
- [13 - Project Roadmap & Vertical Slices](file:///e:/MyProjects/Fyndo/docs/13_Project_Roadmap.md)
- [14 - Anti-Fraud & Disintermediation Strategy](file:///e:/MyProjects/Fyndo/docs/14_Anti_Fraud_And_Disintermediation.md)

### Architectural Decision Records (ADRs)
- [ADR-001: Core Technology Stack Selection](file:///e:/MyProjects/Fyndo/docs/decisions/ADR-001-Tech-Stack.md)
- [ADR-002: Audio Strategy & Copyright Elimination](file:///e:/MyProjects/Fyndo/docs/decisions/ADR-002-Audio-Strategy.md)
- [ADR-003: Video Moderation Workflow](file:///e:/MyProjects/Fyndo/docs/decisions/ADR-003-Video-Moderation-Workflow.md)
- [ADR-004: Anti-Cheating & Disintermediation Mechanisms](file:///e:/MyProjects/Fyndo/docs/decisions/ADR-004-Anti-Cheating-Mechanisms.md)

---

## 🛠️ Tech Stack Overview
- **Backend API**: Python 3.11+ / 3.13 (FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2.0 Async, GeoAlchemy2)
- **Database**: PostgreSQL 16 + PostGIS extension (SQLite for zero-config dev)
- **Cache**: Redis 7 (Sessions, OTP verification, Rate limiting / in-memory FakeRedis fallback)
- **Media Storage & CDN (Beta)**: Cloudinary (Video hosting, automatic WebP thumbnails, on-the-fly transformations & global CDN)
- **Frontend (Web & Mobile)**: React 19 / TypeScript / Vite, Tailwind CSS (v3.4), shadcn/ui, TanStack Query v5, Redux Toolkit
- **Containerization**: Docker Compose
