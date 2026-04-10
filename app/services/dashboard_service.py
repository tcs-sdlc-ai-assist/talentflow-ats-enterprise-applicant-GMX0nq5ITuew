import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.job import Job
from app.models.user import User

logger = logging.getLogger(__name__)


class DashboardService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_data(self, user_id: int, role: str) -> dict[str, Any]:
        if role in ("System Admin", "HR Recruiter"):
            return await self._get_admin_dashboard(user_id)
        elif role == "Hiring Manager":
            return await self._get_hiring_manager_dashboard(user_id)
        elif role == "Interviewer":
            return await self._get_interviewer_dashboard(user_id)
        else:
            return await self._get_default_dashboard(user_id)

    async def _get_admin_dashboard(self, user_id: int) -> dict[str, Any]:
        metrics = {}

        # Open positions count (Published jobs)
        result = await self.db.execute(
            select(func.count(Job.id)).where(Job.status == "Published")
        )
        metrics["open_positions"] = result.scalar() or 0

        # Active candidates count
        result = await self.db.execute(
            select(func.count(Candidate.id))
        )
        metrics["active_candidates"] = result.scalar() or 0

        # Average time to hire (days between created_at and updated_at for Hired applications)
        metrics["time_to_hire"] = await self._calculate_time_to_hire()

        # Pending interviews (interviews without feedback)
        result = await self.db.execute(
            select(func.count(Interview.id)).where(
                Interview.feedback_rating.is_(None)
            )
        )
        metrics["pending_interviews"] = result.scalar() or 0

        # Recent audit logs
        recent_audit_logs = await self._get_recent_audit_logs(limit=10)

        # Pending items (applications in early stages, interviews without feedback)
        pending_items = await self._get_admin_pending_items()

        return {
            "metrics": metrics,
            "recent_audit_logs": recent_audit_logs,
            "pending_items": pending_items,
        }

    async def _get_hiring_manager_dashboard(self, user_id: int) -> dict[str, Any]:
        metrics = {}

        # Open positions for this hiring manager
        result = await self.db.execute(
            select(func.count(Job.id)).where(
                Job.hiring_manager_id == user_id,
                Job.status == "Published",
            )
        )
        metrics["open_positions"] = result.scalar() or 0

        # Active candidates for this manager's jobs
        result = await self.db.execute(
            select(func.count(Application.id.distinct())).where(
                Application.job_id.in_(
                    select(Job.id).where(Job.hiring_manager_id == user_id)
                ),
                Application.status.notin_(["Hired", "Rejected"]),
            )
        )
        metrics["active_candidates"] = result.scalar() or 0

        # Pending interviews for this manager's jobs
        result = await self.db.execute(
            select(func.count(Interview.id)).where(
                Interview.feedback_rating.is_(None),
                Interview.application_id.in_(
                    select(Application.id).where(
                        Application.job_id.in_(
                            select(Job.id).where(Job.hiring_manager_id == user_id)
                        )
                    )
                ),
            )
        )
        metrics["pending_interviews"] = result.scalar() or 0

        # Jobs for this manager
        result = await self.db.execute(
            select(Job)
            .where(Job.hiring_manager_id == user_id)
            .options(selectinload(Job.applications))
            .order_by(Job.created_at.desc())
        )
        jobs_raw = result.scalars().all()

        jobs = []
        for job in jobs_raw:
            job.applicant_count = len(job.applications) if job.applications else 0
            jobs.append(job)

        # Pending items for hiring manager
        pending_items = await self._get_hm_pending_items(user_id)

        return {
            "metrics": metrics,
            "jobs": jobs,
            "pending_items": pending_items,
        }

    async def _get_interviewer_dashboard(self, user_id: int) -> dict[str, Any]:
        metrics = {}

        # Upcoming interviews assigned to this interviewer
        result = await self.db.execute(
            select(func.count(Interview.id)).where(
                Interview.interviewer_id == user_id,
                Interview.feedback_rating.is_(None),
            )
        )
        metrics["pending_interviews"] = result.scalar() or 0

        # Missing feedback count
        result = await self.db.execute(
            select(func.count(Interview.id)).where(
                Interview.interviewer_id == user_id,
                Interview.feedback_rating.is_(None),
                Interview.scheduled_at < datetime.utcnow(),
            )
        )
        metrics["missing_feedback"] = result.scalar() or 0

        # Upcoming interviews
        result = await self.db.execute(
            select(Interview)
            .where(
                Interview.interviewer_id == user_id,
                Interview.feedback_rating.is_(None),
            )
            .options(
                selectinload(Interview.application).selectinload(Application.candidate),
                selectinload(Interview.application).selectinload(Application.job),
            )
            .order_by(Interview.scheduled_at.asc())
        )
        upcoming_interviews = result.scalars().all()

        pending_items = []
        for interview in upcoming_interviews:
            candidate_name = ""
            job_title = ""
            if interview.application:
                if interview.application.candidate:
                    candidate_name = (
                        f"{interview.application.candidate.first_name} "
                        f"{interview.application.candidate.last_name}"
                    )
                if interview.application.job:
                    job_title = interview.application.job.title

            scheduled_str = ""
            if interview.scheduled_at:
                scheduled_str = interview.scheduled_at.strftime("%b %d, %Y at %I:%M %p")

            pending_items.append({
                "description": f"Interview for {candidate_name} — {job_title}",
                "scheduled_at": scheduled_str,
                "candidate_name": candidate_name,
                "link": f"/dashboard/interviews/{interview.id}/feedback",
            })

        # Missing feedback items
        missing_feedback_items = []
        result = await self.db.execute(
            select(Interview)
            .where(
                Interview.interviewer_id == user_id,
                Interview.feedback_rating.is_(None),
                Interview.scheduled_at < datetime.utcnow(),
            )
            .options(
                selectinload(Interview.application).selectinload(Application.candidate),
                selectinload(Interview.application).selectinload(Application.job),
            )
            .order_by(Interview.scheduled_at.asc())
        )
        past_interviews = result.scalars().all()

        for interview in past_interviews:
            candidate_name = ""
            if interview.application and interview.application.candidate:
                candidate_name = (
                    f"{interview.application.candidate.first_name} "
                    f"{interview.application.candidate.last_name}"
                )
            missing_feedback_items.append({
                "description": f"Feedback pending for {candidate_name}",
                "link": f"/dashboard/interviews/{interview.id}/feedback",
            })

        return {
            "metrics": metrics,
            "pending_items": pending_items,
            "missing_feedback_items": missing_feedback_items,
        }

    async def _get_default_dashboard(self, user_id: int) -> dict[str, Any]:
        return {
            "metrics": {
                "open_positions": 0,
                "active_candidates": 0,
                "time_to_hire": 0,
                "pending_interviews": 0,
            },
            "recent_audit_logs": [],
            "pending_items": [],
        }

    async def _calculate_time_to_hire(self) -> int:
        try:
            result = await self.db.execute(
                select(Application.created_at, Application.updated_at).where(
                    Application.status == "Hired"
                )
            )
            rows = result.all()

            if not rows:
                return 0

            total_days = 0
            count = 0
            for row in rows:
                created_at = row[0]
                updated_at = row[1]
                if created_at and updated_at:
                    delta = updated_at - created_at
                    total_days += delta.days
                    count += 1

            if count == 0:
                return 0

            return round(total_days / count)
        except Exception:
            logger.exception("Error calculating time to hire")
            return 0

    async def _get_recent_audit_logs(self, limit: int = 10) -> list[dict[str, Any]]:
        try:
            result = await self.db.execute(
                select(AuditLog)
                .options(selectinload(AuditLog.user))
                .order_by(AuditLog.timestamp.desc())
                .limit(limit)
            )
            logs = result.scalars().all()

            audit_log_list = []
            for log in logs:
                user_full_name = ""
                if log.user:
                    user_full_name = log.user.full_name or log.user.username

                audit_log_list.append({
                    "id": log.id,
                    "action": log.action,
                    "entity_type": log.entity_type,
                    "entity_id": log.entity_id,
                    "details": log.details,
                    "user_id": log.user_id,
                    "user_full_name": user_full_name,
                    "timestamp": log.timestamp,
                })

            return audit_log_list
        except Exception:
            logger.exception("Error fetching recent audit logs")
            return []

    async def _get_admin_pending_items(self) -> list[dict[str, Any]]:
        pending_items = []

        try:
            # Applications stuck in early stages for more than 7 days
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            result = await self.db.execute(
                select(func.count(Application.id)).where(
                    Application.status.in_(["Applied", "Screening"]),
                    Application.updated_at < seven_days_ago,
                )
            )
            stale_count = result.scalar() or 0
            if stale_count > 0:
                pending_items.append({
                    "description": f"{stale_count} application(s) have been in early stages for over 7 days",
                    "link": "/dashboard/applications?status=Applied",
                })

            # Interviews without feedback that are past scheduled date
            result = await self.db.execute(
                select(func.count(Interview.id)).where(
                    Interview.feedback_rating.is_(None),
                    Interview.scheduled_at < datetime.utcnow(),
                )
            )
            missing_feedback_count = result.scalar() or 0
            if missing_feedback_count > 0:
                pending_items.append({
                    "description": f"{missing_feedback_count} interview(s) are missing feedback",
                    "link": "/dashboard/interviews",
                })

        except Exception:
            logger.exception("Error fetching admin pending items")

        return pending_items

    async def _get_hm_pending_items(self, user_id: int) -> list[dict[str, Any]]:
        pending_items = []

        try:
            result = await self.db.execute(
                select(Interview)
                .where(
                    Interview.feedback_rating.is_(None),
                    Interview.application_id.in_(
                        select(Application.id).where(
                            Application.job_id.in_(
                                select(Job.id).where(Job.hiring_manager_id == user_id)
                            )
                        )
                    ),
                )
                .options(
                    selectinload(Interview.application).selectinload(Application.candidate),
                    selectinload(Interview.application).selectinload(Application.job),
                    selectinload(Interview.interviewer),
                )
                .order_by(Interview.scheduled_at.asc())
                .limit(10)
            )
            interviews = result.scalars().all()

            for interview in interviews:
                candidate_name = ""
                job_title = ""
                if interview.application:
                    if interview.application.candidate:
                        candidate_name = (
                            f"{interview.application.candidate.first_name} "
                            f"{interview.application.candidate.last_name}"
                        )
                    if interview.application.job:
                        job_title = interview.application.job.title

                interviewer_name = ""
                if interview.interviewer:
                    interviewer_name = interview.interviewer.full_name or interview.interviewer.username

                scheduled_str = ""
                if interview.scheduled_at:
                    scheduled_str = interview.scheduled_at.strftime("%b %d, %Y at %I:%M %p")

                pending_items.append({
                    "description": f"Interview: {candidate_name} for {job_title} with {interviewer_name}",
                    "scheduled_at": scheduled_str,
                    "link": f"/dashboard/applications/{interview.application_id}",
                })

        except Exception:
            logger.exception("Error fetching hiring manager pending items")

        return pending_items