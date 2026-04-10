import logging
from datetime import datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ALLOWED_TRANSITIONS, ALLOWED_STATUSES
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.user import User
from app.services.application_service import (
    create_application,
    get_application,
    get_kanban,
    list_applications,
    update_status,
)

logger = logging.getLogger(__name__)


class TestApplicationCreation:
    """Tests for creating applications."""

    async def test_create_application_success(
        self,
        db_session: AsyncSession,
        sample_job: Job,
        sample_candidate: Candidate,
        admin_user: User,
    ):
        application = await create_application(
            db=db_session,
            job_id=sample_job.id,
            candidate_id=sample_candidate.id,
            user=admin_user,
        )

        assert application is not None
        assert application.id is not None
        assert application.job_id == sample_job.id
        assert application.candidate_id == sample_candidate.id
        assert application.status == "Applied"

    async def test_create_application_nonexistent_job(
        self,
        db_session: AsyncSession,
        sample_candidate: Candidate,
        admin_user: User,
    ):
        with pytest.raises(ValueError, match="Job with id 99999 not found"):
            await create_application(
                db=db_session,
                job_id=99999,
                candidate_id=sample_candidate.id,
                user=admin_user,
            )

    async def test_create_application_nonexistent_candidate(
        self,
        db_session: AsyncSession,
        sample_job: Job,
        admin_user: User,
    ):
        with pytest.raises(ValueError, match="Candidate with id 99999 not found"):
            await create_application(
                db=db_session,
                job_id=sample_job.id,
                candidate_id=99999,
                user=admin_user,
            )

    async def test_create_duplicate_application(
        self,
        db_session: AsyncSession,
        sample_job: Job,
        sample_candidate: Candidate,
        admin_user: User,
    ):
        await create_application(
            db=db_session,
            job_id=sample_job.id,
            candidate_id=sample_candidate.id,
            user=admin_user,
        )

        with pytest.raises(ValueError, match="already applied"):
            await create_application(
                db=db_session,
                job_id=sample_job.id,
                candidate_id=sample_candidate.id,
                user=admin_user,
            )

    async def test_create_application_via_form_admin(
        self,
        admin_client: AsyncClient,
        sample_job: Job,
        sample_candidate: Candidate,
    ):
        response = await admin_client.post(
            "/dashboard/applications",
            data={
                "job_id": str(sample_job.id),
                "candidate_id": str(sample_candidate.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard/applications/" in response.headers.get("location", "")

    async def test_create_application_via_form_recruiter(
        self,
        recruiter_client: AsyncClient,
        sample_job: Job,
        sample_candidate: Candidate,
    ):
        response = await recruiter_client.post(
            "/dashboard/applications",
            data={
                "job_id": str(sample_job.id),
                "candidate_id": str(sample_candidate.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard/applications/" in response.headers.get("location", "")


class TestApplicationStatusTransitions:
    """Tests for application status transitions and ALLOWED_TRANSITIONS enforcement."""

    async def test_valid_transition_applied_to_screening(
        self,
        db_session: AsyncSession,
        sample_application: Application,
        admin_user: User,
    ):
        updated = await update_status(
            db=db_session,
            application_id=sample_application.id,
            new_status="Screening",
            user=admin_user,
        )
        assert updated.status == "Screening"

    async def test_valid_transition_applied_to_rejected(
        self,
        db_session: AsyncSession,
        sample_application: Application,
        admin_user: User,
    ):
        updated = await update_status(
            db=db_session,
            application_id=sample_application.id,
            new_status="Rejected",
            user=admin_user,
        )
        assert updated.status == "Rejected"

    async def test_valid_transition_screening_to_interview(
        self,
        db_session: AsyncSession,
        sample_application: Application,
        admin_user: User,
    ):
        await update_status(
            db=db_session,
            application_id=sample_application.id,
            new_status="Screening",
            user=admin_user,
        )
        updated = await update_status(
            db=db_session,
            application_id=sample_application.id,
            new_status="Interview",
            user=admin_user,
        )
        assert updated.status == "Interview"

    async def test_valid_transition_interview_to_offer(
        self,
        db_session: AsyncSession,
        sample_application: Application,
        admin_user: User,
    ):
        await update_status(db=db_session, application_id=sample_application.id, new_status="Screening", user=admin_user)
        await update_status(db=db_session, application_id=sample_application.id, new_status="Interview", user=admin_user)
        updated = await update_status(
            db=db_session,
            application_id=sample_application.id,
            new_status="Offer",
            user=admin_user,
        )
        assert updated.status == "Offer"

    async def test_valid_transition_offer_to_hired(
        self,
        db_session: AsyncSession,
        sample_application: Application,
        admin_user: User,
    ):
        await update_status(db=db_session, application_id=sample_application.id, new_status="Screening", user=admin_user)
        await update_status(db=db_session, application_id=sample_application.id, new_status="Interview", user=admin_user)
        await update_status(db=db_session, application_id=sample_application.id, new_status="Offer", user=admin_user)
        updated = await update_status(
            db=db_session,
            application_id=sample_application.id,
            new_status="Hired",
            user=admin_user,
        )
        assert updated.status == "Hired"

    async def test_invalid_transition_applied_to_interview(
        self,
        db_session: AsyncSession,
        sample_application: Application,
        admin_user: User,
    ):
        with pytest.raises(ValueError, match="Invalid status transition"):
            await update_status(
                db=db_session,
                application_id=sample_application.id,
                new_status="Interview",
                user=admin_user,
            )

    async def test_invalid_transition_applied_to_offer(
        self,
        db_session: AsyncSession,
        sample_application: Application,
        admin_user: User,
    ):
        with pytest.raises(ValueError, match="Invalid status transition"):
            await update_status(
                db=db_session,
                application_id=sample_application.id,
                new_status="Offer",
                user=admin_user,
            )

    async def test_invalid_transition_applied_to_hired(
        self,
        db_session: AsyncSession,
        sample_application: Application,
        admin_user: User,
    ):
        with pytest.raises(ValueError, match="Invalid status transition"):
            await update_status(
                db=db_session,
                application_id=sample_application.id,
                new_status="Hired",
                user=admin_user,
            )

    async def test_invalid_transition_hired_to_any(
        self,
        db_session: AsyncSession,
        sample_application: Application,
        admin_user: User,
    ):
        await update_status(db=db_session, application_id=sample_application.id, new_status="Screening", user=admin_user)
        await update_status(db=db_session, application_id=sample_application.id, new_status="Interview", user=admin_user)
        await update_status(db=db_session, application_id=sample_application.id, new_status="Offer", user=admin_user)
        await update_status(db=db_session, application_id=sample_application.id, new_status="Hired", user=admin_user)

        for status in ALLOWED_STATUSES:
            if status == "Hired":
                continue
            with pytest.raises(ValueError, match="Invalid status transition"):
                await update_status(
                    db=db_session,
                    application_id=sample_application.id,
                    new_status=status,
                    user=admin_user,
                )

    async def test_invalid_transition_rejected_to_any(
        self,
        db_session: AsyncSession,
        sample_application: Application,
        admin_user: User,
    ):
        await update_status(
            db=db_session,
            application_id=sample_application.id,
            new_status="Rejected",
            user=admin_user,
        )

        for status in ALLOWED_STATUSES:
            if status == "Rejected":
                continue
            with pytest.raises(ValueError, match="Invalid status transition"):
                await update_status(
                    db=db_session,
                    application_id=sample_application.id,
                    new_status=status,
                    user=admin_user,
                )

    async def test_invalid_status_value(
        self,
        db_session: AsyncSession,
        sample_application: Application,
        admin_user: User,
    ):
        with pytest.raises(ValueError, match="Invalid status"):
            await update_status(
                db=db_session,
                application_id=sample_application.id,
                new_status="InvalidStatus",
                user=admin_user,
            )

    async def test_update_status_nonexistent_application(
        self,
        db_session: AsyncSession,
        admin_user: User,
    ):
        with pytest.raises(ValueError, match="Application with id 99999 not found"):
            await update_status(
                db=db_session,
                application_id=99999,
                new_status="Screening",
                user=admin_user,
            )

    async def test_status_update_via_form(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
    ):
        response = await admin_client.post(
            f"/dashboard/applications/{sample_application.id}/status",
            data={"status": "Screening"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert f"/dashboard/applications/{sample_application.id}" in response.headers.get("location", "")

    async def test_status_update_invalid_transition_via_form(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
    ):
        response = await admin_client.post(
            f"/dashboard/applications/{sample_application.id}/status",
            data={"status": "Hired"},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_all_allowed_transitions_are_valid(self):
        """Verify that ALLOWED_TRANSITIONS only contains valid statuses."""
        for source_status, targets in ALLOWED_TRANSITIONS.items():
            assert source_status in ALLOWED_STATUSES, f"Source status '{source_status}' not in ALLOWED_STATUSES"
            for target in targets:
                assert target in ALLOWED_STATUSES, f"Target status '{target}' not in ALLOWED_STATUSES"


class TestApplicationListing:
    """Tests for listing and filtering applications."""

    async def test_list_applications_empty(
        self,
        db_session: AsyncSession,
    ):
        applications = await list_applications(db=db_session)
        assert applications == []

    async def test_list_applications_with_data(
        self,
        db_session: AsyncSession,
        sample_application: Application,
    ):
        applications = await list_applications(db=db_session)
        assert len(applications) == 1
        assert applications[0].id == sample_application.id

    async def test_list_applications_filter_by_status(
        self,
        db_session: AsyncSession,
        sample_application: Application,
    ):
        applications = await list_applications(db=db_session, status_filter="Applied")
        assert len(applications) == 1

        applications = await list_applications(db=db_session, status_filter="Screening")
        assert len(applications) == 0

    async def test_list_applications_filter_by_job_id(
        self,
        db_session: AsyncSession,
        sample_application: Application,
        sample_job: Job,
    ):
        applications = await list_applications(db=db_session, job_id=sample_job.id)
        assert len(applications) == 1

        applications = await list_applications(db=db_session, job_id=99999)
        assert len(applications) == 0

    async def test_list_applications_filter_by_candidate_id(
        self,
        db_session: AsyncSession,
        sample_application: Application,
        sample_candidate: Candidate,
    ):
        applications = await list_applications(db=db_session, candidate_id=sample_candidate.id)
        assert len(applications) == 1

        applications = await list_applications(db=db_session, candidate_id=99999)
        assert len(applications) == 0

    async def test_get_application_detail(
        self,
        db_session: AsyncSession,
        sample_application: Application,
    ):
        application = await get_application(db=db_session, application_id=sample_application.id)
        assert application is not None
        assert application.id == sample_application.id
        assert application.job is not None
        assert application.candidate is not None

    async def test_get_application_not_found(
        self,
        db_session: AsyncSession,
    ):
        application = await get_application(db=db_session, application_id=99999)
        assert application is None


class TestKanbanPipeline:
    """Tests for Kanban pipeline data grouping."""

    async def test_kanban_empty_pipeline(
        self,
        db_session: AsyncSession,
        sample_job: Job,
    ):
        pipeline = await get_kanban(db=db_session, job_id=sample_job.id)
        assert isinstance(pipeline, dict)
        for status in ALLOWED_STATUSES:
            assert status in pipeline
            assert pipeline[status] == []

    async def test_kanban_with_applications(
        self,
        db_session: AsyncSession,
        sample_job: Job,
        sample_application: Application,
    ):
        pipeline = await get_kanban(db=db_session, job_id=sample_job.id)
        assert len(pipeline["Applied"]) == 1
        assert pipeline["Applied"][0].id == sample_application.id
        assert len(pipeline["Screening"]) == 0
        assert len(pipeline["Interview"]) == 0
        assert len(pipeline["Offer"]) == 0
        assert len(pipeline["Hired"]) == 0
        assert len(pipeline["Rejected"]) == 0

    async def test_kanban_applications_in_multiple_stages(
        self,
        db_session: AsyncSession,
        sample_job: Job,
        sample_candidate: Candidate,
        admin_user: User,
    ):
        app1 = await create_application(
            db=db_session,
            job_id=sample_job.id,
            candidate_id=sample_candidate.id,
            user=admin_user,
        )

        candidate2 = Candidate(
            first_name="John",
            last_name="Smith",
            email="john.smith@example.com",
            phone="+1-555-0200",
        )
        db_session.add(candidate2)
        await db_session.flush()
        await db_session.refresh(candidate2)

        app2 = await create_application(
            db=db_session,
            job_id=sample_job.id,
            candidate_id=candidate2.id,
            user=admin_user,
        )

        await update_status(
            db=db_session,
            application_id=app2.id,
            new_status="Screening",
            user=admin_user,
        )

        pipeline = await get_kanban(db=db_session, job_id=sample_job.id)
        assert len(pipeline["Applied"]) == 1
        assert len(pipeline["Screening"]) == 1
        assert pipeline["Applied"][0].id == app1.id
        assert pipeline["Screening"][0].id == app2.id

    async def test_kanban_nonexistent_job(
        self,
        db_session: AsyncSession,
    ):
        with pytest.raises(ValueError, match="Job with id 99999 not found"):
            await get_kanban(db=db_session, job_id=99999)

    async def test_kanban_all_statuses_present(
        self,
        db_session: AsyncSession,
        sample_job: Job,
    ):
        pipeline = await get_kanban(db=db_session, job_id=sample_job.id)
        for status in ALLOWED_STATUSES:
            assert status in pipeline, f"Status '{status}' missing from Kanban pipeline"


class TestApplicationRBAC:
    """Tests for role-based access control on application endpoints."""

    async def test_applications_list_page_admin(
        self,
        admin_client: AsyncClient,
    ):
        response = await admin_client.get("/dashboard/applications", follow_redirects=False)
        assert response.status_code == 200

    async def test_applications_list_page_recruiter(
        self,
        recruiter_client: AsyncClient,
    ):
        response = await recruiter_client.get("/dashboard/applications", follow_redirects=False)
        assert response.status_code == 200

    async def test_applications_list_page_hiring_manager(
        self,
        hiring_manager_client: AsyncClient,
    ):
        response = await hiring_manager_client.get("/dashboard/applications", follow_redirects=False)
        assert response.status_code == 200

    async def test_applications_list_page_interviewer_forbidden(
        self,
        interviewer_client: AsyncClient,
    ):
        response = await interviewer_client.get("/dashboard/applications", follow_redirects=False)
        assert response.status_code == 403

    async def test_applications_list_page_unauthenticated_redirects(
        self,
        async_client: AsyncClient,
    ):
        response = await async_client.get("/dashboard/applications", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    async def test_create_application_page_admin(
        self,
        admin_client: AsyncClient,
    ):
        response = await admin_client.get("/dashboard/applications/create", follow_redirects=False)
        assert response.status_code == 200

    async def test_create_application_page_recruiter(
        self,
        recruiter_client: AsyncClient,
    ):
        response = await recruiter_client.get("/dashboard/applications/create", follow_redirects=False)
        assert response.status_code == 200

    async def test_create_application_page_hiring_manager_forbidden(
        self,
        hiring_manager_client: AsyncClient,
    ):
        response = await hiring_manager_client.get("/dashboard/applications/create", follow_redirects=False)
        assert response.status_code == 403

    async def test_create_application_page_interviewer_forbidden(
        self,
        interviewer_client: AsyncClient,
    ):
        response = await interviewer_client.get("/dashboard/applications/create", follow_redirects=False)
        assert response.status_code == 403

    async def test_create_application_post_interviewer_forbidden(
        self,
        interviewer_client: AsyncClient,
        sample_job: Job,
        sample_candidate: Candidate,
    ):
        response = await interviewer_client.post(
            "/dashboard/applications",
            data={
                "job_id": str(sample_job.id),
                "candidate_id": str(sample_candidate.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_application_detail_page_admin(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
    ):
        response = await admin_client.get(
            f"/dashboard/applications/{sample_application.id}",
            follow_redirects=False,
        )
        assert response.status_code == 200

    async def test_application_detail_page_interviewer(
        self,
        interviewer_client: AsyncClient,
        sample_application: Application,
    ):
        response = await interviewer_client.get(
            f"/dashboard/applications/{sample_application.id}",
            follow_redirects=False,
        )
        assert response.status_code == 200

    async def test_application_detail_not_found(
        self,
        admin_client: AsyncClient,
    ):
        response = await admin_client.get(
            "/dashboard/applications/99999",
            follow_redirects=False,
        )
        assert response.status_code == 404

    async def test_status_update_admin_allowed(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
    ):
        response = await admin_client.post(
            f"/dashboard/applications/{sample_application.id}/status",
            data={"status": "Screening"},
            follow_redirects=False,
        )
        assert response.status_code == 302

    async def test_status_update_recruiter_allowed(
        self,
        recruiter_client: AsyncClient,
        sample_application: Application,
    ):
        response = await recruiter_client.post(
            f"/dashboard/applications/{sample_application.id}/status",
            data={"status": "Screening"},
            follow_redirects=False,
        )
        assert response.status_code == 302

    async def test_status_update_hiring_manager_allowed(
        self,
        hiring_manager_client: AsyncClient,
        sample_application: Application,
    ):
        response = await hiring_manager_client.post(
            f"/dashboard/applications/{sample_application.id}/status",
            data={"status": "Screening"},
            follow_redirects=False,
        )
        assert response.status_code == 302

    async def test_status_update_interviewer_forbidden(
        self,
        interviewer_client: AsyncClient,
        sample_application: Application,
    ):
        response = await interviewer_client.post(
            f"/dashboard/applications/{sample_application.id}/status",
            data={"status": "Screening"},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_status_update_unauthenticated_redirects(
        self,
        async_client: AsyncClient,
        sample_application: Application,
    ):
        response = await async_client.post(
            f"/dashboard/applications/{sample_application.id}/status",
            data={"status": "Screening"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")


class TestPipelinePage:
    """Tests for the pipeline/Kanban page."""

    async def test_pipeline_page_admin(
        self,
        admin_client: AsyncClient,
        sample_job: Job,
    ):
        response = await admin_client.get(
            f"/dashboard/jobs/{sample_job.id}/pipeline",
            follow_redirects=False,
        )
        assert response.status_code == 200

    async def test_pipeline_page_recruiter(
        self,
        recruiter_client: AsyncClient,
        sample_job: Job,
    ):
        response = await recruiter_client.get(
            f"/dashboard/jobs/{sample_job.id}/pipeline",
            follow_redirects=False,
        )
        assert response.status_code == 200

    async def test_pipeline_page_hiring_manager(
        self,
        hiring_manager_client: AsyncClient,
        sample_job: Job,
    ):
        response = await hiring_manager_client.get(
            f"/dashboard/jobs/{sample_job.id}/pipeline",
            follow_redirects=False,
        )
        assert response.status_code == 200

    async def test_pipeline_page_interviewer_forbidden(
        self,
        interviewer_client: AsyncClient,
        sample_job: Job,
    ):
        response = await interviewer_client.get(
            f"/dashboard/jobs/{sample_job.id}/pipeline",
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_pipeline_page_unauthenticated_redirects(
        self,
        async_client: AsyncClient,
        sample_job: Job,
    ):
        response = await async_client.get(
            f"/dashboard/jobs/{sample_job.id}/pipeline",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    async def test_pipeline_page_nonexistent_job(
        self,
        admin_client: AsyncClient,
    ):
        response = await admin_client.get(
            "/dashboard/jobs/99999/pipeline",
            follow_redirects=False,
        )
        assert response.status_code == 404

    async def test_pipeline_page_contains_all_statuses(
        self,
        admin_client: AsyncClient,
        sample_job: Job,
    ):
        response = await admin_client.get(
            f"/dashboard/jobs/{sample_job.id}/pipeline",
            follow_redirects=False,
        )
        assert response.status_code == 200
        content = response.text
        for status in ALLOWED_STATUSES:
            assert status in content, f"Status '{status}' not found in pipeline page"


class TestApplicationCreateFormValidation:
    """Tests for application creation form validation."""

    async def test_create_application_duplicate_via_form(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
        sample_job: Job,
        sample_candidate: Candidate,
    ):
        response = await admin_client.post(
            "/dashboard/applications",
            data={
                "job_id": str(sample_job.id),
                "candidate_id": str(sample_candidate.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert "already applied" in response.text

    async def test_create_application_nonexistent_job_via_form(
        self,
        admin_client: AsyncClient,
        sample_candidate: Candidate,
    ):
        response = await admin_client.post(
            "/dashboard/applications",
            data={
                "job_id": "99999",
                "candidate_id": str(sample_candidate.id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert "not found" in response.text

    async def test_create_application_nonexistent_candidate_via_form(
        self,
        admin_client: AsyncClient,
        sample_job: Job,
    ):
        response = await admin_client.post(
            "/dashboard/applications",
            data={
                "job_id": str(sample_job.id),
                "candidate_id": "99999",
            },
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert "not found" in response.text


class TestApplicationStatusUpdateFromPipeline:
    """Tests for status updates originating from the pipeline page."""

    async def test_status_update_with_pipeline_referer_redirects_to_pipeline(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
        sample_job: Job,
    ):
        response = await admin_client.post(
            f"/dashboard/applications/{sample_application.id}/status",
            data={"status": "Screening"},
            headers={"referer": f"http://testserver/dashboard/jobs/{sample_job.id}/pipeline"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert f"/dashboard/jobs/{sample_job.id}/pipeline" in location

    async def test_status_update_without_pipeline_referer_redirects_to_detail(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
    ):
        response = await admin_client.post(
            f"/dashboard/applications/{sample_application.id}/status",
            data={"status": "Screening"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert f"/dashboard/applications/{sample_application.id}" in location


class TestApplicationDetailContent:
    """Tests for application detail page content."""

    async def test_detail_page_shows_candidate_info(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
        sample_candidate: Candidate,
    ):
        response = await admin_client.get(
            f"/dashboard/applications/{sample_application.id}",
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert sample_candidate.first_name in response.text
        assert sample_candidate.last_name in response.text
        assert sample_candidate.email in response.text

    async def test_detail_page_shows_job_info(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
        sample_job: Job,
    ):
        response = await admin_client.get(
            f"/dashboard/applications/{sample_application.id}",
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert sample_job.title in response.text
        assert sample_job.department in response.text

    async def test_detail_page_shows_status_transition_options_for_admin(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
    ):
        response = await admin_client.get(
            f"/dashboard/applications/{sample_application.id}",
            follow_redirects=False,
        )
        assert response.status_code == 200
        content = response.text
        allowed = ALLOWED_TRANSITIONS.get("Applied", [])
        for transition in allowed:
            assert transition in content

    async def test_detail_page_hides_status_transition_for_interviewer(
        self,
        interviewer_client: AsyncClient,
        sample_application: Application,
    ):
        response = await interviewer_client.get(
            f"/dashboard/applications/{sample_application.id}",
            follow_redirects=False,
        )
        assert response.status_code == 200
        content = response.text
        assert "Update Status" not in content