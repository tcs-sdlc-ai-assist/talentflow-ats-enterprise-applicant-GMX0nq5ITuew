import logging
import math
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.candidate_service import (
    create_candidate,
    edit_candidate,
    get_candidate,
    list_candidates,
    get_all_skills,
)
from app.services.application_service import list_applications
from app.services.audit_service import log_action

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/dashboard/candidates")
async def candidates_list_page(
    request: Request,
    search: Optional[str] = None,
    skill: Optional[str] = None,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if page < 1:
        page = 1

    per_page = 20

    candidates, total = await list_candidates(
        db=db,
        search=search if search else None,
        skill_name=skill if skill else None,
        page=page,
        per_page=per_page,
    )

    total_pages = max(1, math.ceil(total / per_page))

    all_skills = await get_all_skills(db)

    return templates.TemplateResponse(
        request,
        "candidates/list.html",
        context={
            "user": user,
            "candidates": candidates,
            "search": search,
            "selected_skill": skill,
            "skills": all_skills,
            "current_page": page,
            "total_pages": total_pages,
            "total": total,
        },
    )


@router.get("/dashboard/candidates/create")
async def candidates_create_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return templates.TemplateResponse(
        request,
        "candidates/form.html",
        context={
            "user": user,
            "candidate": None,
            "error": None,
        },
    )


@router.post("/dashboard/candidates")
async def candidates_create(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    linkedin_url: str = Form(""),
    skills: str = Form(""),
    resume_text: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    skill_names = None
    if skills and skills.strip():
        skill_names = [s.strip() for s in skills.split(",") if s.strip()]

    try:
        candidate = await create_candidate(
            db=db,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone if phone and phone.strip() else None,
            linkedin_url=linkedin_url if linkedin_url and linkedin_url.strip() else None,
            resume_text=resume_text if resume_text and resume_text.strip() else None,
            skill_names=skill_names,
        )

        try:
            await log_action(
                db=db,
                user_id=user.id,
                action="Candidate Created",
                entity_type="Candidate",
                entity_id=candidate.id,
                details=f"Candidate '{candidate.first_name} {candidate.last_name}' created",
            )
        except Exception:
            logger.warning("Failed to create audit log for candidate creation, candidate_id=%s", candidate.id)

        return RedirectResponse(
            url=f"/dashboard/candidates/{candidate.id}",
            status_code=302,
        )
    except ValueError as e:
        logger.warning("Candidate creation failed: %s", str(e))
        return templates.TemplateResponse(
            request,
            "candidates/form.html",
            context={
                "user": user,
                "candidate": None,
                "error": str(e),
            },
            status_code=400,
        )


@router.get("/dashboard/candidates/{candidate_id}")
async def candidates_detail_page(
    request: Request,
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter", "Hiring Manager", "Interviewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    candidate = await get_candidate(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    applications = await list_applications(
        db=db,
        candidate_id=candidate_id,
    )

    return templates.TemplateResponse(
        request,
        "candidates/detail.html",
        context={
            "user": user,
            "candidate": candidate,
            "applications": applications,
        },
    )


@router.get("/dashboard/candidates/{candidate_id}/edit")
async def candidates_edit_form(
    request: Request,
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    candidate = await get_candidate(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return templates.TemplateResponse(
        request,
        "candidates/form.html",
        context={
            "user": user,
            "candidate": candidate,
            "error": None,
        },
    )


@router.post("/dashboard/candidates/{candidate_id}")
async def candidates_update(
    request: Request,
    candidate_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    linkedin_url: str = Form(""),
    skills: str = Form(""),
    resume_text: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    candidate = await get_candidate(db, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    skill_names = None
    if skills is not None:
        skill_names = [s.strip() for s in skills.split(",") if s.strip()]

    try:
        updated_candidate = await edit_candidate(
            db=db,
            candidate_id=candidate_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone if phone and phone.strip() else None,
            linkedin_url=linkedin_url if linkedin_url and linkedin_url.strip() else None,
            resume_text=resume_text if resume_text and resume_text.strip() else None,
            skill_names=skill_names,
        )

        try:
            await log_action(
                db=db,
                user_id=user.id,
                action="Candidate Updated",
                entity_type="Candidate",
                entity_id=updated_candidate.id,
                details=f"Candidate '{updated_candidate.first_name} {updated_candidate.last_name}' updated",
            )
        except Exception:
            logger.warning("Failed to create audit log for candidate update, candidate_id=%s", candidate_id)

        return RedirectResponse(
            url=f"/dashboard/candidates/{updated_candidate.id}",
            status_code=302,
        )
    except ValueError as e:
        logger.warning("Candidate update failed: %s", str(e))
        refreshed_candidate = await get_candidate(db, candidate_id)
        return templates.TemplateResponse(
            request,
            "candidates/form.html",
            context={
                "user": user,
                "candidate": refreshed_candidate if refreshed_candidate else candidate,
                "error": str(e),
            },
            status_code=400,
        )