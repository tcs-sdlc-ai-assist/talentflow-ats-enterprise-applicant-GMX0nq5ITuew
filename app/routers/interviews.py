import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.interview_service import (
    get_interview,
    get_my_interviews,
    list_interviews,
    schedule_interview,
    submit_feedback,
)
from app.services.application_service import get_application, list_applications
from app.services.auth_service import get_all_users, get_users_by_role

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/dashboard/interviews")
async def interviews_list_page(
    request: Request,
    application_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter", "Hiring Manager", "Interviewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    interviews = await list_interviews(db, application_id=application_id)

    return templates.TemplateResponse(
        request,
        "interviews/list.html",
        context={
            "user": user,
            "interviews": interviews,
            "application_id": application_id,
        },
    )


@router.get("/dashboard/interviews/schedule")
async def interview_schedule_form_page(
    request: Request,
    application_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    applications = await list_applications(db)
    interviewers = await get_users_by_role(db, "Interviewer")
    all_users = await get_all_users(db)
    eligible_interviewers = [u for u in all_users if u.role in ["Interviewer", "Hiring Manager", "HR Recruiter", "System Admin"] and u.is_active]

    return templates.TemplateResponse(
        request,
        "interviews/schedule.html",
        context={
            "user": user,
            "applications": applications,
            "interviewers": eligible_interviewers,
            "selected_application_id": application_id,
            "error": None,
        },
    )


@router.post("/dashboard/interviews")
async def interview_schedule_submit(
    request: Request,
    application_id: int = Form(...),
    interviewer_id: int = Form(...),
    scheduled_at: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    from datetime import datetime

    try:
        scheduled_datetime = datetime.fromisoformat(scheduled_at)
    except (ValueError, TypeError):
        applications = await list_applications(db)
        all_users = await get_all_users(db)
        eligible_interviewers = [u for u in all_users if u.role in ["Interviewer", "Hiring Manager", "HR Recruiter", "System Admin"] and u.is_active]

        return templates.TemplateResponse(
            request,
            "interviews/schedule.html",
            context={
                "user": user,
                "applications": applications,
                "interviewers": eligible_interviewers,
                "selected_application_id": application_id,
                "error": "Invalid date/time format. Please use a valid date and time.",
            },
        )

    try:
        interview = await schedule_interview(
            db=db,
            application_id=application_id,
            interviewer_id=interviewer_id,
            scheduled_at=scheduled_datetime,
            user=user,
        )
        logger.info(
            "Interview scheduled: id=%s, application_id=%s, interviewer_id=%s, by user=%s",
            interview.id,
            application_id,
            interviewer_id,
            user.id,
        )
        return RedirectResponse(url="/dashboard/interviews", status_code=302)
    except ValueError as e:
        applications = await list_applications(db)
        all_users = await get_all_users(db)
        eligible_interviewers = [u for u in all_users if u.role in ["Interviewer", "Hiring Manager", "HR Recruiter", "System Admin"] and u.is_active]

        return templates.TemplateResponse(
            request,
            "interviews/schedule.html",
            context={
                "user": user,
                "applications": applications,
                "interviewers": eligible_interviewers,
                "selected_application_id": application_id,
                "error": str(e),
            },
        )


@router.get("/dashboard/interviews/my")
async def my_interviews_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter", "Hiring Manager", "Interviewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    interviews = await get_my_interviews(db, user)

    return templates.TemplateResponse(
        request,
        "interviews/my.html",
        context={
            "user": user,
            "interviews": interviews,
        },
    )


@router.get("/dashboard/interviews/{interview_id}")
async def interview_detail_page(
    request: Request,
    interview_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter", "Hiring Manager", "Interviewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    interview = await get_interview(db, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")

    candidate = None
    job = None
    if interview.application:
        candidate = interview.application.candidate
        job = interview.application.job

    return templates.TemplateResponse(
        request,
        "interviews/feedback_form.html",
        context={
            "user": user,
            "interview": interview,
            "candidate": candidate,
            "job": job,
            "error": None,
            "success": None,
        },
    )


@router.get("/dashboard/interviews/{interview_id}/feedback")
async def interview_feedback_form_page(
    request: Request,
    interview_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter", "Hiring Manager", "Interviewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    interview = await get_interview(db, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")

    if user.role == "Interviewer" and interview.interviewer_id != user.id:
        raise HTTPException(status_code=403, detail="You are not authorized to view this interview feedback form")

    candidate = None
    job = None
    if interview.application:
        candidate = interview.application.candidate
        job = interview.application.job

    return templates.TemplateResponse(
        request,
        "interviews/feedback_form.html",
        context={
            "user": user,
            "interview": interview,
            "candidate": candidate,
            "job": job,
            "error": None,
            "success": None,
        },
    )


@router.post("/dashboard/interviews/{interview_id}/feedback")
async def interview_feedback_submit(
    request: Request,
    interview_id: int,
    feedback_rating: int = Form(...),
    feedback_notes: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter", "Hiring Manager", "Interviewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    interview = await get_interview(db, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")

    candidate = None
    job = None
    if interview.application:
        candidate = interview.application.candidate
        job = interview.application.job

    try:
        notes = feedback_notes.strip() if feedback_notes else None
        updated_interview = await submit_feedback(
            db=db,
            interview_id=interview_id,
            feedback_rating=feedback_rating,
            feedback_notes=notes,
            user=user,
        )
        logger.info(
            "Feedback submitted for interview %s by user %s, rating=%s",
            interview_id,
            user.id,
            feedback_rating,
        )

        refreshed_interview = await get_interview(db, interview_id)
        if refreshed_interview and refreshed_interview.application:
            candidate = refreshed_interview.application.candidate
            job = refreshed_interview.application.job

        return templates.TemplateResponse(
            request,
            "interviews/feedback_form.html",
            context={
                "user": user,
                "interview": refreshed_interview if refreshed_interview else updated_interview,
                "candidate": candidate,
                "job": job,
                "error": None,
                "success": "Feedback submitted successfully!",
            },
        )
    except PermissionError as e:
        return templates.TemplateResponse(
            request,
            "interviews/feedback_form.html",
            context={
                "user": user,
                "interview": interview,
                "candidate": candidate,
                "job": job,
                "error": str(e),
                "success": None,
            },
            status_code=403,
        )
    except ValueError as e:
        return templates.TemplateResponse(
            request,
            "interviews/feedback_form.html",
            context={
                "user": user,
                "interview": interview,
                "candidate": candidate,
                "job": job,
                "error": str(e),
                "success": None,
            },
        )