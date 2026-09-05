# Deploying Shopping AI to Railway

## Prerequisites

- Railway account (railway.app) — Hobby plan ($5/month) is sufficient
- GitHub repository connected to Railway
- Local `.env` file with all required variables (see `.env.example`)

---

## Step 1 — Create a Railway project

1. Go to railway.app → **New Project**
2. Select **Deploy from GitHub repo**
3. Choose the `shopping-ai` repository
4. Railway auto-detects `railway.json` and uses it for build/start

---

## Step 2 — Provision a PostgreSQL database

1. Inside your Railway project, click **+ New Service**
2. Select **Database → PostgreSQL**
3. Railway creates a managed Postgres instance and injects `DATABASE_URL` into the environment automatically
4. The variable name is `DATABASE_URL` — this matches what the app expects

**Do not set DATABASE_URL manually.** Use Railway's reference variable:

In your web service environment variables, add:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

Railway resolves this at deploy time. The app reads it via `pydantic-settings`.

---

## Step 3 — Set required environment variables

In **Project → web service → Variables**, add:

| Variable | Value | Notes |
|---|---|---|
| `SECRET_KEY` | generate with `openssl rand -hex 32` | Required. No default. App refuses to start without it. |
| `EBAY_APP_ID` | from developer.ebay.com | Leave blank until eBay account created |
| `EBAY_CERT_ID` | from developer.ebay.com | Leave blank until eBay account created |
| `EBAY_ENVIRONMENT` | `production` | Set to `sandbox` while testing collector |
| `ANTHROPIC_API_KEY` | from console.anthropic.com | Required for AI search features |
| `COLLECTOR_WRITES_ENABLED` | `true` | Defaults false. Collector is read-only until explicitly set. |

`DATABASE_URL` is provided automatically by the Postgres service — do not set it manually.

---

## Step 4 — Deploy

1. Push to `main` branch — Railway triggers a build automatically
2. Build runs: `pip install -r backend/requirements.txt`
3. Start command runs: `alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
4. Alembic applies all pending migrations before uvicorn starts
5. Railway health-checks `GET /health` — must return `{"status": "ok"}`

---

## Step 5 — Post-deploy verification

After deployment succeeds, open the Railway-assigned domain (shown in the service panel):

```bash
# Health check
curl https://your-app.railway.app/health

# API version
curl https://your-app.railway.app/

# Search (should return 20 products)
curl "https://your-app.railway.app/api/v1/search?q=Sony"
```

Expected responses:
- `/health` → `{"status": "ok"}`
- `/` → `{"message": "Shopping AI API", "version": "0.4.0", ...}`
- `/api/v1/search?q=Sony` → JSON with `total` > 0 and `results` array

---

## Step 6 — Database migrations

Migrations run automatically at startup via `alembic upgrade head` in the start command.

To run manually (e.g. after a schema change):

```bash
# From Railway CLI
railway run alembic upgrade head

# Or trigger a redeploy — migrations run before uvicorn starts
```

To generate a new migration after changing a SQLAlchemy model:

```bash
# Local (uses SQLite)
alembic revision --autogenerate -m "describe the change"

# Review the generated file in alembic/versions/ before committing
```

---

## Troubleshooting

**App fails to start:**
- Check that `SECRET_KEY` is set in Railway environment variables
- Check that `DATABASE_URL` is properly referenced from the Postgres service
- View logs in Railway dashboard → Deployments → most recent → View Logs

**`alembic upgrade head` fails:**
- Ensure `DATABASE_URL` points to the Postgres instance (not SQLite)
- Check that `alembic/versions/` contains the baseline migration
- Run `alembic history` locally against the production URL to inspect state

**`from backend.app` ImportError:**
- The start command uses `uvicorn backend.app.main:app` (not `app.main:app`)
- The working directory must be the project root (`/app` in Railway's Nixpacks build)
- `railway.json` build command installs from `backend/requirements.txt` — confirm the path

**`pydantic_settings.SecretsDirectorySettingsSource` error or similar:**
- Ensure `pydantic-settings>=2.0.0` is in `backend/requirements.txt`

---

## Estimated monthly cost (Hobby plan)

| Service | Cost |
|---|---|
| Web service (backend) | ~$5.00 |
| PostgreSQL | ~$0.15 (minimal usage) |
| Collector Cron (future) | ~$0.08 |
| **Total** | **~$5.23** |

Pricing is usage-based. Idle services cost less.
