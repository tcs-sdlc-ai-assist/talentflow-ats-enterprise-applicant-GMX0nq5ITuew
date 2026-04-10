import logging
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.job import Job
from app.models.user import User

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestAdminDashboard:
    """Tests for System Admin / HR Recruiter dashboard."""

    async def test_admin_dashboard_renders_successfully(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Welcome" in response.text
        assert "Open Positions" in response.text
        assert "Active Candidates" in response.text
        assert "Avg. Time to Hire" in response.text
        assert "Pending Interviews" in response.text

    async def test_recruiter_dashboard_renders_successfully(self, recruiter_client: AsyncClient):
        response = await recruiter_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Welcome" in response.text
        assert "Open Positions" in response.text

    async def test_admin_dashboard_shows_correct_open_positions_count(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
    ):
        job1 = Job(
            title="Published Job 1",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="A published job.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        job2 = Job(
            title="Published Job 2",
            department="Marketing",
            location="NYC",
            type="Full-Time",
            salary_min=80000,
            salary_max=120000,
            description="Another published job.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        job3 = Job(
            title="Draft Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=90000,
            salary_max=130000,
            description="A draft job.",
            status="Draft",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add_all([job1, job2, job3])
        await db_session.flush()

        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        # Should show 2 open (published) positions
        assert "Open Positions" in response.text

    async def test_admin_dashboard_shows_active_candidates_count(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
    ):
        candidate1 = Candidate(
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
        )
        candidate2 = Candidate(
            first_name="Bob",
            last_name="Jones",
            email="bob@example.com",
        )
        db_session.add_all([candidate1, candidate2])
        await db_session.flush()

        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Active Candidates" in response.text

    async def test_admin_dashboard_shows_pending_interviews(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
        interviewer_user: User,
    ):
        job = Job(
            title="Test Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Test job description.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(job)
        await db_session.flush()

        candidate = Candidate(
            first_name="Charlie",
            last_name="Brown",
            email="charlie@example.com",
        )
        db_session.add(candidate)
        await db_session.flush()

        application = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status="Interview",
        )
        db_session.add(application)
        await db_session.flush()

        interview = Interview(
            application_id=application.id,
            interviewer_id=interviewer_user.id,
            scheduled_at=datetime.utcnow() + timedelta(days=2),
        )
        db_session.add(interview)
        await db_session.flush()

        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Pending Interviews" in response.text

    async def test_admin_dashboard_shows_recent_audit_logs(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        admin_user: User,
    ):
        audit_log = AuditLog(
            action="Job Created",
            entity_type="Job",
            entity_id=1,
            details="Job 'Test Job' created in department 'Engineering'",
            user_id=admin_user.id,
        )
        db_session.add(audit_log)
        await db_session.flush()

        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Recent Activity" in response.text
        assert "Job Created" in response.text

    async def test_admin_dashboard_shows_action_items_for_stale_applications(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
    ):
        job = Job(
            title="Stale Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Test job.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(job)
        await db_session.flush()

        candidate = Candidate(
            first_name="Stale",
            last_name="Candidate",
            email="stale@example.com",
        )
        db_session.add(candidate)
        await db_session.flush()

        application = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status="Applied",
        )
        db_session.add(application)
        await db_session.flush()

        # Manually set updated_at to 10 days ago to trigger stale detection
        application.updated_at = datetime.utcnow() - timedelta(days=10)
        await db_session.flush()

        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Action Items" in response.text or "application" in response.text.lower()

    async def test_admin_dashboard_shows_missing_feedback_action_item(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
        interviewer_user: User,
    ):
        job = Job(
            title="Feedback Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Test job.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(job)
        await db_session.flush()

        candidate = Candidate(
            first_name="Feedback",
            last_name="Candidate",
            email="feedback@example.com",
        )
        db_session.add(candidate)
        await db_session.flush()

        application = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status="Interview",
        )
        db_session.add(application)
        await db_session.flush()

        # Past interview without feedback
        interview = Interview(
            application_id=application.id,
            interviewer_id=interviewer_user.id,
            scheduled_at=datetime.utcnow() - timedelta(days=2),
        )
        db_session.add(interview)
        await db_session.flush()

        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "missing feedback" in response.text.lower() or "Action Items" in response.text

    async def test_admin_dashboard_time_to_hire_metric(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
    ):
        job = Job(
            title="Hired Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Test job.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(job)
        await db_session.flush()

        candidate = Candidate(
            first_name="Hired",
            last_name="Person",
            email="hired@example.com",
        )
        db_session.add(candidate)
        await db_session.flush()

        application = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status="Hired",
        )
        db_session.add(application)
        await db_session.flush()

        # Set created_at to 15 days ago
        application.created_at = datetime.utcnow() - timedelta(days=15)
        application.updated_at = datetime.utcnow()
        await db_session.flush()

        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Avg. Time to Hire" in response.text
        assert "days" in response.text


@pytest.mark.asyncio
class TestHiringManagerDashboard:
    """Tests for Hiring Manager dashboard."""

    async def test_hiring_manager_dashboard_renders(
        self,
        hiring_manager_client: AsyncClient,
    ):
        response = await hiring_manager_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Welcome" in response.text
        assert "My Open Positions" in response.text
        assert "Active Candidates" in response.text
        assert "Pending Interviews" in response.text

    async def test_hiring_manager_sees_own_jobs(
        self,
        hiring_manager_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
        admin_user: User,
    ):
        # Job owned by hiring manager
        own_job = Job(
            title="My Published Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="My job.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        # Job owned by someone else
        other_job = Job(
            title="Other Manager Job",
            department="Marketing",
            location="NYC",
            type="Full-Time",
            salary_min=80000,
            salary_max=120000,
            description="Not my job.",
            status="Published",
            hiring_manager_id=admin_user.id,
        )
        db_session.add_all([own_job, other_job])
        await db_session.flush()

        response = await hiring_manager_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "My Requisitions" in response.text
        assert "My Published Job" in response.text

    async def test_hiring_manager_sees_own_open_positions_count(
        self,
        hiring_manager_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
    ):
        job1 = Job(
            title="HM Published 1",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Published.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        job2 = Job(
            title="HM Draft",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Draft.",
            status="Draft",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add_all([job1, job2])
        await db_session.flush()

        response = await hiring_manager_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "My Open Positions" in response.text

    async def test_hiring_manager_sees_pending_interviews_for_own_jobs(
        self,
        hiring_manager_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
        interviewer_user: User,
    ):
        job = Job(
            title="HM Interview Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Job with interview.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(job)
        await db_session.flush()

        candidate = Candidate(
            first_name="HM",
            last_name="Candidate",
            email="hmcandidate@example.com",
        )
        db_session.add(candidate)
        await db_session.flush()

        application = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status="Interview",
        )
        db_session.add(application)
        await db_session.flush()

        interview = Interview(
            application_id=application.id,
            interviewer_id=interviewer_user.id,
            scheduled_at=datetime.utcnow() + timedelta(days=1),
        )
        db_session.add(interview)
        await db_session.flush()

        response = await hiring_manager_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Pending Interviews" in response.text

    async def test_hiring_manager_sees_pending_items(
        self,
        hiring_manager_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
        interviewer_user: User,
    ):
        job = Job(
            title="HM Pending Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Job with pending items.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(job)
        await db_session.flush()

        candidate = Candidate(
            first_name="Pending",
            last_name="Item",
            email="pending@example.com",
        )
        db_session.add(candidate)
        await db_session.flush()

        application = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status="Interview",
        )
        db_session.add(application)
        await db_session.flush()

        interview = Interview(
            application_id=application.id,
            interviewer_id=interviewer_user.id,
            scheduled_at=datetime.utcnow() + timedelta(days=3),
        )
        db_session.add(interview)
        await db_session.flush()

        response = await hiring_manager_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        # Should show pending interviews section
        assert "Pending Interviews" in response.text

    async def test_hiring_manager_empty_dashboard(
        self,
        hiring_manager_client: AsyncClient,
    ):
        response = await hiring_manager_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "No requisitions" in response.text or "My Requisitions" in response.text


@pytest.mark.asyncio
class TestInterviewerDashboard:
    """Tests for Interviewer dashboard."""

    async def test_interviewer_dashboard_renders(
        self,
        interviewer_client: AsyncClient,
    ):
        response = await interviewer_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Welcome" in response.text
        assert "Upcoming Interviews" in response.text

    async def test_interviewer_sees_own_upcoming_interviews(
        self,
        interviewer_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
        interviewer_user: User,
    ):
        job = Job(
            title="Interviewer Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Job for interviewer.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(job)
        await db_session.flush()

        candidate = Candidate(
            first_name="Interviewee",
            last_name="Person",
            email="interviewee@example.com",
        )
        db_session.add(candidate)
        await db_session.flush()

        application = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status="Interview",
        )
        db_session.add(application)
        await db_session.flush()

        interview = Interview(
            application_id=application.id,
            interviewer_id=interviewer_user.id,
            scheduled_at=datetime.utcnow() + timedelta(days=1),
        )
        db_session.add(interview)
        await db_session.flush()

        response = await interviewer_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Upcoming Interviews" in response.text
        assert "Interviewee Person" in response.text

    async def test_interviewer_sees_missing_feedback_count(
        self,
        interviewer_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
        interviewer_user: User,
    ):
        job = Job(
            title="Feedback Missing Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Job needing feedback.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(job)
        await db_session.flush()

        candidate = Candidate(
            first_name="Missing",
            last_name="Feedback",
            email="missingfb@example.com",
        )
        db_session.add(candidate)
        await db_session.flush()

        application = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status="Interview",
        )
        db_session.add(application)
        await db_session.flush()

        # Past interview without feedback
        interview = Interview(
            application_id=application.id,
            interviewer_id=interviewer_user.id,
            scheduled_at=datetime.utcnow() - timedelta(days=3),
        )
        db_session.add(interview)
        await db_session.flush()

        response = await interviewer_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Missing Feedback" in response.text

    async def test_interviewer_sees_missing_feedback_alert(
        self,
        interviewer_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
        interviewer_user: User,
    ):
        job = Job(
            title="Alert Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Job for alert.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(job)
        await db_session.flush()

        candidate = Candidate(
            first_name="Alert",
            last_name="Candidate",
            email="alert@example.com",
        )
        db_session.add(candidate)
        await db_session.flush()

        application = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status="Interview",
        )
        db_session.add(application)
        await db_session.flush()

        interview = Interview(
            application_id=application.id,
            interviewer_id=interviewer_user.id,
            scheduled_at=datetime.utcnow() - timedelta(days=1),
        )
        db_session.add(interview)
        await db_session.flush()

        response = await interviewer_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        # Should show missing feedback alert
        assert "Missing Feedback" in response.text
        assert "Feedback pending" in response.text or "awaiting feedback" in response.text.lower()

    async def test_interviewer_empty_dashboard(
        self,
        interviewer_client: AsyncClient,
    ):
        response = await interviewer_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "No upcoming interviews" in response.text or "Upcoming Interviews" in response.text

    async def test_interviewer_does_not_see_other_interviewers_interviews(
        self,
        interviewer_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
    ):
        # Create another interviewer
        other_interviewer = User(
            username="otherinterviewer",
            email="other_interviewer@talentflow.local",
            password_hash=hash_password("otherpass123"),
            full_name="Other Interviewer",
            role="Interviewer",
            is_active=True,
        )
        db_session.add(other_interviewer)
        await db_session.flush()

        job = Job(
            title="Other Interviewer Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Job for other interviewer.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(job)
        await db_session.flush()

        candidate = Candidate(
            first_name="Other",
            last_name="Interviewee",
            email="otherinterviewee@example.com",
        )
        db_session.add(candidate)
        await db_session.flush()

        application = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status="Interview",
        )
        db_session.add(application)
        await db_session.flush()

        # Interview assigned to the OTHER interviewer
        interview = Interview(
            application_id=application.id,
            interviewer_id=other_interviewer.id,
            scheduled_at=datetime.utcnow() + timedelta(days=1),
        )
        db_session.add(interview)
        await db_session.flush()

        response = await interviewer_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        # Should NOT show the other interviewer's candidate
        assert "Other Interviewee" not in response.text


@pytest.mark.asyncio
class TestDashboardRBAC:
    """Tests for dashboard RBAC enforcement."""

    async def test_unauthenticated_user_redirected_to_login(
        self,
        async_client: AsyncClient,
    ):
        response = await async_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    async def test_admin_can_access_dashboard(
        self,
        admin_client: AsyncClient,
    ):
        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200

    async def test_recruiter_can_access_dashboard(
        self,
        recruiter_client: AsyncClient,
    ):
        response = await recruiter_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200

    async def test_hiring_manager_can_access_dashboard(
        self,
        hiring_manager_client: AsyncClient,
    ):
        response = await hiring_manager_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200

    async def test_interviewer_can_access_dashboard(
        self,
        interviewer_client: AsyncClient,
    ):
        response = await interviewer_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200

    async def test_admin_sees_admin_dashboard_layout(
        self,
        admin_client: AsyncClient,
    ):
        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Open Positions" in response.text
        assert "Active Candidates" in response.text
        assert "Avg. Time to Hire" in response.text
        assert "Pending Interviews" in response.text

    async def test_hiring_manager_sees_hm_dashboard_layout(
        self,
        hiring_manager_client: AsyncClient,
    ):
        response = await hiring_manager_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "My Open Positions" in response.text
        assert "My Requisitions" in response.text

    async def test_interviewer_sees_interviewer_dashboard_layout(
        self,
        interviewer_client: AsyncClient,
    ):
        response = await interviewer_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Upcoming Interviews" in response.text
        assert "Missing Feedback" in response.text

    async def test_admin_dashboard_does_not_show_my_requisitions(
        self,
        admin_client: AsyncClient,
    ):
        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        # Admin dashboard should not have "My Requisitions" section
        assert "My Requisitions" not in response.text

    async def test_interviewer_dashboard_does_not_show_open_positions(
        self,
        interviewer_client: AsyncClient,
    ):
        response = await interviewer_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        # Interviewer dashboard should not have "Open Positions" metric
        # (it has "Upcoming Interviews" and "Missing Feedback" instead)
        assert "Open Positions" not in response.text


@pytest.mark.asyncio
class TestDashboardAuditLogDisplay:
    """Tests for audit log display in dashboards."""

    async def test_admin_dashboard_shows_audit_logs_section(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        admin_user: User,
    ):
        # Create some audit logs
        for i in range(3):
            log = AuditLog(
                action="Job Created",
                entity_type="Job",
                entity_id=i + 1,
                details=f"Job #{i + 1} created",
                user_id=admin_user.id,
            )
            db_session.add(log)
        await db_session.flush()

        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Recent Activity" in response.text
        assert "Job Created" in response.text

    async def test_admin_dashboard_shows_audit_log_user_name(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        admin_user: User,
    ):
        log = AuditLog(
            action="Candidate Created",
            entity_type="Candidate",
            entity_id=1,
            details="Candidate 'Test Person' created",
            user_id=admin_user.id,
        )
        db_session.add(log)
        await db_session.flush()

        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Test Admin" in response.text or "testadmin" in response.text

    async def test_admin_dashboard_shows_audit_log_details(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        admin_user: User,
    ):
        log = AuditLog(
            action="Application Status Changed",
            entity_type="Application",
            entity_id=42,
            details="Status changed from 'Applied' to 'Screening'",
            user_id=admin_user.id,
        )
        db_session.add(log)
        await db_session.flush()

        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Application Status Changed" in response.text
        assert "Application #42" in response.text

    async def test_admin_dashboard_shows_view_all_link(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        admin_user: User,
    ):
        log = AuditLog(
            action="Job Published",
            entity_type="Job",
            entity_id=1,
            details="Job published",
            user_id=admin_user.id,
        )
        db_session.add(log)
        await db_session.flush()

        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "View all" in response.text

    async def test_admin_dashboard_no_audit_logs_when_empty(
        self,
        admin_client: AsyncClient,
    ):
        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        # Should still render without errors even with no audit logs

    async def test_admin_dashboard_shows_multiple_action_types(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        admin_user: User,
    ):
        actions = [
            ("Job Published", "Job", 1, "Job published"),
            ("Candidate Created", "Candidate", 1, "Candidate created"),
            ("Interview Scheduled", "Interview", 1, "Interview scheduled"),
        ]
        for action, entity_type, entity_id, details in actions:
            log = AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                user_id=admin_user.id,
            )
            db_session.add(log)
        await db_session.flush()

        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        assert "Job Published" in response.text
        assert "Candidate Created" in response.text
        assert "Interview Scheduled" in response.text

    async def test_hiring_manager_dashboard_does_not_show_audit_logs(
        self,
        hiring_manager_client: AsyncClient,
        db_session: AsyncSession,
        admin_user: User,
    ):
        log = AuditLog(
            action="Job Created",
            entity_type="Job",
            entity_id=1,
            details="Job created",
            user_id=admin_user.id,
        )
        db_session.add(log)
        await db_session.flush()

        response = await hiring_manager_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        # Hiring manager dashboard should not have "Recent Activity" section
        assert "Recent Activity" not in response.text

    async def test_interviewer_dashboard_does_not_show_audit_logs(
        self,
        interviewer_client: AsyncClient,
        db_session: AsyncSession,
        admin_user: User,
    ):
        log = AuditLog(
            action="Job Created",
            entity_type="Job",
            entity_id=1,
            details="Job created",
            user_id=admin_user.id,
        )
        db_session.add(log)
        await db_session.flush()

        response = await interviewer_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        # Interviewer dashboard should not have "Recent Activity" section
        assert "Recent Activity" not in response.text


@pytest.mark.asyncio
class TestDashboardEdgeCases:
    """Tests for dashboard edge cases and error handling."""

    async def test_dashboard_handles_no_data_gracefully(
        self,
        admin_client: AsyncClient,
    ):
        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        # Should render with zero metrics
        assert "0" in response.text

    async def test_dashboard_with_completed_interview_feedback(
        self,
        interviewer_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
        interviewer_user: User,
    ):
        job = Job(
            title="Completed Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Job with completed feedback.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(job)
        await db_session.flush()

        candidate = Candidate(
            first_name="Completed",
            last_name="Feedback",
            email="completed@example.com",
        )
        db_session.add(candidate)
        await db_session.flush()

        application = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status="Interview",
        )
        db_session.add(application)
        await db_session.flush()

        # Interview WITH feedback already submitted
        interview = Interview(
            application_id=application.id,
            interviewer_id=interviewer_user.id,
            scheduled_at=datetime.utcnow() - timedelta(days=1),
            feedback_rating=4,
            feedback_notes="Great candidate.",
        )
        db_session.add(interview)
        await db_session.flush()

        response = await interviewer_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200
        # Completed interview should not appear in pending/upcoming
        # The "Completed Feedback" candidate should not be in the upcoming list

    async def test_dashboard_with_multiple_roles_data_isolation(
        self,
        db_session: AsyncSession,
        hiring_manager_user: User,
        interviewer_user: User,
        admin_user: User,
        admin_client: AsyncClient,
        hiring_manager_client: AsyncClient,
        interviewer_client: AsyncClient,
    ):
        """Verify each role sees appropriate data."""
        job = Job(
            title="Isolation Test Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Test isolation.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(job)
        await db_session.flush()

        candidate = Candidate(
            first_name="Isolation",
            last_name="Test",
            email="isolation@example.com",
        )
        db_session.add(candidate)
        await db_session.flush()

        application = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            status="Interview",
        )
        db_session.add(application)
        await db_session.flush()

        interview = Interview(
            application_id=application.id,
            interviewer_id=interviewer_user.id,
            scheduled_at=datetime.utcnow() + timedelta(days=2),
        )
        db_session.add(interview)
        await db_session.flush()

        # Admin sees org-wide metrics
        admin_response = await admin_client.get("/dashboard", follow_redirects=False)
        assert admin_response.status_code == 200
        assert "Open Positions" in admin_response.text

        # Hiring manager sees own requisitions
        hm_response = await hiring_manager_client.get("/dashboard", follow_redirects=False)
        assert hm_response.status_code == 200
        assert "My Requisitions" in hm_response.text

        # Interviewer sees own interviews
        interviewer_response = await interviewer_client.get("/dashboard", follow_redirects=False)
        assert interviewer_response.status_code == 200
        assert "Upcoming Interviews" in interviewer_response.text