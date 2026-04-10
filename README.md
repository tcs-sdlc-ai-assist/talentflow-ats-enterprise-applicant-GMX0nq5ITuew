# TalentFlow ATS

An Applicant Tracking System built with Python and FastAPI for managing recruitment workflows including job postings, candidate applications, interviews, and hiring pipelines.

## Tech Stack

- **Backend:** Python 3.11+, FastAPI
- **Database:** SQLite (async via aiosqlite), SQLAlchemy 2.0 (async)
- **Authentication:** JWT (python-jose), bcrypt password hashing
- **Validation:** Pydantic v2
- **Templates:** Jinja2 with Tailwind CSS
- **Testing:** pytest, pytest-asyncio, httpx

## Folder Structure

```
talentflow-ats/
├── app/
│   ├── core/
│   │   ├── config.py          # Pydantic Settings configuration
│   │   ├── database.py        # Async SQLAlchemy engine & session
│   │   └── security.py        # JWT token & password hashing utilities
│   ├── models/
│   │   ├── user.py            # User model (recruiters, hiring managers, admins)
│   │   ├── job.py             # Job posting model
│   │   ├── candidate.py       # Candidate model & candidate_skills association
│   │   ├── application.py     # Application model (links candidates to jobs)
│   │   ├── interview.py       # Interview, InterviewAssignment, InterviewFeedback
│   │   └── audit_log.py       # Audit log for tracking system actions
│   ├── schemas/
│   │   ├── user.py            # User request/response schemas
│   │   ├── job.py             # Job request/response schemas
│   │   ├── candidate.py       # Candidate request/response schemas
│   │   ├── application.py     # Application request/response schemas
│   │   ├── interview.py       # Interview request/response schemas
│   │   └── audit_log.py       # Audit log response schemas
│   ├── services/
│   │   ├── user.py            # User CRUD & business logic
│   │   ├── job.py             # Job CRUD & business logic
│   │   ├── candidate.py       # Candidate CRUD & business logic
│   │   ├── application.py     # Application pipeline logic
│   │   ├── interview.py       # Interview scheduling & feedback logic
│   │   └── audit_log.py       # Audit logging service
│   ├── routers/
│   │   ├── auth.py            # Login, register, token refresh
│   │   ├── users.py           # User management endpoints
│   │   ├── jobs.py            # Job posting endpoints
│   │   ├── candidates.py      # Candidate management endpoints
│   │   ├── applications.py    # Application pipeline endpoints
│   │   └── interviews.py      # Interview scheduling endpoints
│   ├── dependencies/
│   │   └── auth.py            # get_current_user, role-based access dependencies
│   ├── templates/             # Jinja2 HTML templates (Tailwind CSS)
│   └── main.py                # FastAPI app entry point, lifespan, router includes
├── tests/
│   ├── conftest.py            # Shared fixtures (async client, test DB, auth tokens)
│   ├── test_auth.py           # Authentication endpoint tests
│   ├── test_users.py          # User management tests
│   ├── test_jobs.py           # Job posting tests
│   ├── test_candidates.py     # Candidate tests
│   ├── test_applications.py   # Application pipeline tests
│   └── test_interviews.py     # Interview scheduling tests
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
└── README.md                  # This file
```

## User Roles

| Role             | Description                                                        |
|------------------|--------------------------------------------------------------------|
| **Super Admin**  | Full system access. Manages users, settings, and all resources.    |
| **Hiring Manager** | Creates and manages job postings. Reviews applications and makes hiring decisions. |
| **Recruiter**    | Manages candidates, screens applications, and schedules interviews.|
| **Interviewer**  | Views assigned interviews and submits feedback.                    |
| **Viewer**       | Read-only access to jobs, candidates, and application statuses.    |

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd talentflow-ats
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and update values:

```bash
cp .env.example .env
```

Required environment variables:

| Variable              | Description                          | Default                  |
|-----------------------|--------------------------------------|--------------------------|
| `DATABASE_URL`        | SQLite async connection string       | `sqlite+aiosqlite:///./talentflow.db` |
| `SECRET_KEY`          | JWT signing secret (use a strong random string) | `change-me-in-production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token lifetime   | `30`                     |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | JWT refresh token lifetime  | `7`                      |
| `CORS_ORIGINS`        | Comma-separated allowed origins      | `http://localhost:3000`  |
| `ENVIRONMENT`         | Runtime environment                  | `development`            |

### 5. Initialize the Database

The database tables are created automatically on application startup via the lifespan handler. No manual migration step is required for initial setup.

For production or schema changes, use Alembic:

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Generate a migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### 6. Run the Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

Interactive API docs:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

## API Routes Reference

### Authentication

| Method | Path                  | Description              | Auth Required |
|--------|-----------------------|--------------------------|---------------|
| POST   | `/api/auth/register`  | Register a new user      | No            |
| POST   | `/api/auth/login`     | Login and get JWT tokens | No            |
| POST   | `/api/auth/refresh`   | Refresh access token     | Yes           |
| GET    | `/api/auth/me`        | Get current user profile | Yes           |

