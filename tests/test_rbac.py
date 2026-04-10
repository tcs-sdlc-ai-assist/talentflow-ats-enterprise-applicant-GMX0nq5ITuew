import logging
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.application import Application
from app.models.interview import Interview

logger = logging.getLogger(__name__)


# ─── Unauthenticated Access Tests ───────────────────────────────────────────


class TestUnauthenticatedAccess:
    """Verify that unauthenticated users are redirected to login for protected routes."""

    @pytest.mark.asyncio
    async def test_unauthenticated_dashboard_redirects_to_login(self, async_client: AsyncClient):
        response = await async_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_unauthenticated_jobs_redirects_to_login(self, async_client: AsyncClient):
        response = await async_client.get("/dashboard/jobs", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_unauthenticated_candidates_redirects_to_login(self, async_client: AsyncClient):
        response = await async_client.get("/dashboard/candidates", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_unauthenticated_applications_redirects_to_login(self, async_client: AsyncClient):
        response = await async_client.get("/dashboard/applications", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_unauthenticated_interviews_redirects_to_login(self, async_client: AsyncClient):
        response = await async_client.get("/dashboard/interviews", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_unauthenticated_my_interviews_redirects_to_login(self, async_client: AsyncClient):
        response = await async_client.get("/dashboard/interviews/my", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_unauthenticated_create_job_redirects_to_login(self, async_client: AsyncClient):
        response = await async_client.get("/dashboard/jobs/create", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_unauthenticated_create_candidate_redirects_to_login(self, async_client: AsyncClient):
        response = await async_client.get("/dashboard/candidates/create", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_unauthenticated_create_application_redirects_to_login(self, async_client: AsyncClient):
        response = await async_client.get("/dashboard/applications/create", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_unauthenticated_schedule_interview_redirects_to_login(self, async_client: AsyncClient):
        response = await async_client.get("/dashboard/interviews/schedule", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_unauthenticated_landing_page_accessible(self, async_client: AsyncClient):
        """Landing page should be accessible without authentication."""
        response = await async_client.get("/", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unauthenticated_health_check_accessible(self, async_client: AsyncClient):
        """Health check should be accessible without authentication."""
        response = await async_client.get("/health", follow_redirects=False)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


# ─── System Admin Role Tests ────────────────────────────────────────────────


class TestSystemAdminAccess:
    """Verify System Admin can access all protected routes."""

    @pytest.mark.asyncio
    async def test_admin_can_access_dashboard(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_jobs_list(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard/jobs", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_create_job(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard/jobs/create", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_candidates_list(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard/candidates", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_create_candidate(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard/candidates/create", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_applications_list(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard/applications", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_create_application(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard/applications/create", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_interviews_list(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard/interviews", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_schedule_interview(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard/interviews/schedule", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_my_interviews(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard/interviews/my", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_job_detail(
        self, admin_client: AsyncClient, sample_job: Job
    ):
        response = await admin_client.get(
            f"/dashboard/jobs/{sample_job.id}", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_candidate_detail(
        self, admin_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await admin_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_application_detail(
        self, admin_client: AsyncClient, sample_application: Application
    ):
        response = await admin_client.get(
            f"/dashboard/applications/{sample_application.id}", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_pipeline(
        self, admin_client: AsyncClient, sample_job: Job
    ):
        response = await admin_client.get(
            f"/dashboard/jobs/{sample_job.id}/pipeline", follow_redirects=False
        )
        assert response.status_code == 200


# ─── HR Recruiter Role Tests ────────────────────────────────────────────────


class TestHRRecruiterAccess:
    """Verify HR Recruiter can access permitted routes."""

    @pytest.mark.asyncio
    async def test_recruiter_can_access_dashboard(self, recruiter_client: AsyncClient):
        response = await recruiter_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_recruiter_can_access_jobs_list(self, recruiter_client: AsyncClient):
        response = await recruiter_client.get("/dashboard/jobs", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_recruiter_can_access_create_job(self, recruiter_client: AsyncClient):
        response = await recruiter_client.get(
            "/dashboard/jobs/create", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_recruiter_can_access_candidates_list(self, recruiter_client: AsyncClient):
        response = await recruiter_client.get(
            "/dashboard/candidates", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_recruiter_can_access_create_candidate(self, recruiter_client: AsyncClient):
        response = await recruiter_client.get(
            "/dashboard/candidates/create", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_recruiter_can_access_applications_list(self, recruiter_client: AsyncClient):
        response = await recruiter_client.get(
            "/dashboard/applications", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_recruiter_can_access_create_application(self, recruiter_client: AsyncClient):
        response = await recruiter_client.get(
            "/dashboard/applications/create", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_recruiter_can_access_interviews_list(self, recruiter_client: AsyncClient):
        response = await recruiter_client.get(
            "/dashboard/interviews", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_recruiter_can_access_schedule_interview(self, recruiter_client: AsyncClient):
        response = await recruiter_client.get(
            "/dashboard/interviews/schedule", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_recruiter_can_access_pipeline(
        self, recruiter_client: AsyncClient, sample_job: Job
    ):
        response = await recruiter_client.get(
            f"/dashboard/jobs/{sample_job.id}/pipeline", follow_redirects=False
        )
        assert response.status_code == 200


# ─── Hiring Manager Role Tests ──────────────────────────────────────────────


class TestHiringManagerAccess:
    """Verify Hiring Manager can access permitted routes and is denied on restricted ones."""

    @pytest.mark.asyncio
    async def test_hm_can_access_dashboard(self, hiring_manager_client: AsyncClient):
        response = await hiring_manager_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_hm_can_access_jobs_list(self, hiring_manager_client: AsyncClient):
        response = await hiring_manager_client.get(
            "/dashboard/jobs", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_hm_can_access_applications_list(self, hiring_manager_client: AsyncClient):
        response = await hiring_manager_client.get(
            "/dashboard/applications", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_hm_can_access_interviews_list(self, hiring_manager_client: AsyncClient):
        response = await hiring_manager_client.get(
            "/dashboard/interviews", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_hm_cannot_access_create_candidate(self, hiring_manager_client: AsyncClient):
        """Hiring Manager should NOT be able to create candidates."""
        response = await hiring_manager_client.get(
            "/dashboard/candidates/create", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_hm_cannot_access_candidates_list(self, hiring_manager_client: AsyncClient):
        """Hiring Manager should NOT be able to access candidates list."""
        response = await hiring_manager_client.get(
            "/dashboard/candidates", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_hm_cannot_access_create_job(self, hiring_manager_client: AsyncClient):
        """Hiring Manager should NOT be able to create jobs (only System Admin and HR Recruiter)."""
        response = await hiring_manager_client.get(
            "/dashboard/jobs/create", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_hm_cannot_access_create_application(self, hiring_manager_client: AsyncClient):
        """Hiring Manager should NOT be able to create applications."""
        response = await hiring_manager_client.get(
            "/dashboard/applications/create", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_hm_cannot_access_schedule_interview(self, hiring_manager_client: AsyncClient):
        """Hiring Manager should NOT be able to schedule interviews."""
        response = await hiring_manager_client.get(
            "/dashboard/interviews/schedule", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_hm_can_access_own_job_detail(
        self, hiring_manager_client: AsyncClient, sample_job: Job
    ):
        """Hiring Manager can view their own job details."""
        response = await hiring_manager_client.get(
            f"/dashboard/jobs/{sample_job.id}", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_hm_can_access_application_detail(
        self, hiring_manager_client: AsyncClient, sample_application: Application
    ):
        response = await hiring_manager_client.get(
            f"/dashboard/applications/{sample_application.id}", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_hm_can_access_pipeline(
        self, hiring_manager_client: AsyncClient, sample_job: Job
    ):
        response = await hiring_manager_client.get(
            f"/dashboard/jobs/{sample_job.id}/pipeline", follow_redirects=False
        )
        assert response.status_code == 200


# ─── Interviewer Role Tests ─────────────────────────────────────────────────


class TestInterviewerAccess:
    """Verify Interviewer can only access interview-related routes."""

    @pytest.mark.asyncio
    async def test_interviewer_can_access_interviews_list(
        self, interviewer_client: AsyncClient
    ):
        response = await interviewer_client.get(
            "/dashboard/interviews", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_interviewer_can_access_my_interviews(
        self, interviewer_client: AsyncClient
    ):
        response = await interviewer_client.get(
            "/dashboard/interviews/my", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_interviewer_cannot_access_jobs_list(
        self, interviewer_client: AsyncClient
    ):
        """Interviewer should NOT be able to access jobs list."""
        response = await interviewer_client.get(
            "/dashboard/jobs", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_interviewer_cannot_access_create_job(
        self, interviewer_client: AsyncClient
    ):
        response = await interviewer_client.get(
            "/dashboard/jobs/create", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_interviewer_cannot_access_candidates_list(
        self, interviewer_client: AsyncClient
    ):
        response = await interviewer_client.get(
            "/dashboard/candidates", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_interviewer_cannot_access_create_candidate(
        self, interviewer_client: AsyncClient
    ):
        response = await interviewer_client.get(
            "/dashboard/candidates/create", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_interviewer_cannot_access_applications_list(
        self, interviewer_client: AsyncClient
    ):
        response = await interviewer_client.get(
            "/dashboard/applications", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_interviewer_cannot_access_create_application(
        self, interviewer_client: AsyncClient
    ):
        response = await interviewer_client.get(
            "/dashboard/applications/create", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_interviewer_cannot_access_schedule_interview(
        self, interviewer_client: AsyncClient
    ):
        response = await interviewer_client.get(
            "/dashboard/interviews/schedule", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_interviewer_cannot_access_pipeline(
        self, interviewer_client: AsyncClient, sample_job: Job
    ):
        response = await interviewer_client.get(
            f"/dashboard/jobs/{sample_job.id}/pipeline", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_interviewer_can_access_interview_detail(
        self, interviewer_client: AsyncClient, sample_interview: Interview
    ):
        response = await interviewer_client.get(
            f"/dashboard/interviews/{sample_interview.id}", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_interviewer_can_access_own_feedback_form(
        self, interviewer_client: AsyncClient, sample_interview: Interview
    ):
        response = await interviewer_client.get(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            follow_redirects=False,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_interviewer_can_access_candidate_detail(
        self, interviewer_client: AsyncClient, sample_candidate: Candidate
    ):
        """Interviewer can view candidate details (read-only)."""
        response = await interviewer_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=False
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_interviewer_can_access_application_detail(
        self, interviewer_client: AsyncClient, sample_application: Application
    ):
        """Interviewer can view application details (read-only)."""
        response = await interviewer_client.get(
            f"/dashboard/applications/{sample_application.id}", follow_redirects=False
        )
        assert response.status_code == 200


# ─── Exact Role String Matching Tests ────────────────────────────────────────


class TestExactRoleStringMatching:
    """Verify that role checks use exact string matching (Title Case with spaces)."""

    @pytest.mark.asyncio
    async def test_lowercase_role_is_not_recognized(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """A user with a lowercase role string should be denied access to admin routes."""
        user = User(
            username="lowercaseadmin",
            email="lowercaseadmin@talentflow.local",
            password_hash=hash_password("testpass123"),
            full_name="Lowercase Admin",
            role="system admin",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)

        login_response = await async_client.post(
            "/auth/login",
            data={"username": "lowercaseadmin", "password": "testpass123"},
            follow_redirects=False,
        )
        if login_response.status_code in (302, 303):
            for key, value in login_response.cookies.items():
                async_client.cookies.set(key, value)

        response = await async_client.get("/dashboard/jobs", follow_redirects=False)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_snake_case_role_is_not_recognized(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """A user with a snake_case role string should be denied access."""
        user = User(
            username="snakecaserecruiter",
            email="snakecaserecruiter@talentflow.local",
            password_hash=hash_password("testpass123"),
            full_name="Snake Case Recruiter",
            role="hr_recruiter",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)

        login_response = await async_client.post(
            "/auth/login",
            data={"username": "snakecaserecruiter", "password": "testpass123"},
            follow_redirects=False,
        )
        if login_response.status_code in (302, 303):
            for key, value in login_response.cookies.items():
                async_client.cookies.set(key, value)

        response = await async_client.get(
            "/dashboard/candidates", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_misspelled_role_is_not_recognized(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """A user with a misspelled role should be denied access."""
        user = User(
            username="misspelleduser",
            email="misspelled@talentflow.local",
            password_hash=hash_password("testpass123"),
            full_name="Misspelled User",
            role="Hiring Manger",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)

        login_response = await async_client.post(
            "/auth/login",
            data={"username": "misspelleduser", "password": "testpass123"},
            follow_redirects=False,
        )
        if login_response.status_code in (302, 303):
            for key, value in login_response.cookies.items():
                async_client.cookies.set(key, value)

        response = await async_client.get("/dashboard/jobs", follow_redirects=False)
        assert response.status_code == 403


# ─── Status Update RBAC Tests ───────────────────────────────────────────────


class TestStatusUpdateRBAC:
    """Verify role-based access for status update operations."""

    @pytest.mark.asyncio
    async def test_admin_can_update_application_status(
        self, admin_client: AsyncClient, sample_application: Application
    ):
        response = await admin_client.post(
            f"/dashboard/applications/{sample_application.id}/status",
            data={"status": "Screening"},
            follow_redirects=False,
        )
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_recruiter_can_update_application_status(
        self, recruiter_client: AsyncClient, sample_application: Application
    ):
        response = await recruiter_client.post(
            f"/dashboard/applications/{sample_application.id}/status",
            data={"status": "Screening"},
            follow_redirects=False,
        )
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_hiring_manager_can_update_application_status(
        self, hiring_manager_client: AsyncClient, sample_application: Application
    ):
        response = await hiring_manager_client.post(
            f"/dashboard/applications/{sample_application.id}/status",
            data={"status": "Screening"},
            follow_redirects=False,
        )
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_interviewer_cannot_update_application_status(
        self, interviewer_client: AsyncClient, sample_application: Application
    ):
        response = await interviewer_client.post(
            f"/dashboard/applications/{sample_application.id}/status",
            data={"status": "Screening"},
            follow_redirects=False,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_change_job_status(
        self, admin_client: AsyncClient, sample_job: Job
    ):
        response = await admin_client.post(
            f"/dashboard/jobs/{sample_job.id}/status",
            data={"status": "Closed"},
            follow_redirects=False,
        )
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_interviewer_cannot_change_job_status(
        self, interviewer_client: AsyncClient, sample_job: Job
    ):
        response = await interviewer_client.post(
            f"/dashboard/jobs/{sample_job.id}/status",
            data={"status": "Closed"},
            follow_redirects=False,
        )
        assert response.status_code == 403


# ─── Feedback Submission RBAC Tests ──────────────────────────────────────────


class TestFeedbackSubmissionRBAC:
    """Verify role-based access for interview feedback submission."""

    @pytest.mark.asyncio
    async def test_interviewer_can_submit_own_feedback(
        self, interviewer_client: AsyncClient, sample_interview: Interview
    ):
        response = await interviewer_client.post(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            data={"feedback_rating": 4, "feedback_notes": "Good candidate."},
            follow_redirects=False,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_submit_feedback(
        self, admin_client: AsyncClient, sample_interview: Interview
    ):
        response = await admin_client.post(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            data={"feedback_rating": 5, "feedback_notes": "Excellent candidate."},
            follow_redirects=False,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_recruiter_can_submit_feedback(
        self, recruiter_client: AsyncClient, sample_interview: Interview
    ):
        response = await recruiter_client.post(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            data={"feedback_rating": 3, "feedback_notes": "Average performance."},
            follow_redirects=False,
        )
        assert response.status_code == 200


# ─── Interviewer Feedback Access Control ─────────────────────────────────────


class TestInterviewerFeedbackAccessControl:
    """Verify that interviewers can only access feedback for their own interviews."""

    @pytest.mark.asyncio
    async def test_interviewer_cannot_access_other_interviewers_feedback_form(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        sample_application: Application,
    ):
        """An interviewer should not be able to access the feedback form for another interviewer's interview."""
        other_interviewer = User(
            username="otherinterviewer",
            email="otherinterviewer@talentflow.local",
            password_hash=hash_password("otherpass123"),
            full_name="Other Interviewer",
            role="Interviewer",
            is_active=True,
        )
        db_session.add(other_interviewer)
        await db_session.flush()
        await db_session.refresh(other_interviewer)

        from datetime import datetime, timedelta

        interview = Interview(
            application_id=sample_application.id,
            interviewer_id=other_interviewer.id,
            scheduled_at=datetime.utcnow() + timedelta(days=5),
        )
        db_session.add(interview)
        await db_session.flush()
        await db_session.refresh(interview)

        second_interviewer = User(
            username="secondinterviewer",
            email="secondinterviewer@talentflow.local",
            password_hash=hash_password("secondpass123"),
            full_name="Second Interviewer",
            role="Interviewer",
            is_active=True,
        )
        db_session.add(second_interviewer)
        await db_session.flush()
        await db_session.refresh(second_interviewer)

        login_response = await async_client.post(
            "/auth/login",
            data={"username": "secondinterviewer", "password": "secondpass123"},
            follow_redirects=False,
        )
        if login_response.status_code in (302, 303):
            for key, value in login_response.cookies.items():
                async_client.cookies.set(key, value)

        response = await async_client.get(
            f"/dashboard/interviews/{interview.id}/feedback",
            follow_redirects=False,
        )
        assert response.status_code == 403


# ─── Inactive User Tests ────────────────────────────────────────────────────


class TestInactiveUserAccess:
    """Verify that inactive users cannot access protected routes."""

    @pytest.mark.asyncio
    async def test_inactive_user_cannot_login(
        self, async_client: AsyncClient, inactive_user: User
    ):
        response = await async_client.post(
            "/auth/login",
            data={"username": "inactiveuser", "password": "inactivepass123"},
            follow_redirects=False,
        )
        assert response.status_code == 401


# ─── Cross-Role POST Operation Tests ────────────────────────────────────────


class TestCrossRolePOSTOperations:
    """Verify that POST operations enforce RBAC correctly."""

    @pytest.mark.asyncio
    async def test_interviewer_cannot_create_candidate_via_post(
        self, interviewer_client: AsyncClient
    ):
        response = await interviewer_client.post(
            "/dashboard/candidates",
            data={
                "first_name": "Test",
                "last_name": "Candidate",
                "email": "test.candidate@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_interviewer_cannot_create_application_via_post(
        self,
        interviewer_client: AsyncClient,
        sample_job: Job,
        sample_candidate: Candidate,
    ):
        response = await interviewer_client.post(
            "/dashboard/applications",
            data={
                "job_id": sample_job.id,
                "candidate_id": sample_candidate.id,
            },
            follow_redirects=False,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_hiring_manager_cannot_create_candidate_via_post(
        self, hiring_manager_client: AsyncClient
    ):
        response = await hiring_manager_client.post(
            "/dashboard/candidates",
            data={
                "first_name": "Test",
                "last_name": "Candidate",
                "email": "hm.candidate@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_interviewer_cannot_schedule_interview_via_post(
        self,
        interviewer_client: AsyncClient,
        sample_application: Application,
        interviewer_user: User,
    ):
        response = await interviewer_client.post(
            "/dashboard/interviews",
            data={
                "application_id": sample_application.id,
                "interviewer_id": interviewer_user.id,
                "scheduled_at": "2025-06-15T10:00:00",
            },
            follow_redirects=False,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_create_candidate_via_post(
        self, async_client: AsyncClient
    ):
        response = await async_client.post(
            "/dashboard/candidates",
            data={
                "first_name": "Anon",
                "last_name": "User",
                "email": "anon@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")


# ─── Hiring Manager Job Ownership Tests ──────────────────────────────────────


class TestHiringManagerJobOwnership:
    """Verify that Hiring Managers can only access their own jobs."""

    @pytest.mark.asyncio
    async def test_hm_cannot_view_other_managers_job(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """A Hiring Manager should not be able to view a job owned by another manager."""
        manager_a = User(
            username="managera",
            email="managera@talentflow.local",
            password_hash=hash_password("managerpass123"),
            full_name="Manager A",
            role="Hiring Manager",
            is_active=True,
        )
        db_session.add(manager_a)
        await db_session.flush()
        await db_session.refresh(manager_a)

        manager_b = User(
            username="managerb",
            email="managerb@talentflow.local",
            password_hash=hash_password("managerpass123"),
            full_name="Manager B",
            role="Hiring Manager",
            is_active=True,
        )
        db_session.add(manager_b)
        await db_session.flush()
        await db_session.refresh(manager_b)

        job = Job(
            title="Manager A's Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="A job owned by Manager A.",
            status="Published",
            hiring_manager_id=manager_a.id,
        )
        db_session.add(job)
        await db_session.flush()
        await db_session.refresh(job)

        login_response = await async_client.post(
            "/auth/login",
            data={"username": "managerb", "password": "managerpass123"},
            follow_redirects=False,
        )
        if login_response.status_code in (302, 303):
            for key, value in login_response.cookies.items():
                async_client.cookies.set(key, value)

        response = await async_client.get(
            f"/dashboard/jobs/{job.id}", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_hm_cannot_edit_other_managers_job(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """A Hiring Manager should not be able to edit a job owned by another manager."""
        manager_a = User(
            username="editmanagera",
            email="editmanagera@talentflow.local",
            password_hash=hash_password("managerpass123"),
            full_name="Edit Manager A",
            role="Hiring Manager",
            is_active=True,
        )
        db_session.add(manager_a)
        await db_session.flush()
        await db_session.refresh(manager_a)

        manager_b = User(
            username="editmanagerb",
            email="editmanagerb@talentflow.local",
            password_hash=hash_password("managerpass123"),
            full_name="Edit Manager B",
            role="Hiring Manager",
            is_active=True,
        )
        db_session.add(manager_b)
        await db_session.flush()
        await db_session.refresh(manager_b)

        job = Job(
            title="Edit Manager A's Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="A job owned by Edit Manager A.",
            status="Draft",
            hiring_manager_id=manager_a.id,
        )
        db_session.add(job)
        await db_session.flush()
        await db_session.refresh(job)

        login_response = await async_client.post(
            "/auth/login",
            data={"username": "editmanagerb", "password": "managerpass123"},
            follow_redirects=False,
        )
        if login_response.status_code in (302, 303):
            for key, value in login_response.cookies.items():
                async_client.cookies.set(key, value)

        response = await async_client.get(
            f"/dashboard/jobs/{job.id}/edit", follow_redirects=False
        )
        assert response.status_code == 403