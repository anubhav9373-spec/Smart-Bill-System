# SmartBill Retail Billing System — Audit Report

**Audit date:** 2026-10-29  
**Scope:** Current working-tree filesystem, Flask routes/templates, static CSS/JavaScript/assets, migrations, and Render deployment readiness.  
**Initial audit safety constraint:** No file was deleted or behavior changed during the audit. After the report was delivered, the user explicitly authorized corrective changes. Secret values were not read or reproduced.

## Executive summary

| Area | Finding | Priority |
|---|---|---|
| Deployment | No `render.yaml`, `Procfile`, or production WSGI dependency is present. `README.md` requires a production WSGI server, while `app.py` only exposes direct `app.run(...)`. | High |
| Source hygiene | `.gitignore` is absent. Local SQLite databases, generated snapshots, cache files, and a temporary runner file are present in the working tree. | High |
| CSS | `base.html` loads both the 5,271-line `style.css` and the 3,340-line `app-redesign.css` globally. The latter explicitly says it overrides the former. This creates a large cascade/maintenance surface. | Medium |
| CSS candidates | Conservative static analysis found 43 selectors in `app-redesign.css`, 191 in `style.css`, and one in `home.css` with no direct textual reference. These are not safe-to-delete without browser coverage because selectors can be used by dynamic markup or responsive states. | Medium |
| JavaScript | `static/js/app.js` is present but is not referenced by current templates. The current base template loads `api.js`; page scripts are loaded per page. | Medium |
| Duplicate assets | Five exact duplicate PNG pairs exist. Duplicate bytes do not prove interchangeable semantics, but they are strong consolidation candidates. | Low |
| Legacy transition | Git shows deleted legacy analytics/home/settings files while new profile/setup/share/login surfaces exist in the working tree. There are no current `/analytics` or `/settings` routes. | Medium |
| Runtime health | Python compilation and Flask app-factory route registration passed. No deletion was performed. | — |

## Evidence and recommendations by file

### Application, configuration, and deployment

| File | Purpose | Issue / evidence | Recommendation |
|---|---|---|---|
| [`app.py`](./app.py) | Flask application factory, SQLAlchemy models, routes, authorization, CSRF, rate limits, invoice and sharing logic. | `create_app()` and all current routes register successfully. The module falls back to local `smartbill.db`; schema auto-creation defaults to true. The `__main__` block uses Flask's development server. | Keep business logic unchanged. For Render, add a production WSGI entrypoint/command and make production schema migration and database settings explicit. Review the fallback/auto-create defaults before deployment. |
| [`requirements.txt`](./requirements.txt) | Python runtime dependencies. | Flask, SQLAlchemy, psycopg, limiter and Alembic are present, but no Gunicorn/other production WSGI server is listed. | Add the selected production WSGI server only as part of an approved deployment change. |
| [`README.md`](./README.md) | Architecture, local setup, production requirements, and acceptance matrix. | Documentation correctly says PostgreSQL, persistent secret, secure cookies, migrations, and a WSGI server are required, but repository deployment files do not implement that instruction. It also contains a visible encoding artifact in “Profile & Settings â†’ Team access”. | Correct the encoding artifact and add the exact Render build/start/migration procedure after deployment decisions are confirmed. |
| [`.env.example`](./.env.example) | Names and safe examples for environment configuration. | It contains variable names only in the audit output; no secret values were exposed. | Keep as a template. Ensure real `.env` files and database files are ignored before deployment. |
| [`alembic.ini`](./alembic.ini) | Alembic configuration. | Present and paired with migrations. | Keep; verify Render runs `alembic upgrade head` before starting the web process. |
| [`migrations/`](./migrations/) | Versioned schema migrations and Alembic environment. | Four migration revisions are present. | Keep; test upgrade from a clean PostgreSQL database and from the existing schema before production. |
| [`start_smartbill.ps1`](./start_smartbill.ps1) | Local Cloudflare Tunnel + Flask launcher. | It is Windows/local-development specific, hard-codes local port 5000 and a local cloudflared path, and is not a Render start command. It also has a broad empty `catch` around state-file cleanup. | Keep for local use, but do not use as Render configuration. Consider logging cleanup failures if this script remains operationally important. |
| [`.vscode/settings.json`](./.vscode/settings.json) | Editor settings. | Local IDE configuration, not deployment configuration. | Keep only if team-shared editor behavior is intended; otherwise document it as local-only. |

