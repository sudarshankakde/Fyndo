# 17 - Super-Admin Panel (HTML / htmx)

> **Location**: `backend/app/admin/`
> **URL**: `/admin/` (mounted on the same FastAPI app as the mobile API)
> **Stack**: FastAPI + Jinja2 + htmx 2.0.4 (vendored) + hand-written CSS
> **Auth**: dedicated `SUPER_ADMIN` session cookie, independent of the shopper/merchant JWT

The panel is a server-rendered back office for operators. It exists so support and ops staff can
**see and edit the live data** in every table without SQL access, curl, or a mobile build. It is
deliberately outside the JSON API contract: it is not part of the OpenAPI schema, and its routes
never return the API's `{success, data, error}` envelope.

---

## 1. Why htmx instead of SQLAdmin / Django-admin

| Option | Verdict |
|---|---|
| **Django-admin style package** (e.g. `sqladmin`) | Rejected — adds a second framework surface, its own auth, and its own templating stack on top of an already-async FastAPI app. |
| **Custom htmx + Jinja2 panel** (chosen) | Reuses the existing async SQLAlchemy session, the existing `audit_log` helper, and the existing `SUPER_ADMIN` credentials. One page load, then partial swaps — no client framework, no build step. |

htmx is **vendored** at `app/admin/static/htmx.min.js`, so the panel works with no CDN and no
outbound network access.

---

## 2. Architecture

```
app/admin/
├── __init__.py      # exports admin_router
├── router.py        # /admin prefix, static asset route, sub-router assembly
├── deps.py          # session cookie, current_admin guard, RedirectToLogin
├── auth.py          # GET/POST /login, GET|POST /logout
├── views.py         # dashboard, list, create-form, detail
├── crud.py          # create / update / delete POST handlers
├── helpers.py       # context, redirect_to, form fields, apply_form
├── utils.py         # formatting, coercion, pagination query
├── registry.py      # SQLAlchemy mapper introspection → ModelMeta
├── configs.py       # per-table presentation overrides
├── templating.py    # Jinja2Templates + nav globals
├── static/
│   ├── admin.css
│   └── htmx.min.js
└── templates/
    ├── base.html        # sidebar nav + topbar shell
    ├── login.html       # standalone sign-in screen
    ├── dashboard.html   # counters + one tile per table
    ├── list.html        # search toolbar + table
    ├── detail.html      # read-only field list + delete
    ├── form.html        # create / edit form
    └── partials/table.html   # the htmx swap target
```

### 2.1 Generic CRUD engine

Rather than hand-writing a screen per table, `registry.py` introspects each SQLAlchemy model with
`sa_inspect(model).columns` and produces:

- `ColumnMeta` — name, human label, inferred `kind` (`text` / `integer` / `number` / `boolean` /
  `datetime` / `json` / `uuid`), nullability, primary-key flag, foreign-key target table, enum
  choices, and derive-at-render helpers (`widget`, `input_type`, `step`).
- `ModelMeta` — the table's label, list columns, searchable columns, default sort, page size.

`configs.py` then supplies only what cannot be inferred: labels, the columns shown in the list,
search columns, enum choices (models persist enums as plain strings), and the `secret` /
`readonly` lists. **Adding a new table to the panel is a single dict entry in `MODEL_CONFIGS`.**

### 2.2 Tables exposed

| Group | Tables |
|---|---|
| **People** | `users`, `merchants`, `merchant_staff` |
| **Content** | `reels`, `reel_views`, `reel_likes`, `reel_comments` |
| **Rewards** | `coupon_templates`, `user_coupons`, `redemptions_ledger` |
| **Messaging** | `notifications`, `device_tokens` |

---

