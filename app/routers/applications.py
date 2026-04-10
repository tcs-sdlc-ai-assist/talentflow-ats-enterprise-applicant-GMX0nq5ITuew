import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.application import ALLOWED_TRANSITIONS
from app.services.application_service import (
    create_application,
    get_application,
    get_kanban,
    list_applications,
    update_status,
)
from app.services.candidate_service import list_candidates
from app.services.job_service import get_job, list_jobs

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/dashboard/applications")
async def applications_list_page(
    request: Request,
    status: Optional[str] = None,
    job_id: Optional[int] = None,
    candidate_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter", "Hiring Manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        applications = await list_applications(
            db=db,
            status_filter=status,
            job_id=job_id,
            candidate_id=candidate_id,
        )
    except Exception:
        logger.exception("Error listing applications")
        applications = []

    return templates.TemplateResponse(
        request,
        "applications/list.html",
        context={
            "user": user,
            "applications": applications,
            "status_filter": status,
        },
    )


@router.get("/dashboard/applications/create")
async def application_create_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    jobs_list, _ = await list_jobs(db=db, status="Published")
    candidates_list, _ = await list_candidates(db=db)

    return templates.TemplateResponse(
        request,
        "applications/create.html",
        context={
            "user": user,
            "jobs": jobs_list,
            "candidates": candidates_list,
            "error": None,
        },
    )


@router.post("/dashboard/applications")
async def application_create(
    request: Request,
    job_id: int = Form(...),
    candidate_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        application = await create_application(
            db=db,
            job_id=job_id,
            candidate_id=candidate_id,
            user=user,
        )
        return RedirectResponse(
            url=f"/dashboard/applications/{application.id}",
            status_code=302,
        )
    except ValueError as e:
        logger.warning("Application creation failed: %s", str(e))
        jobs_list, _ = await list_jobs(db=db, status="Published")
        candidates_list, _ = await list_candidates(db=db)
        return templates.TemplateResponse(
            request,
            "applications/create.html",
            context={
                "user": user,
                "jobs": jobs_list,
                "candidates": candidates_list,
                "error": str(e),
            },
        )
    except Exception:
        logger.exception("Unexpected error creating application")
        jobs_list, _ = await list_jobs(db=db, status="Published")
        candidates_list, _ = await list_candidates(db=db)
        return templates.TemplateResponse(
            request,
            "applications/create.html",
            context={
                "user": user,
                "jobs": jobs_list,
                "candidates": candidates_list,
                "error": "An unexpected error occurred. Please try again.",
            },
        )


@router.get("/dashboard/applications/{application_id}")
async def application_detail_page(
    request: Request,
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter", "Hiring Manager", "Interviewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    application = await get_application(db=db, application_id=application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    allowed_transitions = ALLOWED_TRANSITIONS.get(application.status, [])

    interviews = application.interviews if application.interviews else []

    can_update_status = user.role in ["System Admin", "HR Recruiter", "Hiring Manager"]

    return templates.TemplateResponse(
        request,
        "applications/detail.html",
        context={
            "user": user,
            "application": application,
            "allowed_transitions": allowed_transitions if can_update_status else [],
            "interviews": interviews,
        },
    )


@router.post("/dashboard/applications/{application_id}/status")
async def application_update_status(
    request: Request,
    application_id: int,
    status: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter", "Hiring Manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        await update_status(
            db=db,
            application_id=application_id,
            new_status=status,
            user=user,
        )
    except ValueError as e:
        logger.warning(
            "Application status update failed: application_id=%s, error=%s",
            application_id,
            str(e),
        )
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception(
            "Unexpected error updating application status: application_id=%s",
            application_id,
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while updating the application status.",
        )

    referer = request.headers.get("referer", "")
    if "pipeline" in referer:
        application = await get_application(db=db, application_id=application_id)
        if application is not None:
            return RedirectResponse(
                url=f"/dashboard/jobs/{application.job_id}/pipeline",
                status_code=302,
            )

    return RedirectResponse(
        url=f"/dashboard/applications/{application_id}",
        status_code=302,
    )


@router.get("/dashboard/jobs/{job_id}/pipeline")
async def job_pipeline_page(
    request: Request,
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter", "Hiring Manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    job = await get_job(db=db, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        pipeline = await get_kanban(db=db, job_id=job_id)
    except ValueError as e:
        logger.warning("Error fetching pipeline for job %s: %s", job_id, str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("Unexpected error fetching pipeline for job %s", job_id)
        pipeline = {}

    return templates.TemplateResponse(
        request,
        "applications/pipeline.html",
        context={
            "user": user,
            "job": job,
            "pipeline": pipeline,
        },
    )