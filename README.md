# SmartBill

SmartBill is a multi-shop retail billing application with a responsive desktop, tablet and mobile UI.

## Architecture

- Flask web application
- SQLAlchemy 2 models
- PostgreSQL in deployment (`DATABASE_URL`), with SQLite available for local development
- Password-hashed owner accounts and secure sessions
- Tenant isolation: every product, invoice and setting is scoped to its shop
- Server-side invoice totals, stock checks and stock deduction
- CSRF protection on state-changing requests
- Expiring, random-token public invoice sharing
- Login/registration rate limits and baseline security headers
- JSON backup export and validated legacy data import
- Alembic migration scaffold for controlled schema changes
- Shop memberships with owner, manager, cashier and staff roles
- Server-side role authorization for products, settings, billing actions, backups and imports
- Active-shop switching with membership validation and tenant-scoped APIs
- Transaction-safe invoice numbering and stock row locks on supported databases
- Audit events for staff, product, settings and invoice security actions
- Safe JSON errors for unknown API routes and unexpected server failures
- Account lockout after repeated failed sign-ins and session invalidation after password changes

## Local setup

1. Create a virtual environment and install dependencies:

   ```text
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install -r requirements.txt
   ```

2. For PostgreSQL, copy `.env.example` to `.env` and provide a real `DATABASE_URL` and long `SMARTBILL_SECRET_KEY`.

3. For a quick local smoke run without PostgreSQL, leave `DATABASE_URL` unset. The app uses `smartbill.db` locally.

4. Start the app:

   ```text
   python app.py
   ```

5. Open `http://127.0.0.1:5000`. The first visit opens the setup wizard. New shops can later register at `/register`.

### Render deployment

The repository includes [`render.yaml`](./render.yaml) for a production web service. Create a
managed PostgreSQL database and set the `DATABASE_URL`, `SMARTBILL_SECRET_KEY`,
`SMARTBILL_PUBLIC_URL`, and `RATELIMIT_STORAGE_URI` values in Render's environment.
The deployment runs `alembic upgrade head` before starting Gunicorn. Keep
`SMARTBILL_AUTO_CREATE_SCHEMA=false` in production and never upload local SQLite databases.

### Invoice QR sharing

QR links contain a random, expiring token and do not expose invoice data in the URL. To open a QR link from a phone using 4G/5G, the app must be deployed behind a public HTTPS domain (or a temporary HTTPS tunnel during development). Set that exact public origin before starting the app:

```text
SMARTBILL_PUBLIC_URL=https://billing.example.com
```

`127.0.0.1`, `localhost`, and a private LAN address are only reachable from the same device/network; they cannot work over mobile data. The app rejects non-HTTPS public origins outside local development.

For repeatable local testing across 4G, 5G, and different Wi-Fi networks, install Cloudflare Tunnel and run:

```powershell
.\start_smartbill.ps1
```

This starts a temporary HTTPS tunnel, detects its URL, and launches Flask as detached background processes. You can close VS Code after the script prints the URL; the app keeps running until you stop the saved processes or start the script again. The URL changes when the temporary tunnel is restarted, so always open the URL printed by the script and generate a fresh QR code.

## Production requirements

- Use PostgreSQL, not the local SQLite fallback.
- Set a persistent `SMARTBILL_SECRET_KEY`.
- Set `SMARTBILL_SECURE_COOKIES=true` behind HTTPS.
- Keep `FLASK_DEBUG=false`.
- Run behind a production WSGI server and reverse proxy.
- Configure automated PostgreSQL backups and database migrations before schema changes.
- Apply schema changes with `alembic upgrade head` after configuring `DATABASE_URL`.
- Use a shared rate-limit store such as Redis by setting `RATELIMIT_STORAGE_URI` in multi-process production.
- Use `SMARTBILL_AUTO_CREATE_SCHEMA=true` only for quick local development; production should use Alembic migrations with it set to `false`.
- Set `SMARTBILL_LOG_LEVEL=INFO` (or `WARNING` in quieter deployments) and collect application logs centrally.
- Run `alembic upgrade head` to create the `shop_memberships` table and backfill each existing account as an owner.

## Team roles

Owners can add team members from **Profile & Settings → Team access**. The server enforces these roles:

- **Owner**: full shop administration, backups, imports and team management
- **Manager**: products, settings, sales and invoice administration
- **Cashier**: billing and secure invoice sharing
- **Staff**: read-only access to the operational screens

Role checks are enforced in the API, so hiding a button in the browser cannot bypass authorization.

Users with more than one shop membership can switch the active shop from **Profile & Settings → Active shop**. The switch endpoint validates membership before changing the session, and all private product, invoice, dashboard and settings queries use the selected shop.

Operational hardening is included in the latest migration. It adds audit events and a per-shop invoice-number uniqueness constraint. Apply it with:

```text
alembic upgrade head
```

Five consecutive failed sign-in attempts temporarily lock an account for 15 minutes. A successful password change invalidates the current session and requires a fresh sign-in. Password reset email delivery is intentionally deployment-specific; connect a verified transactional email provider before exposing a reset-token workflow.

## Responsive acceptance matrix

The current UI has been checked for horizontal overflow at 320, 360, 390, 414, 768, 820, 1024, 1366 and 1440 pixels on the home, dashboard, products, billing, sales and profile routes. Keep this matrix in the release checklist when changing layout or tables.