### Templates and route surfaces

| File | Purpose | Issue / evidence | Recommendation |
|---|---|---|---|
| [`templates/base.html`](./templates/base.html) | Shared shell, navigation, global CSS, API bootstrap, theme and mobile navigation. | Loads `style.css` and then `app-redesign.css` globally. It loads `api.js`; `app.js` is not loaded. | Keep the shared shell. Treat CSS consolidation and script ownership as a separate, tested refactor. |
| [`templates/home.html`](./templates/home.html) | Public landing page. | Uses `home.css` and current logo assets; no `home.js` reference. | Keep. Confirm unused promotional assets before removing any. |
| [`templates/login.html`](./templates/login.html) | Login screen. | Uses direct CSS links rather than extending `base.html`; this is intentional for the auth surface but duplicates global asset declarations. | Keep behavior. Optionally introduce a dedicated auth base only after visual regression testing. |
| [`templates/setup.html`](./templates/setup.html) | Setup and registration screen. | Same direct CSS pattern as login. | Keep; consider shared auth layout later. |
| [`templates/dashboard.html`](./templates/dashboard.html) | Dashboard KPI/chart view. | Loads external Chart.js from jsDelivr and `dashboard.js`. | Keep feature. Pin/verify the CDN policy or self-host only if deployment CSP/reliability requires it. |
| [`templates/products.html`](./templates/products.html) | Product management view. | Loads `products.js`. | Keep; no orphan script evidence. |
| [`templates/billing.html`](./templates/billing.html) | Billing/cart workflow. | Loads `billing.js` through `extra_js`. | Keep; business-critical surface. |
| [`templates/sales.html`](./templates/sales.html) | Sales history view. | Loads `sales.js`; no current analytics page route. | Keep current sales view. Do not restore/delete legacy analytics assets until product scope is confirmed. |
| [`templates/invoice.html`](./templates/invoice.html) | Invoice rendering and QR sharing. | Loads `qrious.min.js` and `invoice.js`. | Keep; verify QR behavior in deployment with the configured HTTPS public URL. |
| [`templates/profile.html`](./templates/profile.html) | Profile, active shop, team and settings surface. | Replaces the tracked legacy `settings.html` surface in the current worktree. | Keep; verify all role-gated controls against server authorization. |
| [`templates/share.html`](./templates/share.html) | Public invoice share page. | Loads external html2canvas from jsDelivr and a Google font. | Keep feature. Review external dependency availability and CSP before production. |
| [`rendered-home.html`](./rendered-home.html) | Generated/static rendered snapshot of home HTML. | It is not a Flask template and contains hard-coded `/static/...` references. It is not used by current routes. | Candidate for archival or removal after confirming no external preview/demo depends on it. Do not delete before approval. |
| `templates/analytics.html` and `templates/settings.html` | Legacy analytics/settings pages in the last tracked baseline. | Git marks both deleted; current `app.py` has no corresponding routes. | Treat deletion as an already-present working-tree transition, not as a new audit action. Verify history and product requirements before committing the transition. |

### JavaScript

