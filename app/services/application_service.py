import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application, ALLOWED_TRANSITIONS, ALLOWED_STATUSES
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.user import User
from app.services.audit_service import create_audit_log

logger = logging.getLogger(__name__)


async def create_application(
    db: AsyncSession,
    job_id: int,
    candidate_id: int,
    user: User,
) -> Application:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalars().first()
    if job is None:
        raise ValueError(f"Job with id {job_id} not found")

    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalars().first()
    if candidate is None:
        raise ValueError(f"Candidate with id {candidate_id} not found")

    result = await db.execute(
        select(Application).where(
            Application.job_id == job_id,
            Application.candidate_id == candidate_id,
        )
    )
    existing = result.scalars().first()
    if existing is not None:
        raise ValueError(
            f"Candidate {candidate_id} has already applied to job {job_id}"
        )

    application = Application(
        job_id=job_id,
        candidate_id=candidate_id,
        status="Applied",
    )
    db.add(application)
    await db.flush()
    await db.refresh(application)

    logger.info(
        "Application created: id=%s, job_id=%s, candidate_id=%s, by user=%s",
        application.id,
        job_id,
        candidate_id,
        user.id,
    )

    await create_audit_log(
        db=db,
        action="Application Created",
        entity_type="Application",
        entity_id=application.id,
        user_id=user.id,
        details=f"Candidate {candidate_id} applied to job {job_id}",
    )

    return application


async def update_status(
    db: AsyncSession,
    application_id: int,
    new_status: str,
    user: User,
) -> Application:
    if new_status not in ALLOWED_STATUSES:
        raise ValueError(
            f"Invalid status '{new_status}'. Must be one of: {', '.join(ALLOWED_STATUSES)}"
        )

    result = await db.execute(
        select(Application)
        .where(Application.id == application_id)
        .options(
            selectinload(Application.job),
            selectinload(Application.candidate),
        )
    )
    application = result.scalars().first()
    if application is None:
        raise ValueError(f"Application with id {application_id} not found")

    current_status = application.status
    allowed = ALLOWED_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Invalid status transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {', '.join(allowed) if allowed else 'none'}"
        )

    old_status = application.status
    application.status = new_status
    application.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(application)

    logger.info(
        "Application %s status changed: %s -> %s by user %s",
        application_id,
        old_status,
        new_status,
        user.id,
    )

    await create_audit_log(
        db=db,
        action="Application Status Changed",
        entity_type="Application",
        entity_id=application.id,
        user_id=user.id,
        details=f"Status changed from '{old_status}' to '{new_status}'",
    )

    return application


async def list_applications(
    db: AsyncSession,
    status_filter: Optional[str] = None,
    job_id: Optional[int] = None,
    candidate_id: Optional[int] = None,
) -> list[Application]:
    query = (
        select(Application)
        .options(
            selectinload(Application.job),
            selectinload(Application.candidate),
            selectinload(Application.interviews),
        )
        .order_by(Application.created_at.desc())
    )

    if status_filter and status_filter in ALLOWED_STATUSES:
        query = query.where(Application.status == status_filter)

    if job_id is not None:
        query = query.where(Application.job_id == job_id)

    if candidate_id is not None:
        query = query.where(Application.candidate_id == candidate_id)

    result = await db.execute(query)
    applications = result.scalars().all()
    return list(applications)


async def get_application(
    db: AsyncSession,
    application_id: int,
) -> Optional[Application]:
    result = await db.execute(
        select(Application)
        .where(Application.id == application_id)
        .options(
            selectinload(Application.job),
            selectinload(Application.candidate),
            selectinload(Application.interviews),
            selectinload(Application.offers),
        )
    )
    application = result.scalars().first()
    return application


async def get_kanban(
    db: AsyncSession,
    job_id: int,
) -> dict[str, list[Application]]:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalars().first()
    if job is None:
        raise ValueError(f"Job with id {job_id} not found")

    result = await db.execute(
        select(Application)
        .where(Application.job_id == job_id)
        .options(
            selectinload(Application.candidate),
            selectinload(Application.job),
            selectinload(Application.interviews),
        )
        .order_by(Application.created_at.asc())
    )
    applications = result.scalars().all()

    pipeline: dict[str, list[Application]] = {}
    for status in ALLOWED_STATUSES:
        pipeline[status] = []

    for application in applications:
        status = application.status
        if status in pipeline:
            pipeline[status].append(application)
        else:
            pipeline[status] = [application]

    return pipeline


async def get_application_count_for_job(
    db: AsyncSession,
    job_id: int,
) -> int:
    result = await db.execute(
        select(func.count(Application.id)).where(Application.job_id == job_id)
    )
    count = result.scalar()
    return count or 0