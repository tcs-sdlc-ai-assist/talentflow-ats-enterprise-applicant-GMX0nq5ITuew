import logging
from datetime import datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.user import User
from app.core.security import hash_password

logger = logging.getLogger(__name__)


class TestJobListPage:
    """Tests for GET /dashboard/jobs — job listing page."""

    async def test_unauthenticated_redirects_to_login(self, async_client: AsyncClient):
        response = await async_client.get("/dashboard/jobs", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["location"]

    async def test_admin_can_view_jobs_list(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard/jobs", follow_redirects=False)
        assert response.status_code == 200
        assert b"Job Requisitions" in response.content

    async def test_recruiter_can_view_jobs_list(self, recruiter_client: AsyncClient):
        response = await recruiter_client.get("/dashboard/jobs", follow_redirects=False)
        assert response.status_code == 200
        assert b"Job Requisitions" in response.content

    async def test_hiring_manager_can_view_jobs_list(self, hiring_manager_client: AsyncClient):
        response = await hiring_manager_client.get("/dashboard/jobs", follow_redirects=False)
        assert response.status_code == 200
        assert b"Job Requisitions" in response.content

    async def test_interviewer_cannot_view_jobs_list(self, interviewer_client: AsyncClient):
        response = await interviewer_client.get("/dashboard/jobs", follow_redirects=False)
        assert response.status_code == 403

    async def test_jobs_list_shows_existing_jobs(
        self, admin_client: AsyncClient, sample_job: Job
    ):
        response = await admin_client.get("/dashboard/jobs", follow_redirects=False)
        assert response.status_code == 200
        assert b"Senior Backend Engineer" in response.content

    async def test_jobs_list_filter_by_status(
        self, admin_client: AsyncClient, sample_job: Job
    ):
        response = await admin_client.get(
            "/dashboard/jobs?status=Published", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Senior Backend Engineer" in response.content

    async def test_jobs_list_filter_by_status_no_results(
        self, admin_client: AsyncClient, sample_job: Job
    ):
        response = await admin_client.get(
            "/dashboard/jobs?status=Closed", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Senior Backend Engineer" not in response.content

    async def test_jobs_list_filter_by_department(
        self, admin_client: AsyncClient, sample_job: Job
    ):
        response = await admin_client.get(
            "/dashboard/jobs?department=Engineering", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Senior Backend Engineer" in response.content

    async def test_jobs_list_search_by_title(
        self, admin_client: AsyncClient, sample_job: Job
    ):
        response = await admin_client.get(
            "/dashboard/jobs?search=Backend", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Senior Backend Engineer" in response.content

    async def test_jobs_list_search_no_match(
        self, admin_client: AsyncClient, sample_job: Job
    ):
        response = await admin_client.get(
            "/dashboard/jobs?search=NonExistentJobTitle", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Senior Backend Engineer" not in response.content

    async def test_hiring_manager_sees_only_own_jobs(
        self,
        hiring_manager_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
        admin_user: User,
    ):
        own_job = Job(
            title="HM Own Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="A job owned by the hiring manager.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        other_job = Job(
            title="Other Manager Job",
            department="Sales",
            location="NYC",
            type="Full-Time",
            salary_min=80000,
            salary_max=120000,
            description="A job owned by another manager.",
            status="Published",
            hiring_manager_id=admin_user.id,
        )
        db_session.add(own_job)
        db_session.add(other_job)
        await db_session.flush()

        response = await hiring_manager_client.get(
            "/dashboard/jobs", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"HM Own Job" in response.content
        assert b"Other Manager Job" not in response.content


class TestJobCreateForm:
    """Tests for GET /dashboard/jobs/create — job creation form."""

    async def test_unauthenticated_redirects_to_login(self, async_client: AsyncClient):
        response = await async_client.get(
            "/dashboard/jobs/create", follow_redirects=False
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers["location"]

    async def test_admin_can_access_create_form(self, admin_client: AsyncClient):
        response = await admin_client.get(
            "/dashboard/jobs/create", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Create New Job" in response.content

    async def test_recruiter_can_access_create_form(self, recruiter_client: AsyncClient):
        response = await recruiter_client.get(
            "/dashboard/jobs/create", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Create New Job" in response.content

    async def test_hiring_manager_cannot_access_create_form(
        self, hiring_manager_client: AsyncClient
    ):
        response = await hiring_manager_client.get(
            "/dashboard/jobs/create", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_interviewer_cannot_access_create_form(
        self, interviewer_client: AsyncClient
    ):
        response = await interviewer_client.get(
            "/dashboard/jobs/create", follow_redirects=False
        )
        assert response.status_code == 403


class TestJobCreate:
    """Tests for POST /dashboard/jobs — job creation."""

    async def test_admin_can_create_job(
        self,
        admin_client: AsyncClient,
        hiring_manager_user: User,
    ):
        response = await admin_client.post(
            "/dashboard/jobs",
            data={
                "title": "Frontend Developer",
                "department": "Engineering",
                "location": "San Francisco, CA",
                "type": "Full-Time",
                "salary_min": "100000",
                "salary_max": "150000",
                "description": "Build amazing user interfaces.",
                "hiring_manager_id": str(hiring_manager_user.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard/jobs/" in response.headers["location"]

    async def test_recruiter_can_create_job(
        self,
        recruiter_client: AsyncClient,
        hiring_manager_user: User,
    ):
        response = await recruiter_client.post(
            "/dashboard/jobs",
            data={
                "title": "Data Analyst",
                "department": "Product",
                "location": "Remote",
                "type": "Full-Time",
                "salary_min": "80000",
                "salary_max": "120000",
                "description": "Analyze product data and provide insights.",
                "hiring_manager_id": str(hiring_manager_user.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard/jobs/" in response.headers["location"]

    async def test_hiring_manager_cannot_create_job(
        self,
        hiring_manager_client: AsyncClient,
        hiring_manager_user: User,
    ):
        response = await hiring_manager_client.post(
            "/dashboard/jobs",
            data={
                "title": "Some Job",
                "department": "Engineering",
                "location": "Remote",
                "type": "Full-Time",
                "salary_min": "50000",
                "salary_max": "80000",
                "description": "A job description.",
                "hiring_manager_id": str(hiring_manager_user.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_interviewer_cannot_create_job(
        self,
        interviewer_client: AsyncClient,
        hiring_manager_user: User,
    ):
        response = await interviewer_client.post(
            "/dashboard/jobs",
            data={
                "title": "Some Job",
                "department": "Engineering",
                "location": "Remote",
                "type": "Full-Time",
                "salary_min": "50000",
                "salary_max": "80000",
                "description": "A job description.",
                "hiring_manager_id": str(hiring_manager_user.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_created_job_has_draft_status(
        self,
        admin_client: AsyncClient,
        hiring_manager_user: User,
        db_session: AsyncSession,
    ):
        response = await admin_client.post(
            "/dashboard/jobs",
            data={
                "title": "Draft Status Job",
                "department": "Engineering",
                "location": "Remote",
                "type": "Full-Time",
                "salary_min": "90000",
                "salary_max": "130000",
                "description": "This job should start as Draft.",
                "hiring_manager_id": str(hiring_manager_user.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

        result = await db_session.execute(
            select(Job).where(Job.title == "Draft Status Job")
        )
        job = result.scalars().first()
        assert job is not None
        assert job.status == "Draft"

    async def test_create_job_missing_title_returns_error(
        self,
        admin_client: AsyncClient,
        hiring_manager_user: User,
    ):
        response = await admin_client.post(
            "/dashboard/jobs",
            data={
                "title": "",
                "department": "Engineering",
                "location": "Remote",
                "type": "Full-Time",
                "salary_min": "90000",
                "salary_max": "130000",
                "description": "Missing title.",
                "hiring_manager_id": str(hiring_manager_user.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 422
        assert b"Title is required" in response.content

    async def test_create_job_salary_max_less_than_min_returns_error(
        self,
        admin_client: AsyncClient,
        hiring_manager_user: User,
    ):
        response = await admin_client.post(
            "/dashboard/jobs",
            data={
                "title": "Bad Salary Job",
                "department": "Engineering",
                "location": "Remote",
                "type": "Full-Time",
                "salary_min": "150000",
                "salary_max": "100000",
                "description": "Salary max is less than min.",
                "hiring_manager_id": str(hiring_manager_user.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 422
        assert b"Maximum salary must be greater than or equal to minimum salary" in response.content

    async def test_create_job_missing_description_returns_error(
        self,
        admin_client: AsyncClient,
        hiring_manager_user: User,
    ):
        response = await admin_client.post(
            "/dashboard/jobs",
            data={
                "title": "No Description Job",
                "department": "Engineering",
                "location": "Remote",
                "type": "Full-Time",
                "salary_min": "90000",
                "salary_max": "130000",
                "description": "",
                "hiring_manager_id": str(hiring_manager_user.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 422
        assert b"Description is required" in response.content

    async def test_unauthenticated_create_redirects_to_login(
        self, async_client: AsyncClient
    ):
        response = await async_client.post(
            "/dashboard/jobs",
            data={
                "title": "Test",
                "department": "Engineering",
                "location": "Remote",
                "type": "Full-Time",
                "salary_min": "50000",
                "salary_max": "80000",
                "description": "Test",
                "hiring_manager_id": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers["location"]


class TestJobDetail:
    """Tests for GET /dashboard/jobs/{job_id} — job detail page."""

    async def test_admin_can_view_job_detail(
        self, admin_client: AsyncClient, sample_job: Job
    ):
        response = await admin_client.get(
            f"/dashboard/jobs/{sample_job.id}", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Senior Backend Engineer" in response.content

    async def test_recruiter_can_view_job_detail(
        self, recruiter_client: AsyncClient, sample_job: Job
    ):
        response = await recruiter_client.get(
            f"/dashboard/jobs/{sample_job.id}", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Senior Backend Engineer" in response.content

    async def test_hiring_manager_can_view_own_job(
        self, hiring_manager_client: AsyncClient, sample_job: Job
    ):
        response = await hiring_manager_client.get(
            f"/dashboard/jobs/{sample_job.id}", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Senior Backend Engineer" in response.content

    async def test_hiring_manager_cannot_view_other_job(
        self,
        hiring_manager_client: AsyncClient,
        db_session: AsyncSession,
        admin_user: User,
    ):
        other_job = Job(
            title="Other Job",
            department="Sales",
            location="NYC",
            type="Full-Time",
            salary_min=60000,
            salary_max=90000,
            description="Not owned by hiring manager.",
            status="Published",
            hiring_manager_id=admin_user.id,
        )
        db_session.add(other_job)
        await db_session.flush()
        await db_session.refresh(other_job)

        response = await hiring_manager_client.get(
            f"/dashboard/jobs/{other_job.id}", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_interviewer_can_view_job_detail(
        self, interviewer_client: AsyncClient, sample_job: Job
    ):
        response = await interviewer_client.get(
            f"/dashboard/jobs/{sample_job.id}", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Senior Backend Engineer" in response.content

    async def test_nonexistent_job_returns_404(self, admin_client: AsyncClient):
        response = await admin_client.get(
            "/dashboard/jobs/99999", follow_redirects=False
        )
        assert response.status_code == 404

    async def test_unauthenticated_redirects_to_login(
        self, async_client: AsyncClient, sample_job: Job
    ):
        response = await async_client.get(
            f"/dashboard/jobs/{sample_job.id}", follow_redirects=False
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers["location"]

    async def test_job_detail_shows_pipeline_link(
        self, admin_client: AsyncClient, sample_job: Job
    ):
        response = await admin_client.get(
            f"/dashboard/jobs/{sample_job.id}", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"View Kanban Pipeline" in response.content


class TestJobEdit:
    """Tests for GET /dashboard/jobs/{job_id}/edit and POST /dashboard/jobs/{job_id}."""

    async def test_admin_can_access_edit_form(
        self, admin_client: AsyncClient, sample_job: Job
    ):
        response = await admin_client.get(
            f"/dashboard/jobs/{sample_job.id}/edit", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Edit Job" in response.content

    async def test_recruiter_can_access_edit_form(
        self, recruiter_client: AsyncClient, sample_job: Job
    ):
        response = await recruiter_client.get(
            f"/dashboard/jobs/{sample_job.id}/edit", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Edit Job" in response.content

    async def test_hiring_manager_can_edit_own_job_form(
        self, hiring_manager_client: AsyncClient, sample_job: Job
    ):
        response = await hiring_manager_client.get(
            f"/dashboard/jobs/{sample_job.id}/edit", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Edit Job" in response.content

    async def test_hiring_manager_cannot_edit_other_job_form(
        self,
        hiring_manager_client: AsyncClient,
        db_session: AsyncSession,
        admin_user: User,
    ):
        other_job = Job(
            title="Other Job Edit",
            department="Marketing",
            location="LA",
            type="Part-Time",
            salary_min=40000,
            salary_max=60000,
            description="Not owned by HM.",
            status="Draft",
            hiring_manager_id=admin_user.id,
        )
        db_session.add(other_job)
        await db_session.flush()
        await db_session.refresh(other_job)

        response = await hiring_manager_client.get(
            f"/dashboard/jobs/{other_job.id}/edit", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_interviewer_cannot_access_edit_form(
        self, interviewer_client: AsyncClient, sample_job: Job
    ):
        response = await interviewer_client.get(
            f"/dashboard/jobs/{sample_job.id}/edit", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_admin_can_update_job(
        self,
        admin_client: AsyncClient,
        sample_job: Job,
        hiring_manager_user: User,
        db_session: AsyncSession,
    ):
        response = await admin_client.post(
            f"/dashboard/jobs/{sample_job.id}",
            data={
                "title": "Updated Backend Engineer",
                "department": "Engineering",
                "location": "Hybrid",
                "type": "Full-Time",
                "salary_min": "130000",
                "salary_max": "190000",
                "description": "Updated description for the role.",
                "hiring_manager_id": str(hiring_manager_user.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert f"/dashboard/jobs/{sample_job.id}" in response.headers["location"]

        await db_session.refresh(sample_job)
        assert sample_job.title == "Updated Backend Engineer"
        assert sample_job.location == "Hybrid"
        assert sample_job.salary_min == 130000
        assert sample_job.salary_max == 190000

    async def test_hiring_manager_can_update_own_job(
        self,
        hiring_manager_client: AsyncClient,
        sample_job: Job,
        hiring_manager_user: User,
        db_session: AsyncSession,
    ):
        response = await hiring_manager_client.post(
            f"/dashboard/jobs/{sample_job.id}",
            data={
                "title": "HM Updated Job",
                "department": "Engineering",
                "location": "Remote",
                "type": "Full-Time",
                "salary_min": "120000",
                "salary_max": "180000",
                "description": "Updated by hiring manager.",
                "hiring_manager_id": str(hiring_manager_user.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

        await db_session.refresh(sample_job)
        assert sample_job.title == "HM Updated Job"

    async def test_hiring_manager_cannot_update_other_job(
        self,
        hiring_manager_client: AsyncClient,
        db_session: AsyncSession,
        admin_user: User,
        hiring_manager_user: User,
    ):
        other_job = Job(
            title="Other Job Update",
            department="Finance",
            location="Chicago",
            type="Full-Time",
            salary_min=70000,
            salary_max=100000,
            description="Not owned by HM.",
            status="Draft",
            hiring_manager_id=admin_user.id,
        )
        db_session.add(other_job)
        await db_session.flush()
        await db_session.refresh(other_job)

        response = await hiring_manager_client.post(
            f"/dashboard/jobs/{other_job.id}",
            data={
                "title": "Attempted Update",
                "department": "Finance",
                "location": "Chicago",
                "type": "Full-Time",
                "salary_min": "70000",
                "salary_max": "100000",
                "description": "Should not be allowed.",
                "hiring_manager_id": str(hiring_manager_user.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_update_job_validation_error(
        self,
        admin_client: AsyncClient,
        sample_job: Job,
        hiring_manager_user: User,
    ):
        response = await admin_client.post(
            f"/dashboard/jobs/{sample_job.id}",
            data={
                "title": "",
                "department": "Engineering",
                "location": "Remote",
                "type": "Full-Time",
                "salary_min": "120000",
                "salary_max": "180000",
                "description": "Valid description.",
                "hiring_manager_id": str(hiring_manager_user.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 422
        assert b"Title is required" in response.content

    async def test_update_nonexistent_job_returns_404(
        self, admin_client: AsyncClient, hiring_manager_user: User
    ):
        response = await admin_client.post(
            "/dashboard/jobs/99999",
            data={
                "title": "Ghost Job",
                "department": "Engineering",
                "location": "Remote",
                "type": "Full-Time",
                "salary_min": "50000",
                "salary_max": "80000",
                "description": "Does not exist.",
                "hiring_manager_id": str(hiring_manager_user.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 404


class TestJobStatusTransitions:
    """Tests for POST /dashboard/jobs/{job_id}/status — status transitions."""

    async def test_publish_draft_job(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
    ):
        draft_job = Job(
            title="Draft to Publish",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="A draft job to be published.",
            status="Draft",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(draft_job)
        await db_session.flush()
        await db_session.refresh(draft_job)

        response = await admin_client.post(
            f"/dashboard/jobs/{draft_job.id}/status",
            data={"status": "Published"},
            follow_redirects=False,
        )
        assert response.status_code == 302

        await db_session.refresh(draft_job)
        assert draft_job.status == "Published"

    async def test_close_published_job(
        self,
        admin_client: AsyncClient,
        sample_job: Job,
        db_session: AsyncSession,
    ):
        assert sample_job.status == "Published"

        response = await admin_client.post(
            f"/dashboard/jobs/{sample_job.id}/status",
            data={"status": "Closed"},
            follow_redirects=False,
        )
        assert response.status_code == 302

        await db_session.refresh(sample_job)
        assert sample_job.status == "Closed"

    async def test_reopen_closed_job_to_draft(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
    ):
        closed_job = Job(
            title="Closed Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="A closed job.",
            status="Closed",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(closed_job)
        await db_session.flush()
        await db_session.refresh(closed_job)

        response = await admin_client.post(
            f"/dashboard/jobs/{closed_job.id}/status",
            data={"status": "Draft"},
            follow_redirects=False,
        )
        assert response.status_code == 302

        await db_session.refresh(closed_job)
        assert closed_job.status == "Draft"

    async def test_invalid_transition_draft_to_closed_is_allowed(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
    ):
        draft_job = Job(
            title="Draft to Close",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Draft job to close directly.",
            status="Draft",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(draft_job)
        await db_session.flush()
        await db_session.refresh(draft_job)

        response = await admin_client.post(
            f"/dashboard/jobs/{draft_job.id}/status",
            data={"status": "Closed"},
            follow_redirects=False,
        )
        assert response.status_code == 302

        await db_session.refresh(draft_job)
        assert draft_job.status == "Closed"

    async def test_invalid_transition_closed_to_published(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
    ):
        closed_job = Job(
            title="Closed No Publish",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="Cannot go from Closed to Published.",
            status="Closed",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(closed_job)
        await db_session.flush()
        await db_session.refresh(closed_job)

        response = await admin_client.post(
            f"/dashboard/jobs/{closed_job.id}/status",
            data={"status": "Published"},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_invalid_status_value(
        self,
        admin_client: AsyncClient,
        sample_job: Job,
    ):
        response = await admin_client.post(
            f"/dashboard/jobs/{sample_job.id}/status",
            data={"status": "Archived"},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_hiring_manager_can_change_own_job_status(
        self,
        hiring_manager_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
    ):
        draft_job = Job(
            title="HM Draft Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="HM's draft job.",
            status="Draft",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(draft_job)
        await db_session.flush()
        await db_session.refresh(draft_job)

        response = await hiring_manager_client.post(
            f"/dashboard/jobs/{draft_job.id}/status",
            data={"status": "Published"},
            follow_redirects=False,
        )
        assert response.status_code == 302

        await db_session.refresh(draft_job)
        assert draft_job.status == "Published"

    async def test_hiring_manager_cannot_change_other_job_status(
        self,
        hiring_manager_client: AsyncClient,
        db_session: AsyncSession,
        admin_user: User,
    ):
        other_job = Job(
            title="Other HM Job Status",
            department="Sales",
            location="NYC",
            type="Full-Time",
            salary_min=60000,
            salary_max=90000,
            description="Not owned by HM.",
            status="Draft",
            hiring_manager_id=admin_user.id,
        )
        db_session.add(other_job)
        await db_session.flush()
        await db_session.refresh(other_job)

        response = await hiring_manager_client.post(
            f"/dashboard/jobs/{other_job.id}/status",
            data={"status": "Published"},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_interviewer_cannot_change_job_status(
        self, interviewer_client: AsyncClient, sample_job: Job
    ):
        response = await interviewer_client.post(
            f"/dashboard/jobs/{sample_job.id}/status",
            data={"status": "Closed"},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_unauthenticated_cannot_change_status(
        self, async_client: AsyncClient, sample_job: Job
    ):
        response = await async_client.post(
            f"/dashboard/jobs/{sample_job.id}/status",
            data={"status": "Closed"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers["location"]

    async def test_status_change_nonexistent_job(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/dashboard/jobs/99999/status",
            data={"status": "Published"},
            follow_redirects=False,
        )
        assert response.status_code == 404

    async def test_same_status_no_change(
        self,
        admin_client: AsyncClient,
        sample_job: Job,
        db_session: AsyncSession,
    ):
        assert sample_job.status == "Published"

        response = await admin_client.post(
            f"/dashboard/jobs/{sample_job.id}/status",
            data={"status": "Published"},
            follow_redirects=False,
        )
        assert response.status_code == 302

        await db_session.refresh(sample_job)
        assert sample_job.status == "Published"


class TestPublicJobBoard:
    """Tests for GET / — landing page with published jobs."""

    async def test_landing_page_shows_published_jobs(
        self, async_client: AsyncClient, sample_job: Job
    ):
        response = await async_client.get("/", follow_redirects=False)
        assert response.status_code == 200
        assert b"Senior Backend Engineer" in response.content

    async def test_landing_page_does_not_show_draft_jobs(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
    ):
        draft_job = Job(
            title="Secret Draft Job",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="This should not appear on the public board.",
            status="Draft",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(draft_job)
        await db_session.flush()

        response = await async_client.get("/", follow_redirects=False)
        assert response.status_code == 200
        assert b"Secret Draft Job" not in response.content

    async def test_landing_page_does_not_show_closed_jobs(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
    ):
        closed_job = Job(
            title="Closed Position",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="This position is closed.",
            status="Closed",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(closed_job)
        await db_session.flush()

        response = await async_client.get("/", follow_redirects=False)
        assert response.status_code == 200
        assert b"Closed Position" not in response.content

    async def test_landing_page_accessible_without_auth(
        self, async_client: AsyncClient
    ):
        response = await async_client.get("/", follow_redirects=False)
        assert response.status_code == 200
        assert b"TalentFlow" in response.content

    async def test_landing_page_shows_no_openings_message_when_empty(
        self, async_client: AsyncClient
    ):
        response = await async_client.get("/", follow_redirects=False)
        assert response.status_code == 200
        assert b"No Open Positions" in response.content or b"Current Openings" in response.content


class TestJobPipeline:
    """Tests for GET /dashboard/jobs/{job_id}/pipeline — Kanban pipeline view."""

    async def test_admin_can_view_pipeline(
        self, admin_client: AsyncClient, sample_job: Job
    ):
        response = await admin_client.get(
            f"/dashboard/jobs/{sample_job.id}/pipeline", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Pipeline" in response.content

    async def test_recruiter_can_view_pipeline(
        self, recruiter_client: AsyncClient, sample_job: Job
    ):
        response = await recruiter_client.get(
            f"/dashboard/jobs/{sample_job.id}/pipeline", follow_redirects=False
        )
        assert response.status_code == 200
        assert b"Pipeline" in response.content

    async def test_interviewer_cannot_view_pipeline(
        self, interviewer_client: AsyncClient, sample_job: Job
    ):
        response = await interviewer_client.get(
            f"/dashboard/jobs/{sample_job.id}/pipeline", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_unauthenticated_redirects_to_login(
        self, async_client: AsyncClient, sample_job: Job
    ):
        response = await async_client.get(
            f"/dashboard/jobs/{sample_job.id}/pipeline", follow_redirects=False
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers["location"]

    async def test_pipeline_nonexistent_job_returns_404(
        self, admin_client: AsyncClient
    ):
        response = await admin_client.get(
            "/dashboard/jobs/99999/pipeline", follow_redirects=False
        )
        assert response.status_code == 404

    async def test_pipeline_shows_all_status_columns(
        self, admin_client: AsyncClient, sample_job: Job
    ):
        response = await admin_client.get(
            f"/dashboard/jobs/{sample_job.id}/pipeline", follow_redirects=False
        )
        assert response.status_code == 200
        content = response.content
        assert b"Applied" in content
        assert b"Screening" in content
        assert b"Interview" in content
        assert b"Offer" in content
        assert b"Hired" in content
        assert b"Rejected" in content


class TestJobServiceLogic:
    """Tests for job service business logic via the API."""

    async def test_full_lifecycle_draft_to_published_to_closed(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
    ):
        create_response = await admin_client.post(
            "/dashboard/jobs",
            data={
                "title": "Lifecycle Test Job",
                "department": "Engineering",
                "location": "Remote",
                "type": "Full-Time",
                "salary_min": "100000",
                "salary_max": "150000",
                "description": "Testing full lifecycle.",
                "hiring_manager_id": str(hiring_manager_user.id),
            },
            follow_redirects=False,
        )
        assert create_response.status_code == 302
        job_url = create_response.headers["location"]
        job_id = int(job_url.split("/")[-1])

        result = await db_session.execute(select(Job).where(Job.id == job_id))
        job = result.scalars().first()
        assert job is not None
        assert job.status == "Draft"

        publish_response = await admin_client.post(
            f"/dashboard/jobs/{job_id}/status",
            data={"status": "Published"},
            follow_redirects=False,
        )
        assert publish_response.status_code == 302

        await db_session.refresh(job)
        assert job.status == "Published"

        close_response = await admin_client.post(
            f"/dashboard/jobs/{job_id}/status",
            data={"status": "Closed"},
            follow_redirects=False,
        )
        assert close_response.status_code == 302

        await db_session.refresh(job)
        assert job.status == "Closed"

    async def test_published_job_appears_on_landing_then_disappears_when_closed(
        self,
        admin_client: AsyncClient,
        async_client: AsyncClient,
        db_session: AsyncSession,
        hiring_manager_user: User,
    ):
        job = Job(
            title="Visibility Test Job",
            department="Product",
            location="Remote",
            type="Full-Time",
            salary_min=90000,
            salary_max=130000,
            description="Testing visibility on landing page.",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(job)
        await db_session.flush()
        await db_session.refresh(job)

        landing_response = await async_client.get("/", follow_redirects=False)
        assert b"Visibility Test Job" in landing_response.content

        close_response = await admin_client.post(
            f"/dashboard/jobs/{job.id}/status",
            data={"status": "Closed"},
            follow_redirects=False,
        )
        assert close_response.status_code == 302

        landing_response_after = await async_client.get("/", follow_redirects=False)
        assert b"Visibility Test Job" not in landing_response_after.content