### Users

| Method | Path                  | Description              | Auth Required | Roles          |
|--------|-----------------------|--------------------------|---------------|----------------|
| GET    | `/api/users`          | List all users           | Yes           | Super Admin    |
| GET    | `/api/users/{id}`     | Get user by ID           | Yes           | Super Admin    |
| PUT    | `/api/users/{id}`     | Update user              | Yes           | Super Admin    |
| DELETE | `/api/users/{id}`     | Deactivate user          | Yes           | Super Admin    |

### Jobs

| Method | Path                  | Description              | Auth Required | Roles                          |
|--------|-----------------------|--------------------------|---------------|--------------------------------|
| POST   | `/api/jobs`           | Create a job posting     | Yes           | Super Admin, Hiring Manager    |
| GET    | `/api/jobs`           | List job postings        | Yes           | All                            |
| GET    | `/api/jobs/{id}`      | Get job details          | Yes           | All                            |
| PUT    | `/api/jobs/{id}`      | Update job posting       | Yes           | Super Admin, Hiring Manager    |
| DELETE | `/api/jobs/{id}`      | Delete job posting       | Yes           | Super Admin                    |

### Candidates

| Method | Path                       | Description              | Auth Required | Roles                              |
|--------|----------------------------|--------------------------|---------------|-------------------------------------|
| POST   | `/api/candidates`          | Create a candidate       | Yes           | Super Admin, Recruiter              |
| GET    | `/api/candidates`          | List candidates          | Yes           | All                                 |
| GET    | `/api/candidates/{id}`     | Get candidate details    | Yes           | All                                 |
| PUT    | `/api/candidates/{id}`     | Update candidate         | Yes           | Super Admin, Recruiter              |
| DELETE | `/api/candidates/{id}`     | Delete candidate         | Yes           | Super Admin                         |

### Applications

| Method | Path                              | Description                    | Auth Required | Roles                              |
|--------|-----------------------------------|--------------------------------|---------------|-------------------------------------|
| POST   | `/api/applications`               | Submit an application          | Yes           | Super Admin, Recruiter              |
| GET    | `/api/applications`               | List applications              | Yes           | All                                 |
| GET    | `/api/applications/{id}`          | Get application details        | Yes           | All                                 |
| PUT    | `/api/applications/{id}`          | Update application             | Yes           | Super Admin, Recruiter, Hiring Manager |
| PUT    | `/api/applications/{id}/stage`    | Move application to next stage | Yes           | Super Admin, Recruiter, Hiring Manager |
| DELETE | `/api/applications/{id}`          | Withdraw application           | Yes           | Super Admin                         |

### Interviews

| Method | Path                                    | Description                  | Auth Required | Roles                              |
|--------|-----------------------------------------|------------------------------|---------------|-------------------------------------|
| POST   | `/api/interviews`                       | Schedule an interview        | Yes           | Super Admin, Recruiter              |
| GET    | `/api/interviews`                       | List interviews              | Yes           | All                                 |
| GET    | `/api/interviews/{id}`                  | Get interview details        | Yes           | All                                 |
| PUT    | `/api/interviews/{id}`                  | Update interview             | Yes           | Super Admin, Recruiter              |
| DELETE | `/api/interviews/{id}`                  | Cancel interview             | Yes           | Super Admin                         |
| POST   | `/api/interviews/{id}/feedback`         | Submit interview feedback    | Yes           | Interviewer                         |
| GET    | `/api/interviews/{id}/feedback`         | Get feedback for interview   | Yes           | All (except Viewer)                 |

## Testing

### Run All Tests

```bash
pytest
```

### Run Tests with Verbose Output

```bash
pytest -v
```

### Run a Specific Test File

```bash
pytest tests/test_auth.py -v
```

### Run Tests with Coverage

```bash
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```

### Test Configuration

Tests use an in-memory SQLite database (`sqlite+aiosqlite://`) to ensure isolation. The test fixtures in `tests/conftest.py` provide:

- **`async_client`** — An `httpx.AsyncClient` configured with the FastAPI test app
- **`db_session`** — An async SQLAlchemy session bound to the test database
- **`auth_headers`** — Pre-authenticated headers with a valid JWT for a test user

All test functions use `@pytest.mark.asyncio` for async test execution.

## Deployment Notes

### Production Checklist

1. **Set a strong `SECRET_KEY`** — Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"`
2. **Set `ENVIRONMENT=production`** — Disables debug mode and verbose error responses
3. **Configure `CORS_ORIGINS`** — Restrict to your frontend domain(s)
4. **Use PostgreSQL** — Replace `DATABASE_URL` with an async PostgreSQL connection string (`postgresql+asyncpg://...`) and install `asyncpg`
5. **Run with Gunicorn + Uvicorn workers:**
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```
6. **Enable HTTPS** — Use a reverse proxy (nginx, Caddy) with TLS termination
7. **Set up database migrations** — Use Alembic for schema versioning in production

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t talentflow-ats .
docker run -p 8000:8000 --env-file .env talentflow-ats
```

## License

Private — All rights reserved.