| File | Purpose | Issue / evidence | Recommendation |
|---|---|---|---|
| [`static/js/api.js`](./static/js/api.js) | Shared fetch wrapper, theme/session readiness and user UI updates. | Loaded by `base.html`; active dependency. | Keep. |
| [`static/js/app.js`](./static/js/app.js) | Generic DOMContentLoaded navigation/menu behavior. | No current template contains `app.js`; current navigation behavior is also present inline in `base.html`. | High-confidence orphan candidate. Compare its menu behavior with the inline base script, then remove or wire it deliberately in a separate change. |
| [`static/js/billing.js`](./static/js/billing.js) | Cart, quantity, discount and invoice creation behavior. | Loaded by `billing.html`. | Keep. |
| [`static/js/dashboard.js`](./static/js/dashboard.js) | Dashboard data and chart rendering. | Loaded by `dashboard.html`. | Keep; test Chart.js load failure behavior. |
| [`static/js/invoice.js`](./static/js/invoice.js) | Invoice display and QR share modal behavior. | Loaded by `invoice.html`. | Keep. |
| [`static/js/products.js`](./static/js/products.js) | Product list, filtering and CRUD modal behavior. | Loaded by `products.html`. | Keep. |
| [`static/js/profile.js`](./static/js/profile.js) | Profile, shop switching, staff and settings actions. | Loaded by `profile.html`. | Keep. |
| [`static/js/sales.js`](./static/js/sales.js) | Sales history rendering and filtering. | Loaded by `sales.html`. | Keep. |
| [`static/js/qrious.min.js`](./static/js/qrious.min.js) | QR generation library. | Loaded by `invoice.html`; minified vendor file. | Keep unless a dependency policy chooses another QR implementation. |
| `static/js/analytics.js`, `static/js/home.js`, `static/js/setting.js` | Legacy page scripts in the tracked baseline. | Git marks all three deleted; no current template references them. | No further deletion is recommended now; confirm the legacy transition in git history and product requirements. |

### CSS

| File | Purpose | Issue / evidence | Recommendation |
|---|---|---|---|
| [`static/css/style.css`](./static/css/style.css) | Large core/legacy design system and component styles. | 5,271 lines / 138 KB. It is globally loaded and contains many selectors that the conservative scanner could not find in current static markup. | Do not delete selectors based only on text search. Build a route/viewport screenshot matrix, map selectors to live DOM, then remove in small tested batches. |
| [`static/css/app-redesign.css`](./static/css/app-redesign.css) | New visual system and overrides. | 3,340 lines / 98 KB. File header says it is loaded after the legacy stylesheet; it uses many `!important` overrides and the scanner found 43 unreferenced selector candidates, including sales/profile groups. | Consolidate by component/route only after visual regression tests. Replace overrides incrementally; preserve responsive and dark-theme behavior. |
| [`static/css/home.css`](./static/css/home.css) | Public home-page styles. | 105 lines / 18 KB; `.public-mobile-nav` was not found in current templates/JS by the conservative scan. | Verify whether the selector is dead or reserved for a responsive state before removing it. |

### Static assets

The current filesystem contains a large mix of PNG/SVG branding, icon, feature, preview, and illustration assets. Text search found no direct references for many of them; this is expected for assets that may be referenced by CSS or were prepared for future landing-page sections, so it is not deletion proof.

Exact byte-identical duplicate pairs:

| Hash evidence | Files | Recommendation |
|---|---|---|
| SHA-256 `9E7110...` | `static/assets/smartbill-favicon.png`, `static/assets/smartbill-mark.png` | Confirm semantic naming and references; retain one canonical name only after all consumers are checked. |
| SHA-256 `FFA040...` | `static/assets/icons/analytics.png`, `static/assets/icons/sales-tracking.png` | Confirm whether the same visual is intentional; consolidate only if labels/asset contracts permit it. |
| SHA-256 `87C47F...` | `static/assets/icons/bill.png`, `static/assets/icons/invoice.png` | Same visual duplicate; verify UI meaning before consolidation. |
| SHA-256 `306812...` | `static/assets/icons/easy-sharing.png`, `static/assets/icons/share.png` | Same visual duplicate; verify naming/API consumers. |
| SHA-256 `7E16F6...` | `static/assets/icons/product-management.png`, `static/assets/icons/products.png` | Same visual duplicate; verify naming/API consumers. |

Notable asset families requiring an approval decision rather than automatic deletion:

- Root branding files and `assets/branding/` contain overlapping logo/mark variants.
- `static/assets/icons/` contains PNG and SVG versions of many icons.
- Feature/preview/illustration files appear to be landing-page or design-system resources, but current templates do not reference every item.
- `smartbill.db` was locked by a running process during hashing; it was not modified.

