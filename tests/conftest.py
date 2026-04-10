import asyncio
import logging
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.user import User
from app.models.job import Job
from app.models.candidate import Candidate, candidate_skills, Skill
from app.models.application import Application
from app.models.interview import Interview, InterviewFeedback
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

test_async_session = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        username="testadmin",
        email="testadmin@talentflow.local",
        password_hash=hash_password("adminpass123"),
        full_name="Test Admin",
        role="System Admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def recruiter_user(db_session: AsyncSession) -> User:
    user = User(
        username="testrecruiter",
        email="testrecruiter@talentflow.local",
        password_hash=hash_password("recruiterpass123"),
        full_name="Test Recruiter",
        role="HR Recruiter",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def hiring_manager_user(db_session: AsyncSession) -> User:
    user = User(
        username="testhiringmgr",
        email="testhiringmgr@talentflow.local",
        password_hash=hash_password("hiringmgrpass123"),
        full_name="Test Hiring Manager",
        role="Hiring Manager",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def interviewer_user(db_session: AsyncSession) -> User:
    user = User(
        username="testinterviewer",
        email="testinterviewer@talentflow.local",
        password_hash=hash_password("interviewerpass123"),
        full_name="Test Interviewer",
        role="Interviewer",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user(db_session: AsyncSession) -> User:
    user = User(
        username="inactiveuser",
        email="inactive@talentflow.local",
        password_hash=hash_password("inactivepass123"),
        full_name="Inactive User",
        role="Interviewer",
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


async def _login_user(client: AsyncClient, username: str, password: str) -> AsyncClient:
    response = await client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )
    if response.status_code in (302, 303):
        cookies = response.cookies
        for key, value in cookies.items():
            client.cookies.set(key, value)
    return client


@pytest_asyncio.fixture
async def admin_client(async_client: AsyncClient, admin_user: User) -> AsyncClient:
    return await _login_user(async_client, "testadmin", "adminpass123")


@pytest_asyncio.fixture
async def recruiter_client(async_client: AsyncClient, recruiter_user: User) -> AsyncClient:
    return await _login_user(async_client, "testrecruiter", "recruiterpass123")


@pytest_asyncio.fixture
async def hiring_manager_client(async_client: AsyncClient, hiring_manager_user: User) -> AsyncClient:
    return await _login_user(async_client, "testhiringmgr", "hiringmgrpass123")


@pytest_asyncio.fixture
async def interviewer_client(async_client: AsyncClient, interviewer_user: User) -> AsyncClient:
    return await _login_user(async_client, "testinterviewer", "interviewerpass123")


@pytest_asyncio.fixture
async def sample_job(db_session: AsyncSession, hiring_manager_user: User) -> Job:
    job = Job(
        title="Senior Backend Engineer",
        department="Engineering",
        location="Remote",
        type="Full-Time",
        salary_min=120000,
        salary_max=180000,
        description="We are looking for a senior backend engineer to join our team.",
        status="Published",
        hiring_manager_id=hiring_manager_user.id,
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def sample_candidate(db_session: AsyncSession) -> Candidate:
    candidate = Candidate(
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        phone="+1-555-0100",
        linkedin_url="https://linkedin.com/in/janedoe",
        resume_text="Experienced software engineer with 10 years of experience in Python and FastAPI.",
    )
    db_session.add(candidate)
    await db_session.flush()
    await db_session.refresh(candidate)
    return candidate


@pytest_asyncio.fixture
async def sample_application(
    db_session: AsyncSession,
    sample_job: Job,
    sample_candidate: Candidate,
) -> Application:
    application = Application(
        job_id=sample_job.id,
        candidate_id=sample_candidate.id,
        status="Applied",
    )
    db_session.add(application)
    await db_session.flush()
    await db_session.refresh(application)
    return application


@pytest_asyncio.fixture
async def sample_interview(
    db_session: AsyncSession,
    sample_application: Application,
    interviewer_user: User,
) -> Interview:
    from datetime import datetime, timedelta

    interview = Interview(
        application_id=sample_application.id,
        interviewer_id=interviewer_user.id,
        scheduled_at=datetime.utcnow() + timedelta(days=3),
    )
    db_session.add(interview)
    await db_session.flush()
    await db_session.refresh(interview)
    return interview