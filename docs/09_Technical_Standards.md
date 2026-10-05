# 09 - Technical Standards & Coding Conventions

> **Platforms**: Python 3.11+ / FastAPI (Backend) & React / TypeScript (Frontend)  
> **Golden Rule**: Maintain strict separation of concerns and adhere to file line limits.

---

## 1. File Length & Modularization Directives

- **Target Line Limit**: Under **300 lines of code** per file.
- **Hard Ceiling**: Absolute maximum of **400 lines** for exceptional edge cases.
- **Automatic Decomposition**:
  - If a React component approaches 250 lines, extract sub-components into `components/` and state logic into a custom hook in `hooks/`.
  - If a FastAPI router approaches 250 lines, split into specialized sub-routers (`routers/`) or delegate business logic to `services/`.

---

## 2. Architectural Boundaries & Layering

### 2.1 Frontend Architecture (`frontend/src/`)
1. **Presentational Components (`components/`)**:
   - Composed with **shadcn/ui** primitives located in `components/ui/` (Button, Dialog, Sheet, Badge, Card).
   - Styled exclusively with **Tailwind CSS** utility classes and the `cn()` helper.
   - Strictly presentational and single-responsibility. **Never invoke raw `fetch`/Axios in components**.
2. **Server State Management (TanStack Query)**:
   - Data fetching and mutations are encapsulated in specialized query hooks (`hooks/queries/` and `hooks/mutations/`).
   - Network requests are isolated in `services/`.
   - Leverages `staleTime`, optimistic UI updates, and automated cache invalidation.
3. **Client Global State (Redux Toolkit - `store/`)**:
   - Manages client-only app state (auth session, language toggle, bottom sheet visibility, scanner session).
   - Structured into clean slices (`authSlice`, `uiSlice`, `scannerSlice`) using `createSlice`.
4. **Custom Hooks (`hooks/`)**:
   - Encapsulates device APIs (camera viewfinder, geolocation watcher, QR TOTP ticker).
5. **Utilities (`utils/`)**:
   - Pure helpers: `cn()` (`clsx` + `tailwind-merge`), geo-distance Haversine formulas, currency formatters.

### 2.2 Backend Architecture (`backend/app/`)
1. **API Routers (`api/v1/`)**:
   - Request routing, dependency injection (`Depends`), HTTP response status orchestration.
   - No direct database queries or raw SQL in routers.
2. **Services (`services/`)**:
   - Domain business logic (e.g., TOTP validation, sector expiry verification, daily quota checks).
3. **Pydantic Schemas (`schemas/`)**:
   - Strict Pydantic v2 input/output models, validators, and serializers.
4. **Database Models (`models/`)**:
   - SQLAlchemy 2.0 declarative models with `Mapped` type annotations and GeoAlchemy2 geometries.
5. **Core & Dependencies (`core/`)**:
   - Database engine (`async_sessionmaker`), JWT/auth helpers, and app settings (`pydantic-settings`).

---

## 3. Code Quality & Standards

### Frontend (TypeScript)
- **Strict Mode**: `"strict": true` enforced in `tsconfig.json`.
- **No `any` Policy**: Use explicit types, interfaces, or generics.
- **Linting & Formatting**: ESLint + Prettier.

### Backend (Python)
- **Type Annotations**: Mandatory type hints on all functions and async methods (`mypy` compliant).
- **Tooling**: `ruff` for ultra-fast linting and code formatting (PEP 8 compliant).
- **Error Handling**: Use custom HTTPException subclasses with standardized error envelopes.

