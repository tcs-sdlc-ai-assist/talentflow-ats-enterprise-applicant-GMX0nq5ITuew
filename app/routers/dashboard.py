import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/dashboard")
async def dashboard_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    try:
        service = DashboardService(db)
        dashboard_data = await service.get_dashboard_data(user.id, user.role)
    except Exception:
        logger.exception("Error loading dashboard data for user id=%s role=%s", user.id, user.role)
        dashboard_data = {
            "metrics": {
                "open_positions": 0,
                "active_candidates": 0,
                "time_to_hire": 0,
                "pending_interviews": 0,
            },
            "recent_audit_logs": [],
            "pending_items": [],
        }

    context = {
        "user": user,
    }
    context.update(dashboard_data)

    return templates.TemplateResponse(request, "dashboard/index.html", context=context)