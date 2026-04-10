import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import Base, engine, async_session
from app.routers import auth, landing, dashboard, jobs, candidates, applications, interviews

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting TalentFlow ATS...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")

    async with async_session() as session:
        try:
            from app.services.auth_service import create_default_admin

            await create_default_admin(session)
            await session.commit()
            logger.info("Default admin user check completed")
        except Exception:
            await session.rollback()
            logger.exception("Error during startup admin creation")

    yield

    await engine.dispose()
    logger.info("TalentFlow ATS shutdown complete")


app = FastAPI(
    title="TalentFlow ATS",
    description="Applicant Tracking System built with FastAPI",
    version="1.0.0",
    lifespan=lifespan,
)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(auth.router)
app.include_router(landing.router)
app.include_router(dashboard.router)
app.include_router(jobs.router)
app.include_router(candidates.router)
app.include_router(applications.router)
app.include_router(interviews.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}