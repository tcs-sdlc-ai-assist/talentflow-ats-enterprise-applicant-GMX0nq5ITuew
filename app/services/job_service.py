import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job
from app.models.user import User

logger = logging.getLogger(__name__)

ALLOWED_JOB_STATUSES = {"Draft", "Published", "Closed"}

ALLOWED_JOB_TRANSITIONS = {
    "Draft": ["Published", "Closed"],
    "Published": ["Closed", "Draft"],
    "Closed": ["Draft"],
}


async def create_job(
    db: AsyncSession,
    title: str,
    department: str,
    location: str,
    type: str,
    salary_min: int,
    salary_max: int,
    description: str,
    hiring_manager_id: int,
    user: User,
) -> Job:
    result = await db.execute(select(User).where(User.id == hiring_manager_id, User.is_active == True))
    hiring_manager = result.scalars().first()
    if hiring_manager is None:
        raise ValueError(f"Hiring manager with id {hiring_manager_id} not found or inactive")

    if salary_min < 0:
        raise ValueError("Salary min must be a positive number")
    if salary_max < 0:
        raise ValueError("Salary max must be a positive number")
    if salary_max < salary_min:
        raise ValueError("Salary max must be greater than or equal to salary min")

    job = Job(
        title=title.strip(),
        department=department.strip(),
        location=location.strip(),
        type=type.strip(),
        salary_min=salary_min,
        salary_max=salary_max,
        description=description.strip(),
        status="Draft",
        hiring_manager_id=hiring_manager_id,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    logger.info("Job created: id=%s, title='%s', by user=%s", job.id, job.title, user.id)

    try:
        from app.services.audit_service import log_audit

        await log_audit(
            db=db,
            action="Job Created",
            entity_type="Job",
            entity_id=job.id,
            user_id=user.id,
            details=f"Job '{job.title}' created in department '{job.department}'",
        )
    except Exception:
        logger.warning("Failed to create audit log for job creation, job_id=%s", job.id)

    return job


async def edit_job(
    db: AsyncSession,
    job_id: int,
    user: User,
    title: Optional[str] = None,
    department: Optional[str] = None,
    location: Optional[str] = None,
    type: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    description: Optional[str] = None,
    hiring_manager_id: Optional[int] = None,
    status: Optional[str] = None,
) -> Job:
    result = await db.execute(
        select(Job)
        .where(Job.id == job_id)
        .options(selectinload(Job.hiring_manager))
    )
    job = result.scalars().first()
    if job is None:
        raise ValueError(f"Job with id {job_id} not found")

    if title is not None:
        title = title.strip()
        if not title:
            raise ValueError("Title must not be empty")
        if len(title) > 100:
            raise ValueError("Title must be at most 100 characters")
        job.title = title

    if department is not None:
        department = department.strip()
        if not department:
            raise ValueError("Department must not be empty")
        if len(department) > 50:
            raise ValueError("Department must be at most 50 characters")
        job.department = department

    if location is not None:
        location = location.strip()
        if not location:
            raise ValueError("Location must not be empty")
        if len(location) > 100:
            raise ValueError("Location must be at most 100 characters")
        job.location = location

    if type is not None:
        type = type.strip()
        if not type:
            raise ValueError("Type must not be empty")
        if len(type) > 30:
            raise ValueError("Type must be at most 30 characters")
        job.type = type

    if salary_min is not None:
        if salary_min < 0:
            raise ValueError("Salary min must be a positive number")
        job.salary_min = salary_min

    if salary_max is not None:
        if salary_max < 0:
            raise ValueError("Salary max must be a positive number")
        job.salary_max = salary_max

    effective_min = job.salary_min
    effective_max = job.salary_max
    if effective_max < effective_min:
        raise ValueError("Salary max must be greater than or equal to salary min")

    if description is not None:
        description = description.strip()
        if not description:
            raise ValueError("Description must not be empty")
        job.description = description

    if hiring_manager_id is not None:
        hm_result = await db.execute(
            select(User).where(User.id == hiring_manager_id, User.is_active == True)
        )
        hiring_manager = hm_result.scalars().first()
        if hiring_manager is None:
            raise ValueError(f"Hiring manager with id {hiring_manager_id} not found or inactive")
        job.hiring_manager_id = hiring_manager_id

    if status is not None:
        status = status.strip()
        if status not in ALLOWED_JOB_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(sorted(ALLOWED_JOB_STATUSES))}")
        if status != job.status:
            allowed = ALLOWED_JOB_TRANSITIONS.get(job.status, [])
            if status not in allowed:
                raise ValueError(
                    f"Invalid status transition from '{job.status}' to '{status}'. "
                    f"Allowed transitions: {', '.join(allowed) if allowed else 'none'}"
                )
            job.status = status

    job.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(job)

    logger.info("Job updated: id=%s, by user=%s", job.id, user.id)

    try:
        from app.services.audit_service import log_audit

        await log_audit(
            db=db,
            action="Job Updated",
            entity_type="Job",
            entity_id=job.id,
            user_id=user.id,
            details=f"Job '{job.title}' updated",
        )
    except Exception:
        logger.warning("Failed to create audit log for job update, job_id=%s", job.id)

    return job