## 3. Routes

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/login` | Sign-in form (redirects to `/admin/` when already signed in) |
| `POST` | `/admin/login` | Verifies credentials, sets the session cookie, `303` |
| `GET`/`POST` | `/admin/logout` | Clears the cookie, `303` to login |
| `GET` | `/admin/` | Dashboard: 4 operator counters + row count per table |
| `GET` | `/admin/{model_key}` | List view — search, sort, paginate |
| `GET` | `/admin/{model_key}/new` | Create form |
| `POST` | `/admin/{model_key}/new` | Create submit |
| `GET` | `/admin/{model_key}/{pk}` | Detail view |
| `GET` | `/admin/{model_key}/{pk}/edit` | Edit form |
| `POST` | `/admin/{model_key}/{pk}/edit` | Update submit |
| `POST` | `/admin/{model_key}/{pk}/delete` | Delete |
| `GET` | `/admin/static/{filename}` | CSS / JS assets (path-traversal guarded) |

All routes except `/login` and `/static/*` depend on `current_admin` — an anonymous visitor is
bounced to the login form with a `303`, not a JSON `401`.

---

## 4. Authentication & Session

- **Credentials**: `SUPER_ADMIN_IDENTIFIER` (phone) or `SUPER_ADMIN_EMAIL`, matched against
  `SUPER_ADMIN_PASSWORD`. If those do not match, the panel falls back to a `users` row whose
  `role` is `SUPER_ADMIN`, verified with `verify_password` against `password_hash`.
- **Session cookie**: `fyndo_admin_session` — a JWT minted by `create_access_token` carrying
  `scope: "admin_panel"` and `role: "SUPER_ADMIN"`. Attributes: `httpOnly`, `samesite=lax`,
  `path=/admin`, `secure` in production, **8-hour TTL**.
- **Isolation**: the panel does **not** reuse `get_current_user`. A leaked shopper or merchant
  bearer token cannot be replayed against the back office, because the panel only ever reads its
  own cookie and additionally checks the `scope` claim.
- **Open-redirect guard**: the `next` parameter is passed through `_safe_next()`, which only
  accepts targets beginning with `/admin`.

### 4.1 Environment variables

| Variable | Purpose |
|---|---|
| `SUPER_ADMIN_IDENTIFIER` | Master admin phone / login id |
| `SUPER_ADMIN_EMAIL` | Alternate master admin login id |
| `SUPER_ADMIN_PASSWORD` | Master admin password (must be ≥ 10 chars in production) |

In development, when `SUPER_ADMIN_PASSWORD` is unset or too short, the app logs a warning and
generates an ephemeral password for the process. In production it raises at startup instead.

---

## 5. Rendering & htmx behaviour

- **Progressive enhancement**: `list.html` is a full page. When a request carries `HX-Request:
  true`, the list route returns only `partials/table.html`, so search / sort / pagination swap the
  `#table-panel` region in place. Without a swap, the same URL still works as a normal page load.
- **Search**: `hx-get` with `hx-trigger="keyup changed delay:350ms, search"` and `hx-push-url`,
  so the browser URL stays shareable.
- **Navigation**: `redirect_to()` returns an `HX-Redirect` header for htmx requests and a plain
  `303` for full-page posts, so create / update / delete work in both modes.
- **Delete confirmation**: the form posts with `hx-post` and
  `hx-confirm="Delete this row permanently? This cannot be undone."`.
- **Secrets**: columns listed under `secret` (e.g. `users.password_hash`,
  `merchant_staff.pin_hash`, `user_coupons.totp_secret`) are never rendered and never exposed as
  form fields.

---

## 6. Audit trail

Every mutation writes one record through `app/core/audit.py` with `source="admin_panel"`:

| Action | Emitted on |
|---|---|
| `admin.create` | Successful create |
| `admin.update` | Successful update |
| `admin.delete` | Successful delete |

Each record carries the acting `actor_id`, `actor_role=SUPER_ADMIN`, the target table and row id.
Records land in the dedicated `audit.log` stream (see System Architecture §2.6).

---

## 7. Running it

```powershell
# from backend/
python -m uvicorn app.main:app --host 127.0.0.1 --port 5055
# then open http://127.0.0.1:5055/admin/login
```

Sign in with `SUPER_ADMIN_IDENTIFIER` + `SUPER_ADMIN_PASSWORD`.

### 7.1 Verification

Covered by `tests/test_admin_panel.py` (9 tests): anonymous bounce, bad-credential `401`, static
asset serving + traversal guard, dashboard render, htmx partial vs full page, a full
create → detail → search → edit → delete cycle, required-field `422`, htmx delete returning
`HX-Redirect`, and logout clearing the session.

```powershell
python -m pytest tests/test_admin_panel.py -q
```

---

## 8. Extending the panel

1. **Expose a new table** — add a dict to `MODEL_CONFIGS` in `configs.py`. Omitted keys fall back
   to mapper-inferred defaults.
2. **Change what a list shows** — edit that table's `list_columns` / `search_columns`. The first
   entry in `list_columns` becomes the linked cell.
3. **Hide or lock a column** — add it to `secret` (never rendered, never editable) or `readonly`
   (rendered but not editable).
4. **Style** — `static/admin.css` holds the design tokens; the brand accent is `--blue: #0095f6`.
