# 12 - AI Development Rules & Constitution

> **Scope**: Mandatory behavioral and architectural constraints for AI Coding Agents working on Fyndo.

---

## 1. Prime Directives (The Constitution)

1. **Source of Truth First**: Always inspect `/docs` before proposing or generating any code. Requirements in `01_Product_Requirements.md` through `14_Anti_Fraud_And_Disintermediation.md` are canonical.
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
9. **No Duplicate Utilities**: Always check `src/utils/` and `src/components/common/` before creating a new utility function or UI element.
10. **Explain Dependencies**: Never install a new NPM or system dependency without explaining why existing packages are insufficient.

---

## 2. The AI Development Loop

For every feature or modification, the AI agent must strictly follow this review process:

```text
REQUIREMENTS INSPECTION (docs/ PRD, Customer Experience, Content Guidelines)
     ↓
AFFECTED FILES ANALYSIS
     ↓
VERTICAL SLICE PLAN
     ↓
IMPLEMENTATION (<= 300 LOC per file)
     ↓
FUNCTIONAL TESTING & VERIFICATION (Pytest / TS build)
     ↓
UI / UX REVIEW (Anti-Slop, Layout, Spacing)
     ↓
CONTENT REVIEW (docs/CONTENT_GUIDELINES.md & docs/UI_COPY.md)
     ↓
FINAL USER PERSPECTIVE REVIEW (Does it feel like a real product?)
```

---

## 3. Pre-Commit Checklist for AI Agents
- [ ] Are all edited or created files under 300 lines of code?
- [ ] Are API calls strictly kept within `src/services/` and not embedded in React components?
- [ ] Did you update [06_Database_Design.md](file:///e:/MyProjects/Fyndo/docs/06_Database_Design.md) if schema changed?
- [ ] Did you update [07_API_Specification.md](file:///e:/MyProjects/Fyndo/docs/07_API_Specification.md) if an endpoint was touched?
- [ ] **Content Review**: Did you check all user-facing strings against [CONTENT_GUIDELINES.md](file:///e:/MyProjects/Fyndo/docs/CONTENT_GUIDELINES.md) and [UI_COPY.md](file:///e:/MyProjects/Fyndo/docs/UI_COPY.md)?
- [ ] **No Developer Leaks**: Are there ZERO internal development terms (`API`, `RBAC`, `TOTP`, `Geofence`, `JSON`, `HTTP codes`, `PWA`, `entity`, `LLM`) visible in customer UI?
- [ ] Do all unit and integration tests pass without warnings?