async def change_status(
    db: AsyncSession,
    job_id: int,
    new_status: str,
    user: User,
) -> Job:
    new_status = new_status.strip()
    if new_status not in ALLOWED_JOB_STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(sorted(ALLOWED_JOB_STATUSES))}")

    result = await db.execute(
        select(Job)
        .where(Job.id == job_id)
        .options(selectinload(Job.hiring_manager))
    )
    job = result.scalars().first()
    if job is None:
        raise ValueError(f"Job with id {job_id} not found")

    old_status = job.status
    if new_status == old_status:
        return job

    allowed = ALLOWED_JOB_TRANSITIONS.get(old_status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Invalid status transition from '{old_status}' to '{new_status}'. "
            f"Allowed transitions: {', '.join(allowed) if allowed else 'none'}"
        )

    job.status = new_status
    job.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(job)

    logger.info(
        "Job status changed: id=%s, from='%s' to='%s', by user=%s",
        job.id,
        old_status,
        new_status,
        user.id,
    )

    try:
        from app.services.audit_service import log_audit

        if new_status == "Published":
            action = "Job Published"
        elif new_status == "Closed":
            action = "Job Closed"
        else:
            action = "Job Updated"

        await log_audit(
            db=db,
            action=action,
            entity_type="Job",
            entity_id=job.id,
            user_id=user.id,
            details=f"Job '{job.title}' status changed from '{old_status}' to '{new_status}'",
        )
    except Exception:
        logger.warning("Failed to create audit log for job status change, job_id=%s", job.id)

    return job


async def list_jobs(
    db: AsyncSession,
    status: Optional[str] = None,
    department: Optional[str] = None,
    search: Optional[str] = None,
    hiring_manager_id: Optional[int] = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Job], int]:
    query = select(Job).options(selectinload(Job.hiring_manager))
    count_query = select(func.count(Job.id))

    if status is not None and status.strip():
        query = query.where(Job.status == status.strip())
        count_query = count_query.where(Job.status == status.strip())

    if department is not None and department.strip():
        query = query.where(Job.department == department.strip())
        count_query = count_query.where(Job.department == department.strip())

    if hiring_manager_id is not None:
        query = query.where(Job.hiring_manager_id == hiring_manager_id)
        count_query = count_query.where(Job.hiring_manager_id == hiring_manager_id)

    if search is not None and search.strip():
        search_term = f"%{search.strip()}%"
        query = query.where(Job.title.ilike(search_term))
        count_query = count_query.where(Job.title.ilike(search_term))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Job.created_at.desc())

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    jobs = list(result.scalars().all())

    return jobs, total


async def get_job(db: AsyncSession, job_id: int) -> Optional[Job]:
    result = await db.execute(
        select(Job)
        .where(Job.id == job_id)
        .options(
            selectinload(Job.hiring_manager),
            selectinload(Job.applications),
        )
    )
    job = result.scalars().first()
    return job


async def list_published_jobs(db: AsyncSession) -> list[Job]:
    result = await db.execute(
        select(Job)
        .where(Job.status == "Published")
        .options(selectinload(Job.hiring_manager))
        .order_by(Job.created_at.desc())
    )
    jobs = list(result.scalars().all())
    return jobs


async def get_departments(db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(Job.department).distinct().order_by(Job.department)
    )
    departments = [row[0] for row in result.all() if row[0]]
    return departments