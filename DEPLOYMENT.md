# TalentFlow ATS — Deployment Guide

## Table of Contents

- [Overview](#overview)
- [Local Development Setup](#local-development-setup)
- [Environment Variables](#environment-variables)
- [Database Configuration](#database-configuration)
- [Alembic Migrations](#alembic-migrations)
- [Vercel Deployment](#vercel-deployment)
- [CI/CD Notes](#cicd-notes)
- [Troubleshooting](#troubleshooting)

---

## Overview

TalentFlow ATS is a Python FastAPI application that can be deployed to Vercel as a serverless function. The application uses SQLite for local development and PostgreSQL for production deployments.

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- pip or uv package manager
- Git

### Steps

```bash
# Clone the repository
git clone <repository-url>
cd talentflow-ats

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your local settings

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at `http://localhost:8000`.

---

## Environment Variables

Create a `.env` file in the project root with the following variables:

### Required Variables

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Secret key for JWT token signing. Must be a long random string. | `your-super-secret-key-change-in-production` |
| `DATABASE_URL` | Database connection string. | `sqlite+aiosqlite:///./talentflow.db` |

### Optional Variables

| Variable | Description | Default |
|---|---|---|
| `ENVIRONMENT` | Runtime environment (`development`, `staging`, `production`). | `development` |
| `DEBUG` | Enable debug mode. | `false` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token expiry in minutes. | `30` |
| `CORS_ORIGINS` | Comma-separated list of allowed CORS origins. | `http://localhost:3000,http://localhost:8000` |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). | `INFO` |

### Example `.env` File

```env
# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=change-this-to-a-random-secret-key-at-least-32-chars

# Database
DATABASE_URL=sqlite+aiosqlite:///./talentflow.db

# Auth
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Logging
LOG_LEVEL=DEBUG
```

### Generating a Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## Database Configuration

### Local Development (SQLite)

For local development, SQLite with `aiosqlite` is used:

```env
DATABASE_URL=sqlite+aiosqlite:///./talentflow.db
```

This creates a `talentflow.db` file in the project root. No additional database setup is required.

### Production (PostgreSQL)

For production deployments, use PostgreSQL with `asyncpg`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/talentflow
```

#### Recommended PostgreSQL Providers

| Provider | Notes |
|---|---|
| **Neon** | Serverless PostgreSQL, generous free tier, excellent for Vercel deployments. |
| **Supabase** | PostgreSQL with built-in auth and APIs. Free tier available. |
| **Railway** | Simple PostgreSQL hosting with automatic backups. |
| **AWS RDS** | Managed PostgreSQL for larger-scale deployments. |
| **Render** | Free PostgreSQL instances (90-day expiry on free tier). |

#### Neon Setup (Recommended for Vercel)

1. Create an account at [neon.tech](https://neon.tech).
2. Create a new project and database.
3. Copy the connection string from the dashboard.
4. Replace the protocol prefix: change `postgresql://` to `postgresql+asyncpg://`.
5. Set the modified connection string as `DATABASE_URL` in your environment.

```env
# Neon connection string (with asyncpg driver)
DATABASE_URL=postgresql+asyncpg://user:password@ep-cool-name-123456.us-east-2.aws.neon.tech/talentflow?sslmode=require
```

#### Connection Pooling Notes

For serverless environments like Vercel, connection pooling is critical:

- **Neon**: Use the pooled connection string (port 5432 with `-pooler` suffix in hostname).
- **Supabase**: Use the connection pooler URL (port 6543).
- Configure pool size in the application via SQLAlchemy engine options:

```python
# These are typically set in app/core/database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,          # Max persistent connections
    max_overflow=10,      # Additional connections under load
    pool_timeout=30,      # Seconds to wait for a connection
    pool_recycle=1800,    # Recycle connections after 30 minutes
)
```

---

## Alembic Migrations

### Initial Setup

Alembic is used for database schema migrations.

```bash
# Initialize Alembic (already done if alembic/ directory exists)
alembic init alembic

# Generate a migration from model changes
alembic revision --autogenerate -m "describe your changes"

# Apply all pending migrations
alembic upgrade head

# Rollback the last migration
alembic downgrade -1

# View migration history
alembic history --verbose

# View current migration state
alembic current
```

### Alembic Configuration

Ensure `alembic.ini` has the correct `sqlalchemy.url` or that `alembic/env.py` reads from the environment:

```python
# alembic/env.py — recommended approach
import os
from dotenv import load_dotenv

load_dotenv()

config = context.config

# Override sqlalchemy.url with environment variable
database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./talentflow.db")

# For Alembic (synchronous), convert async URLs to sync equivalents
database_url_sync = database_url.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg2")
config.set_main_option("sqlalchemy.url", database_url_sync)
```

### Migration Best Practices

1. **Always review auto-generated migrations** before applying them. Alembic may miss certain changes (e.g., renaming columns vs. dropping and recreating).
2. **Test migrations locally** against a copy of the production database schema before deploying.
3. **Never edit applied migrations.** Create a new migration to fix issues.
4. **Include migrations in version control.** The `alembic/versions/` directory should be committed.

### Running Migrations in Production

Before deploying a new version with schema changes:

```bash
# Set the production DATABASE_URL (sync version for Alembic CLI)
export DATABASE_URL=postgresql+psycopg2://user:password@host:5432/talentflow

# Apply migrations
alembic upgrade head
```

Alternatively, add a migration step to your CI/CD pipeline (see [CI/CD Notes](#cicd-notes)).

---

## Vercel Deployment

### Project Structure for Vercel

Vercel deploys FastAPI applications as serverless functions. The key configuration file is `vercel.json`.

### `vercel.json` Configuration

Create a `vercel.json` file in the project root:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/app/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ],
  "env": {
    "ENVIRONMENT": "production"
  }
}
```

### Deployment Steps

#### 1. Install Vercel CLI

```bash
npm install -g vercel
```

#### 2. Login to Vercel

```bash
vercel login
```

#### 3. Configure Environment Variables

Set environment variables in the Vercel dashboard or via CLI:

```bash
# Required
vercel env add SECRET_KEY production
vercel env add DATABASE_URL production

# Optional
vercel env add ENVIRONMENT production
vercel env add CORS_ORIGINS production
vercel env add LOG_LEVEL production
```

**Important:** Set `DATABASE_URL` to a PostgreSQL connection string for production. SQLite does not persist across serverless function invocations on Vercel.

#### 4. Deploy

```bash
# Preview deployment
vercel

# Production deployment
vercel --prod
```

#### 5. Verify

Visit the deployment URL and check:

- `https://your-app.vercel.app/` — Application root
- `https://your-app.vercel.app/docs` — Swagger API documentation
- `https://your-app.vercel.app/redoc` — ReDoc API documentation

### Vercel-Specific Considerations

| Consideration | Details |
|---|---|
| **Serverless Function Size** | Max 250 MB (compressed). Keep dependencies minimal. |
| **Execution Timeout** | 10 seconds (Hobby), 60 seconds (Pro), 900 seconds (Enterprise). |
| **No Persistent Filesystem** | SQLite files are ephemeral. Use PostgreSQL for production. |
| **Cold Starts** | First request after idle may be slower. Keep the function warm if needed. |
| **Python Version** | Vercel uses Python 3.12 by default. Specify in `runtime.txt` if needed. |

### Specifying Python Version

Create a `runtime.txt` in the project root:

```
python-3.11
```

### Static Files

If serving static files (CSS, JS, images), place them in `app/static/` and ensure the `vercel.json` routes configuration handles them (see above).

---

## CI/CD Notes

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run linting
        run: |
          pip install ruff
          ruff check app/

      - name: Run tests
        env:
          SECRET_KEY: test-secret-key-for-ci
          DATABASE_URL: sqlite+aiosqlite:///./test.db
          ENVIRONMENT: testing
        run: |
          pytest tests/ -v --tb=short

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: "--prod"
```

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `VERCEL_TOKEN` | Vercel personal access token (Settings → Tokens). |
| `VERCEL_ORG_ID` | Found in `.vercel/project.json` after `vercel link`. |
| `VERCEL_PROJECT_ID` | Found in `.vercel/project.json` after `vercel link`. |

### Pre-Deployment Migration Script

For automated migrations in CI/CD, add a step before deployment:

```yaml
- name: Run database migrations
  env:
    DATABASE_URL: ${{ secrets.PRODUCTION_DATABASE_URL }}
  run: |
    pip install alembic psycopg2-binary
    alembic upgrade head
```

---

## Troubleshooting

### Common Issues

#### 1. `ModuleNotFoundError: No module named 'app'`

**Cause:** Python cannot find the `app` package.

**Fix:** Ensure `app/__init__.py` exists and that `vercel.json` points to the correct entry point (`app/main.py`).

#### 2. `sqlalchemy.exc.OperationalError: unable to open database file`

**Cause:** SQLite file path is invalid or the filesystem is read-only (Vercel serverless).

**Fix:** Use PostgreSQL for production. Set `DATABASE_URL` to a PostgreSQL connection string.

#### 3. `ImportError: email-validator is not installed`

**Cause:** A Pydantic schema uses `EmailStr` but `email-validator` is not in `requirements.txt`.

**Fix:** Add `email-validator` to `requirements.txt` and redeploy.

#### 4. `MissingGreenlet: greenlet_spawn has not been called`

**Cause:** Lazy loading a SQLAlchemy relationship inside an async context.

**Fix:** Add `lazy="selectin"` to all `relationship()` declarations, or use `selectinload()` in queries.

#### 5. `Connection refused` or `timeout` to PostgreSQL

**Cause:** Database is not accessible from the deployment environment.

**Fix:**
- Verify the `DATABASE_URL` is correct.
- Ensure the database allows connections from Vercel's IP ranges (or use `0.0.0.0/0` for serverless).
- Check SSL requirements: append `?sslmode=require` to the connection string if needed.

#### 6. `422 Unprocessable Entity` on form submissions

**Cause:** Form field names in the HTML template do not match the FastAPI `Form()` parameter names.

**Fix:** Ensure every `<input name="X">` in templates has a corresponding `X: str = Form(...)` in the route handler.

#### 7. Vercel deployment fails with `Build exceeded maximum allowed size`

**Cause:** Dependencies are too large (common with ML libraries).

**Fix:**
- Remove unused dependencies from `requirements.txt`.
- Use lighter alternatives where possible.
- Consider moving heavy processing to a separate API service.

#### 8. `TypeError: unhashable type: 'dict'` from TemplateResponse

**Cause:** Using the old Starlette `TemplateResponse` API.

**Fix:** Use the new API format:
```python
templates.TemplateResponse(request, "template.html", context={"key": value})
```

#### 9. Cold start timeouts on Vercel

**Cause:** The serverless function takes too long to initialize.

**Fix:**
- Minimize top-level imports.
- Use lazy initialization for heavy resources.
- Consider upgrading to Vercel Pro for longer timeouts.

#### 10. CORS errors in the browser

**Cause:** The frontend origin is not in the allowed CORS origins list.

**Fix:** Add the frontend URL to the `CORS_ORIGINS` environment variable:
```env
CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000
```

### Checking Logs

#### Local Development

Logs are printed to stdout. Set `LOG_LEVEL=DEBUG` for verbose output.

#### Vercel

View function logs in the Vercel dashboard:

1. Go to your project → **Deployments** → select a deployment.
2. Click **Functions** tab.
3. Click on a function invocation to see logs.

Or use the CLI:

```bash
vercel logs your-app.vercel.app
```

### Health Check

The application exposes a health check endpoint:

```bash
curl https://your-app.vercel.app/health
# Expected: {"status": "healthy"}
```

Use this endpoint for uptime monitoring services.

---

## Security Checklist

Before deploying to production, verify:

- [ ] `SECRET_KEY` is a unique, random string (at least 32 characters).
- [ ] `DEBUG` is set to `false`.
- [ ] `CORS_ORIGINS` contains only trusted origins (not `*`).
- [ ] `DATABASE_URL` uses SSL (`?sslmode=require`) for PostgreSQL.
- [ ] All default/test passwords have been changed.
- [ ] Rate limiting is configured for authentication endpoints.
- [ ] HTTPS is enforced (Vercel handles this automatically).
- [ ] Environment variables are set via Vercel dashboard, not committed to the repository.
- [ ] `.env` is listed in `.gitignore`.