## Generated, local, and repository hygiene findings

| Path | Evidence | Recommendation |
|---|---|---|
| [`smartbill.db`](./smartbill.db) | Local SQLite database, currently in use; untracked. | Never deploy as the production database. Add local DB patterns to `.gitignore`; retain only as local developer data if required. |
| [`smartbill-legacy-outer.db`](./smartbill-legacy-outer.db) | Second local SQLite database; untracked and likely migration/import fixture. | Classify as a fixture or local-only file. Keep outside deployment unless explicitly needed for a tested import workflow. |
| [`all_code.txt`](./all_code.txt) | 249 KB generated code aggregate; untracked. | Candidate for local-only cleanup/ignore after confirming no external handoff depends on it. |
| [`tempCodeRunnerFile.py`](./tempCodeRunnerFile.py) | 833-byte editor-generated temporary Python file; untracked. | Candidate for local-only cleanup/ignore after confirming it is not a fixture. |
| [`__pycache__/`](./__pycache__/) | Python bytecode cache; untracked. | Ignore; never deploy or commit. |
| `.gitignore` | Not present. | Add a reviewed ignore file before committing local DBs, caches, virtual environments, `.env`, generated snapshots, and editor artifacts. This is a recommended hygiene change, not performed in this audit. |

## Render deployment checklist

1. Add a Render-compatible production start command using a WSGI server (for example, an approved Gunicorn command targeting the Flask app factory).
2. Add the WSGI dependency to `requirements.txt`.
3. Configure `DATABASE_URL` to managed PostgreSQL; do not use the SQLite fallback.
4. Run `alembic upgrade head` as a controlled deploy/pre-deploy step.
5. Set a persistent `SMARTBILL_SECRET_KEY`; never commit or print its value.
6. Set `SMARTBILL_SECURE_COOKIES=true`, `FLASK_DEBUG=false`, `SMARTBILL_AUTO_CREATE_SCHEMA=false`, and an appropriate rate-limit storage URI for multi-process deployment.
7. Set `SMARTBILL_PUBLIC_URL` to the exact HTTPS Render/custom domain used for QR links.
8. Configure health checks, logs, backups, and a persistent database independently of static asset deployment.
9. Keep local `.db`, `.env`, cache, generated snapshot, and editor files out of the deployment artifact.

## Corrective changes applied after approval

- Added [`.gitignore`](./.gitignore) for environment files, caches, local databases, generated snapshots, and editor artifacts.
- Added [`render.yaml`](./render.yaml) with PostgreSQL-oriented environment settings, Alembic pre-deploy migration, Gunicorn start command, and a health check.
- Added Gunicorn to [`requirements.txt`](./requirements.txt).
- Documented the Render deployment flow in [`README.md`](./README.md).
- Removed [`static/js/app.js`](./static/js/app.js) because no current template loaded it and its navigation/menu logic was duplicated by the inline script in [`templates/base.html`](./templates/base.html).
- Did not remove duplicate image files or CSS selectors because semantic/UI usage was not sufficiently proven.

## Validation performed

- `python -m py_compile app.py migrations\env.py` — **PASS**
- `python -c "import app; a=app.create_app(); ..."` — **PASS**; current Flask routes registered.
- Exact duplicate hash scan — **5 duplicate PNG pairs identified**.
- Conservative CSS selector scan — candidates reported above; not treated as proof of unused code.
- No business logic or UI behavior was intentionally changed.
- Gunicorn is installed at the declared version. Its executable cannot start on Windows because Gunicorn requires the POSIX-only `fcntl` module; the configured command is intended for Render's Linux runtime.

## Safe next steps requiring approval

1. Confirm whether the current working-tree deletions of legacy analytics/home/settings surfaces are intentional.
2. Confirm whether `rendered-home.html`, `all_code.txt`, `tempCodeRunnerFile.py`, and both SQLite files are needed as fixtures/local artifacts.
3. Approve a deployment-only change for Render WSGI configuration and dependency.
4. Approve a visual-regression-backed CSS consolidation plan.
5. Approve duplicate asset consolidation only after reference and semantic-name checks.
