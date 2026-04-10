import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.job_service import list_published_jobs

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/")
async def landing_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user(request, db)

    try:
        jobs = await list_published_jobs(db)
    except Exception:
        logger.exception("Error fetching published jobs for landing page")
        jobs = []

    from datetime import datetime

    current_year = datetime.utcnow().year

    return templates.TemplateResponse(
        request,
        "landing.html",
        context={
            "user": user,
            "jobs": jobs,
            "current_year": current_year,
        },
    )