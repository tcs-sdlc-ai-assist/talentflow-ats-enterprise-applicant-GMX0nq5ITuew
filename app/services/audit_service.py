import logging
import math
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

ALLOWED_ACTIONS = [
    "Job Published",
    "Job Closed",
    "Job Created",
    "Job Updated",
    "Job Archived",
    "Candidate Created",
    "Candidate Updated",
    "Candidate Rejected",
    "Candidate Hired",
    "Application Created",
    "Application Updated",
    "Application Status Changed",
    "Interview Scheduled",
    "Interview Completed",
    "Interview Cancelled",
    "Feedback Submitted",
    "User Created",
    "User Updated",
    "User Deactivated",
    "Offer Created",
    "Offer Updated",
    "Offer Accepted",
    "Offer Rejected",
]

ALLOWED_ENTITY_TYPES = [
    "Job",
    "Candidate",
    "Application",
    "Interview",
    "Feedback",
    "User",
    "Offer",
]


async def log_action(
    db: AsyncSession,
    user_id: int,
    action: str,
    entity_type: str,
    entity_id: int,
    details: Optional[str] = None,
) -> AuditLog:
    if action not in ALLOWED_ACTIONS:
        logger.warning("Attempted to log invalid action: %s", action)
        raise ValueError(f"Invalid action: {action}. Must be one of: {ALLOWED_ACTIONS}")

    if entity_type not in ALLOWED_ENTITY_TYPES:
        logger.warning("Attempted to log invalid entity_type: %s", entity_type)
        raise ValueError(f"Invalid entity_type: {entity_type}. Must be one of: {ALLOWED_ENTITY_TYPES}")

    if entity_id < 1:
        raise ValueError("entity_id must be a positive integer")

    if user_id < 1:
        raise ValueError("user_id must be a positive integer")

    audit_log = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        user_id=user_id,
    )

    db.add(audit_log)
    await db.flush()
    await db.refresh(audit_log)

    logger.info(
        "Audit log created: action=%s, entity_type=%s, entity_id=%d, user_id=%d",
        action,
        entity_type,
        entity_id,
        user_id,
    )

    return audit_log


async def get_logs(
    db: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 20,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
) -> dict:
    if page < 1:
        page = 1
    if per_page < 10:
        per_page = 10
    if per_page > 100:
        per_page = 100

    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    if action is not None:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)

    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
        count_query = count_query.where(AuditLog.user_id == user_id)

    if entity_type is not None:
        query = query.where(AuditLog.entity_type == entity_type)
        count_query = count_query.where(AuditLog.entity_type == entity_type)

    if entity_id is not None:
        query = query.where(AuditLog.entity_id == entity_id)
        count_query = count_query.where(AuditLog.entity_id == entity_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    total_pages = max(1, math.ceil(total / per_page))

    if page > total_pages:
        page = total_pages

    offset = (page - 1) * per_page

    query = query.order_by(AuditLog.timestamp.desc())
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    audit_logs = result.scalars().all()

    return {
        "audit_logs": audit_logs,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


async def get_recent_logs(
    db: AsyncSession,
    limit: int = 10,
) -> list[AuditLog]:
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100

    query = (
        select(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_logs_for_entity(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
    limit: int = 50,
) -> list[AuditLog]:
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100

    query = (
        select(AuditLog)
        .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_logs_for_user(
    db: AsyncSession,
    user_id: int,
    limit: int = 50,
) -> list[AuditLog]:
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100

    query = (
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())