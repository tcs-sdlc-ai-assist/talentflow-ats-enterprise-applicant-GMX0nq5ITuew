import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.auth_service import get_users_by_role, get_all_users
from app.services.job_service import (
    create_job,
    edit_job,
    change_status,
    list_jobs,
    get_job,
    get_departments,
)
from app.services.application_service import get_application_count_for_job

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/dashboard/jobs")
async def jobs_list_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter", "Hiring Manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    hiring_manager_id = None
    if user.role == "Hiring Manager":
        hiring_manager_id = user.id

    per_page = 20
    jobs, total = await list_jobs(
        db,
        status=status,
        department=department,
        search=search,
        hiring_manager_id=hiring_manager_id,
        page=page,
        per_page=per_page,
    )

    total_pages = max(1, (total + per_page - 1) // per_page)

    departments = await get_departments(db)

    filters = {
        "search": search or "",
        "department": department or "",
        "status": status or "",
    }

    return templates.TemplateResponse(
        request,
        "jobs/list.html",
        context={
            "user": user,
            "jobs": jobs,
            "departments": departments,
            "filters": filters,
            "current_page": page,
            "total_pages": total_pages,
            "total": total,
        },
    )


@router.get("/dashboard/jobs/create")
async def jobs_create_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    hiring_managers = await get_users_by_role(db, "Hiring Manager")
    all_admins = await get_users_by_role(db, "System Admin")
    all_hr = await get_users_by_role(db, "HR Recruiter")
    combined_managers = hiring_managers + all_admins + all_hr

    return templates.TemplateResponse(
        request,
        "jobs/form.html",
        context={
            "user": user,
            "job": None,
            "hiring_managers": combined_managers,
            "errors": [],
            "form_data": None,
        },
    )


@router.post("/dashboard/jobs")
async def jobs_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    department: str = Form(...),
    location: str = Form(...),
    type: str = Form(...),
    salary_min: int = Form(...),
    salary_max: int = Form(...),
    description: str = Form(...),
    hiring_manager_id: int = Form(...),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    form_data = {
        "title": title,
        "department": department,
        "location": location,
        "type": type,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "description": description,
        "hiring_manager_id": hiring_manager_id,
    }

    errors = []
    if not title or not title.strip():
        errors.append("Title is required")
    if not department or not department.strip():
        errors.append("Department is required")
    if not location or not location.strip():
        errors.append("Location is required")
    if not type or not type.strip():
        errors.append("Job type is required")
    if not description or not description.strip():
        errors.append("Description is required")
    if salary_min < 0:
        errors.append("Minimum salary must be a positive number")
    if salary_max < 0:
        errors.append("Maximum salary must be a positive number")
    if salary_max < salary_min:
        errors.append("Maximum salary must be greater than or equal to minimum salary")

    if errors:
        hiring_managers = await get_users_by_role(db, "Hiring Manager")
        all_admins = await get_users_by_role(db, "System Admin")
        all_hr = await get_users_by_role(db, "HR Recruiter")
        combined_managers = hiring_managers + all_admins + all_hr

        return templates.TemplateResponse(
            request,
            "jobs/form.html",
            context={
                "user": user,
                "job": None,
                "hiring_managers": combined_managers,
                "errors": errors,
                "form_data": form_data,
            },
            status_code=422,
        )

    try:
        job = await create_job(
            db=db,
            title=title,
            department=department,
            location=location,
            type=type,
            salary_min=salary_min,
            salary_max=salary_max,
            description=description,
            hiring_manager_id=hiring_manager_id,
            user=user,
        )
        return RedirectResponse(
            url=f"/dashboard/jobs/{job.id}", status_code=302
        )
    except ValueError as e:
        hiring_managers = await get_users_by_role(db, "Hiring Manager")
        all_admins = await get_users_by_role(db, "System Admin")
        all_hr = await get_users_by_role(db, "HR Recruiter")
        combined_managers = hiring_managers + all_admins + all_hr

        return templates.TemplateResponse(
            request,
            "jobs/form.html",
            context={
                "user": user,
                "job": None,
                "hiring_managers": combined_managers,
                "errors": [str(e)],
                "form_data": form_data,
            },
            status_code=422,
        )


@router.get("/dashboard/jobs/{job_id}")
async def jobs_detail_page(
    request: Request,
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter", "Hiring Manager", "Interviewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    job = await get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if user.role == "Hiring Manager" and job.hiring_manager_id != user.id:
        raise HTTPException(status_code=403, detail="You can only view your own jobs")

    application_count = await get_application_count_for_job(db, job_id)

    return templates.TemplateResponse(
        request,
        "jobs/detail.html",
        context={
            "user": user,
            "job": job,
            "application_count": application_count,
        },
    )


@router.get("/dashboard/jobs/{job_id}/edit")
async def jobs_edit_form(
    request: Request,
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter", "Hiring Manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    job = await get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if user.role == "Hiring Manager" and job.hiring_manager_id != user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own jobs")

    hiring_managers = await get_users_by_role(db, "Hiring Manager")
    all_admins = await get_users_by_role(db, "System Admin")
    all_hr = await get_users_by_role(db, "HR Recruiter")
    combined_managers = hiring_managers + all_admins + all_hr

    return templates.TemplateResponse(
        request,
        "jobs/form.html",
        context={
            "user": user,
            "job": job,
            "hiring_managers": combined_managers,
            "errors": [],
            "form_data": None,
        },
    )


@router.post("/dashboard/jobs/{job_id}")
async def jobs_update(
    request: Request,
    job_id: int,
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    department: str = Form(...),
    location: str = Form(...),
    type: str = Form(...),
    salary_min: int = Form(...),
    salary_max: int = Form(...),
    description: str = Form(...),
    hiring_manager_id: int = Form(...),
    status: Optional[str] = Form(None),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter", "Hiring Manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    job = await get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if user.role == "Hiring Manager" and job.hiring_manager_id != user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own jobs")

    form_data = {
        "title": title,
        "department": department,
        "location": location,
        "type": type,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "description": description,
        "hiring_manager_id": hiring_manager_id,
    }

    errors = []
    if not title or not title.strip():
        errors.append("Title is required")
    if not department or not department.strip():
        errors.append("Department is required")
    if not location or not location.strip():
        errors.append("Location is required")
    if not type or not type.strip():
        errors.append("Job type is required")
    if not description or not description.strip():
        errors.append("Description is required")
    if salary_min < 0:
        errors.append("Minimum salary must be a positive number")
    if salary_max < 0:
        errors.append("Maximum salary must be a positive number")
    if salary_max < salary_min:
        errors.append("Maximum salary must be greater than or equal to minimum salary")

    if errors:
        hiring_managers = await get_users_by_role(db, "Hiring Manager")
        all_admins = await get_users_by_role(db, "System Admin")
        all_hr = await get_users_by_role(db, "HR Recruiter")
        combined_managers = hiring_managers + all_admins + all_hr

        return templates.TemplateResponse(
            request,
            "jobs/form.html",
            context={
                "user": user,
                "job": job,
                "hiring_managers": combined_managers,
                "errors": errors,
                "form_data": form_data,
            },
            status_code=422,
        )

    try:
        updated_job = await edit_job(
            db=db,
            job_id=job_id,
            user=user,
            title=title,
            department=department,
            location=location,
            type=type,
            salary_min=salary_min,
            salary_max=salary_max,
            description=description,
            hiring_manager_id=hiring_manager_id,
            status=status if status else None,
        )
        return RedirectResponse(
            url=f"/dashboard/jobs/{updated_job.id}", status_code=302
        )
    except ValueError as e:
        hiring_managers = await get_users_by_role(db, "Hiring Manager")
        all_admins = await get_users_by_role(db, "System Admin")
        all_hr = await get_users_by_role(db, "HR Recruiter")
        combined_managers = hiring_managers + all_admins + all_hr

        return templates.TemplateResponse(
            request,
            "jobs/form.html",
            context={
                "user": user,
                "job": job,
                "hiring_managers": combined_managers,
                "errors": [str(e)],
                "form_data": form_data,
            },
            status_code=422,
        )


@router.post("/dashboard/jobs/{job_id}/status")
async def jobs_change_status(
    request: Request,
    job_id: int,
    db: AsyncSession = Depends(get_db),
    status: str = Form(...),
):
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    if user.role not in ["System Admin", "HR Recruiter", "Hiring Manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    job = await get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if user.role == "Hiring Manager" and job.hiring_manager_id != user.id:
        raise HTTPException(status_code=403, detail="You can only change status of your own jobs")

    try:
        await change_status(
            db=db,
            job_id=job_id,
            new_status=status,
            user=user,
        )
        return RedirectResponse(
            url=f"/dashboard/jobs/{job_id}", status_code=302
        )
    except ValueError as e:
        logger.warning(
            "Failed to change job %s status to '%s': %s", job_id, status, str(e)
        )
        raise HTTPException(status_code=422, detail=str(e))