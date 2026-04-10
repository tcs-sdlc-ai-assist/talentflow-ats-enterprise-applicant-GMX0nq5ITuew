import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application
from app.models.interview import Interview
from app.models.user import User

logger = logging.getLogger(__name__)


async def schedule_interview(
    db: AsyncSession,
    application_id: int,
    interviewer_id: int,
    scheduled_at: datetime,
    user: User,
) -> Interview:
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalars().first()
    if application is None:
        raise ValueError(f"Application with id {application_id} not found")

    result = await db.execute(
        select(User).where(User.id == interviewer_id, User.is_active == True)
    )
    interviewer = result.scalars().first()
    if interviewer is None:
        raise ValueError(f"User with id {interviewer_id} not found or inactive")

    interview = Interview(
        application_id=application_id,
        interviewer_id=interviewer_id,
        scheduled_at=scheduled_at,
    )
    db.add(interview)
    await db.flush()
    await db.refresh(interview)

    logger.info(
        "Interview scheduled: id=%s, application_id=%s, interviewer_id=%s, by user=%s",
        interview.id,
        application_id,
        interviewer_id,
        user.id,
    )

    try:
        from app.services.audit_service import log_audit_event

        await log_audit_event(
            db=db,
            action="Interview Scheduled",
            entity_type="Interview",
            entity_id=interview.id,
            user_id=user.id,
            details=f"Interview scheduled for application {application_id} with interviewer {interviewer_id} at {scheduled_at.isoformat()}",
        )
    except Exception:
        logger.warning("Failed to log audit event for interview scheduling", exc_info=True)

    return interview


async def list_interviews(
    db: AsyncSession,
    application_id: Optional[int] = None,
) -> list[Interview]:
    stmt = select(Interview).options(
        selectinload(Interview.application).selectinload(Application.candidate),
        selectinload(Interview.application).selectinload(Application.job),
        selectinload(Interview.interviewer),
    )

    if application_id is not None:
        stmt = stmt.where(Interview.application_id == application_id)

    stmt = stmt.order_by(Interview.scheduled_at.desc())

    result = await db.execute(stmt)
    interviews = result.scalars().all()
    return list(interviews)


async def get_interview(
    db: AsyncSession,
    interview_id: int,
) -> Optional[Interview]:
    stmt = (
        select(Interview)
        .where(Interview.id == interview_id)
        .options(
            selectinload(Interview.application).selectinload(Application.candidate),
            selectinload(Interview.application).selectinload(Application.job),
            selectinload(Interview.interviewer),
        )
    )
    result = await db.execute(stmt)
    interview = result.scalars().first()
    return interview


async def get_my_interviews(
    db: AsyncSession,
    user: User,
) -> list[Interview]:
    stmt = (
        select(Interview)
        .where(Interview.interviewer_id == user.id)
        .options(
            selectinload(Interview.application).selectinload(Application.candidate),
            selectinload(Interview.application).selectinload(Application.job),
            selectinload(Interview.interviewer),
        )
        .order_by(Interview.scheduled_at.desc())
    )
    result = await db.execute(stmt)
    interviews = result.scalars().all()
    return list(interviews)


async def submit_feedback(
    db: AsyncSession,
    interview_id: int,
    feedback_rating: int,
    feedback_notes: Optional[str],
    user: User,
) -> Interview:
    if feedback_rating < 1 or feedback_rating > 5:
        raise ValueError("feedback_rating must be between 1 and 5")

    stmt = (
        select(Interview)
        .where(Interview.id == interview_id)
        .options(
            selectinload(Interview.application).selectinload(Application.candidate),
            selectinload(Interview.application).selectinload(Application.job),
            selectinload(Interview.interviewer),
        )
    )
    result = await db.execute(stmt)
    interview = result.scalars().first()

    if interview is None:
        raise ValueError(f"Interview with id {interview_id} not found")

    if user.role not in ["System Admin", "HR Recruiter"] and interview.interviewer_id != user.id:
        raise PermissionError("You are not authorized to submit feedback for this interview")

    interview.feedback_rating = feedback_rating
    interview.feedback_notes = feedback_notes.strip() if feedback_notes else None
    interview.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(interview)

    logger.info(
        "Feedback submitted: interview_id=%s, rating=%s, by user=%s",
        interview_id,
        feedback_rating,
        user.id,
    )

    try:
        from app.services.audit_service import log_audit_event

        await log_audit_event(
            db=db,
            action="Feedback Submitted",
            entity_type="Interview",
            entity_id=interview.id,
            user_id=user.id,
            details=f"Feedback submitted for interview {interview_id}: rating={feedback_rating}",
        )
    except Exception:
        logger.warning("Failed to log audit event for feedback submission", exc_info=True)

    return interview


async def get_interviews_for_application(
    db: AsyncSession,
    application_id: int,
) -> list[Interview]:
    stmt = (
        select(Interview)
        .where(Interview.application_id == application_id)
        .options(
            selectinload(Interview.interviewer),
            selectinload(Interview.application),
        )
        .order_by(Interview.scheduled_at.asc())
    )
    result = await db.execute(stmt)
    interviews = result.scalars().all()
    return list(interviews)


async def get_pending_feedback_count(
    db: AsyncSession,
    user: User,
) -> int:
    stmt = (
        select(Interview)
        .where(
            Interview.interviewer_id == user.id,
            Interview.feedback_rating.is_(None),
        )
    )
    result = await db.execute(stmt)
    interviews = result.scalars().all()
    return len(interviews)


async def get_interviews_missing_feedback(
    db: AsyncSession,
    user: User,
) -> list[Interview]:
    stmt = (
        select(Interview)
        .where(
            Interview.interviewer_id == user.id,
            Interview.feedback_rating.is_(None),
        )
        .options(
            selectinload(Interview.application).selectinload(Application.candidate),
            selectinload(Interview.application).selectinload(Application.job),
            selectinload(Interview.interviewer),
        )
        .order_by(Interview.scheduled_at.asc())
    )
    result = await db.execute(stmt)
    interviews = result.scalars().all()
    return list(interviews)