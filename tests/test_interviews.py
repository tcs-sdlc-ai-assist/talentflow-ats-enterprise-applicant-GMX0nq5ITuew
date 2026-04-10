import logging
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.job import Job
from app.models.user import User

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestInterviewListPage:
    """Tests for GET /dashboard/interviews — list all interviews."""

    async def test_interviews_list_page_as_admin(
        self,
        admin_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await admin_client.get("/dashboard/interviews", follow_redirects=True)
        assert response.status_code == 200
        assert "Interviews" in response.text

    async def test_interviews_list_page_as_recruiter(
        self,
        recruiter_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await recruiter_client.get("/dashboard/interviews", follow_redirects=True)
        assert response.status_code == 200
        assert "Interviews" in response.text

    async def test_interviews_list_page_as_hiring_manager(
        self,
        hiring_manager_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await hiring_manager_client.get("/dashboard/interviews", follow_redirects=True)
        assert response.status_code == 200
        assert "Interviews" in response.text

    async def test_interviews_list_page_as_interviewer(
        self,
        interviewer_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await interviewer_client.get("/dashboard/interviews", follow_redirects=True)
        assert response.status_code == 200
        assert "Interviews" in response.text

    async def test_interviews_list_page_unauthenticated_redirects_to_login(
        self,
        async_client: AsyncClient,
    ):
        response = await async_client.get("/dashboard/interviews", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    async def test_interviews_list_page_filter_by_application_id(
        self,
        admin_client: AsyncClient,
        sample_interview: Interview,
        sample_application: Application,
    ):
        response = await admin_client.get(
            f"/dashboard/interviews?application_id={sample_application.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200

    async def test_interviews_list_page_empty(
        self,
        admin_client: AsyncClient,
    ):
        response = await admin_client.get("/dashboard/interviews", follow_redirects=True)
        assert response.status_code == 200
        assert "No interviews scheduled" in response.text


@pytest.mark.asyncio
class TestInterviewScheduleForm:
    """Tests for GET /dashboard/interviews/schedule — schedule form page."""

    async def test_schedule_form_as_admin(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
    ):
        response = await admin_client.get("/dashboard/interviews/schedule", follow_redirects=True)
        assert response.status_code == 200
        assert "Schedule" in response.text or "schedule" in response.text.lower()

    async def test_schedule_form_as_recruiter(
        self,
        recruiter_client: AsyncClient,
        sample_application: Application,
    ):
        response = await recruiter_client.get("/dashboard/interviews/schedule", follow_redirects=True)
        assert response.status_code == 200

    async def test_schedule_form_forbidden_for_hiring_manager(
        self,
        hiring_manager_client: AsyncClient,
    ):
        response = await hiring_manager_client.get(
            "/dashboard/interviews/schedule", follow_redirects=True
        )
        assert response.status_code == 403

    async def test_schedule_form_forbidden_for_interviewer(
        self,
        interviewer_client: AsyncClient,
    ):
        response = await interviewer_client.get(
            "/dashboard/interviews/schedule", follow_redirects=True
        )
        assert response.status_code == 403

    async def test_schedule_form_unauthenticated_redirects(
        self,
        async_client: AsyncClient,
    ):
        response = await async_client.get("/dashboard/interviews/schedule", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    async def test_schedule_form_with_preselected_application(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
    ):
        response = await admin_client.get(
            f"/dashboard/interviews/schedule?application_id={sample_application.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200


@pytest.mark.asyncio
class TestInterviewScheduleSubmit:
    """Tests for POST /dashboard/interviews — schedule a new interview."""

    async def test_schedule_interview_as_admin(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
        interviewer_user: User,
    ):
        scheduled_at = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M")
        response = await admin_client.post(
            "/dashboard/interviews",
            data={
                "application_id": str(sample_application.id),
                "interviewer_id": str(interviewer_user.id),
                "scheduled_at": scheduled_at,
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard/interviews" in response.headers.get("location", "")

    async def test_schedule_interview_as_recruiter(
        self,
        recruiter_client: AsyncClient,
        sample_application: Application,
        interviewer_user: User,
    ):
        scheduled_at = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M")
        response = await recruiter_client.post(
            "/dashboard/interviews",
            data={
                "application_id": str(sample_application.id),
                "interviewer_id": str(interviewer_user.id),
                "scheduled_at": scheduled_at,
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard/interviews" in response.headers.get("location", "")

    async def test_schedule_interview_forbidden_for_hiring_manager(
        self,
        hiring_manager_client: AsyncClient,
        sample_application: Application,
        interviewer_user: User,
    ):
        scheduled_at = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M")
        response = await hiring_manager_client.post(
            "/dashboard/interviews",
            data={
                "application_id": str(sample_application.id),
                "interviewer_id": str(interviewer_user.id),
                "scheduled_at": scheduled_at,
            },
            follow_redirects=True,
        )
        assert response.status_code == 403

    async def test_schedule_interview_forbidden_for_interviewer(
        self,
        interviewer_client: AsyncClient,
        sample_application: Application,
        interviewer_user: User,
    ):
        scheduled_at = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M")
        response = await interviewer_client.post(
            "/dashboard/interviews",
            data={
                "application_id": str(sample_application.id),
                "interviewer_id": str(interviewer_user.id),
                "scheduled_at": scheduled_at,
            },
            follow_redirects=True,
        )
        assert response.status_code == 403

    async def test_schedule_interview_unauthenticated_redirects(
        self,
        async_client: AsyncClient,
        sample_application: Application,
        interviewer_user: User,
    ):
        scheduled_at = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M")
        response = await async_client.post(
            "/dashboard/interviews",
            data={
                "application_id": str(sample_application.id),
                "interviewer_id": str(interviewer_user.id),
                "scheduled_at": scheduled_at,
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    async def test_schedule_interview_invalid_datetime_format(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
        interviewer_user: User,
    ):
        response = await admin_client.post(
            "/dashboard/interviews",
            data={
                "application_id": str(sample_application.id),
                "interviewer_id": str(interviewer_user.id),
                "scheduled_at": "not-a-date",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert "Invalid" in response.text or "invalid" in response.text.lower()

    async def test_schedule_interview_nonexistent_application(
        self,
        admin_client: AsyncClient,
        interviewer_user: User,
    ):
        scheduled_at = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M")
        response = await admin_client.post(
            "/dashboard/interviews",
            data={
                "application_id": "99999",
                "interviewer_id": str(interviewer_user.id),
                "scheduled_at": scheduled_at,
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert "not found" in response.text.lower() or "error" in response.text.lower()

    async def test_schedule_interview_nonexistent_interviewer(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
    ):
        scheduled_at = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M")
        response = await admin_client.post(
            "/dashboard/interviews",
            data={
                "application_id": str(sample_application.id),
                "interviewer_id": "99999",
                "scheduled_at": scheduled_at,
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert "not found" in response.text.lower() or "error" in response.text.lower()


@pytest.mark.asyncio
class TestMyInterviewsPage:
    """Tests for GET /dashboard/interviews/my — interviewer's own interviews."""

    async def test_my_interviews_as_interviewer(
        self,
        interviewer_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await interviewer_client.get("/dashboard/interviews/my", follow_redirects=True)
        assert response.status_code == 200
        assert "My Interviews" in response.text

    async def test_my_interviews_as_admin(
        self,
        admin_client: AsyncClient,
    ):
        response = await admin_client.get("/dashboard/interviews/my", follow_redirects=True)
        assert response.status_code == 200
        assert "My Interviews" in response.text

    async def test_my_interviews_as_recruiter(
        self,
        recruiter_client: AsyncClient,
    ):
        response = await recruiter_client.get("/dashboard/interviews/my", follow_redirects=True)
        assert response.status_code == 200

    async def test_my_interviews_as_hiring_manager(
        self,
        hiring_manager_client: AsyncClient,
    ):
        response = await hiring_manager_client.get("/dashboard/interviews/my", follow_redirects=True)
        assert response.status_code == 200

    async def test_my_interviews_unauthenticated_redirects(
        self,
        async_client: AsyncClient,
    ):
        response = await async_client.get("/dashboard/interviews/my", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    async def test_my_interviews_shows_assigned_interview(
        self,
        interviewer_client: AsyncClient,
        sample_interview: Interview,
        sample_candidate: Candidate,
    ):
        response = await interviewer_client.get("/dashboard/interviews/my", follow_redirects=True)
        assert response.status_code == 200
        assert sample_candidate.first_name in response.text

    async def test_my_interviews_empty_when_no_assignments(
        self,
        interviewer_client: AsyncClient,
    ):
        response = await interviewer_client.get("/dashboard/interviews/my", follow_redirects=True)
        assert response.status_code == 200
        assert "No interviews assigned" in response.text


@pytest.mark.asyncio
class TestInterviewDetailPage:
    """Tests for GET /dashboard/interviews/{interview_id} — interview detail."""

    async def test_interview_detail_as_admin(
        self,
        admin_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await admin_client.get(
            f"/dashboard/interviews/{sample_interview.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Feedback" in response.text or "feedback" in response.text.lower()

    async def test_interview_detail_as_interviewer(
        self,
        interviewer_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await interviewer_client.get(
            f"/dashboard/interviews/{sample_interview.id}", follow_redirects=True
        )
        assert response.status_code == 200

    async def test_interview_detail_not_found(
        self,
        admin_client: AsyncClient,
    ):
        response = await admin_client.get(
            "/dashboard/interviews/99999", follow_redirects=True
        )
        assert response.status_code == 404

    async def test_interview_detail_unauthenticated_redirects(
        self,
        async_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await async_client.get(
            f"/dashboard/interviews/{sample_interview.id}", follow_redirects=False
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")


@pytest.mark.asyncio
class TestInterviewFeedbackFormPage:
    """Tests for GET /dashboard/interviews/{interview_id}/feedback — feedback form."""

    async def test_feedback_form_as_assigned_interviewer(
        self,
        interviewer_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await interviewer_client.get(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert "Feedback" in response.text or "feedback" in response.text.lower()

    async def test_feedback_form_as_admin(
        self,
        admin_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await admin_client.get(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            follow_redirects=True,
        )
        assert response.status_code == 200

    async def test_feedback_form_as_recruiter(
        self,
        recruiter_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await recruiter_client.get(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            follow_redirects=True,
        )
        assert response.status_code == 200

    async def test_feedback_form_forbidden_for_unassigned_interviewer(
        self,
        db_session: AsyncSession,
        async_client: AsyncClient,
        sample_interview: Interview,
    ):
        from app.core.security import hash_password

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
        await db_session.refresh(other_interviewer)

        login_response = await async_client.post(
            "/auth/login",
            data={"username": "otherinterviewer", "password": "otherpass123"},
            follow_redirects=False,
        )
        for key, value in login_response.cookies.items():
            async_client.cookies.set(key, value)

        response = await async_client.get(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            follow_redirects=True,
        )
        assert response.status_code == 403

    async def test_feedback_form_not_found(
        self,
        admin_client: AsyncClient,
    ):
        response = await admin_client.get(
            "/dashboard/interviews/99999/feedback",
            follow_redirects=True,
        )
        assert response.status_code == 404

    async def test_feedback_form_unauthenticated_redirects(
        self,
        async_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await async_client.get(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")


@pytest.mark.asyncio
class TestInterviewFeedbackSubmit:
    """Tests for POST /dashboard/interviews/{interview_id}/feedback — submit feedback."""

    async def test_submit_feedback_rating_1(
        self,
        interviewer_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await interviewer_client.post(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            data={
                "feedback_rating": "1",
                "feedback_notes": "Poor performance in technical questions.",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert "success" in response.text.lower() or "submitted" in response.text.lower()

    async def test_submit_feedback_rating_3(
        self,
        interviewer_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await interviewer_client.post(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            data={
                "feedback_rating": "3",
                "feedback_notes": "Average performance. Needs improvement in system design.",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert "success" in response.text.lower() or "submitted" in response.text.lower()

    async def test_submit_feedback_rating_5(
        self,
        interviewer_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await interviewer_client.post(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            data={
                "feedback_rating": "5",
                "feedback_notes": "Excellent candidate. Strong technical skills and great communication.",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert "success" in response.text.lower() or "submitted" in response.text.lower()

    async def test_submit_feedback_as_admin(
        self,
        admin_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await admin_client.post(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            data={
                "feedback_rating": "4",
                "feedback_notes": "Good candidate overall.",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert "success" in response.text.lower() or "submitted" in response.text.lower()

    async def test_submit_feedback_as_recruiter(
        self,
        recruiter_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await recruiter_client.post(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            data={
                "feedback_rating": "4",
                "feedback_notes": "Solid candidate.",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert "success" in response.text.lower() or "submitted" in response.text.lower()

    async def test_submit_feedback_empty_notes(
        self,
        interviewer_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await interviewer_client.post(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            data={
                "feedback_rating": "3",
                "feedback_notes": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

    async def test_submit_feedback_updates_existing(
        self,
        interviewer_client: AsyncClient,
        sample_interview: Interview,
    ):
        await interviewer_client.post(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            data={
                "feedback_rating": "3",
                "feedback_notes": "Initial feedback.",
            },
            follow_redirects=True,
        )

        response = await interviewer_client.post(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            data={
                "feedback_rating": "5",
                "feedback_notes": "Updated feedback after reconsideration.",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

    async def test_submit_feedback_forbidden_for_unassigned_interviewer(
        self,
        db_session: AsyncSession,
        async_client: AsyncClient,
        sample_interview: Interview,
    ):
        from app.core.security import hash_password

        other_interviewer = User(
            username="otherint2",
            email="other_int2@talentflow.local",
            password_hash=hash_password("otherpass123"),
            full_name="Other Interviewer 2",
            role="Interviewer",
            is_active=True,
        )
        db_session.add(other_interviewer)
        await db_session.flush()
        await db_session.refresh(other_interviewer)

        login_response = await async_client.post(
            "/auth/login",
            data={"username": "otherint2", "password": "otherpass123"},
            follow_redirects=False,
        )
        for key, value in login_response.cookies.items():
            async_client.cookies.set(key, value)

        response = await async_client.post(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            data={
                "feedback_rating": "4",
                "feedback_notes": "Should not be allowed.",
            },
            follow_redirects=True,
        )
        assert response.status_code == 403

    async def test_submit_feedback_not_found(
        self,
        admin_client: AsyncClient,
    ):
        response = await admin_client.post(
            "/dashboard/interviews/99999/feedback",
            data={
                "feedback_rating": "4",
                "feedback_notes": "Test feedback.",
            },
            follow_redirects=True,
        )
        assert response.status_code == 404

    async def test_submit_feedback_unauthenticated_redirects(
        self,
        async_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await async_client.post(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            data={
                "feedback_rating": "4",
                "feedback_notes": "Test feedback.",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    async def test_submit_feedback_invalid_rating_too_low(
        self,
        interviewer_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await interviewer_client.post(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            data={
                "feedback_rating": "0",
                "feedback_notes": "Invalid rating.",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        content_lower = response.text.lower()
        assert "error" in content_lower or "between" in content_lower or "invalid" in content_lower

    async def test_submit_feedback_invalid_rating_too_high(
        self,
        interviewer_client: AsyncClient,
        sample_interview: Interview,
    ):
        response = await interviewer_client.post(
            f"/dashboard/interviews/{sample_interview.id}/feedback",
            data={
                "feedback_rating": "6",
                "feedback_notes": "Invalid rating.",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        content_lower = response.text.lower()
        assert "error" in content_lower or "between" in content_lower or "invalid" in content_lower


@pytest.mark.asyncio
class TestInterviewScheduleIntegration:
    """Integration tests for the full interview scheduling and feedback workflow."""

    async def test_full_interview_workflow(
        self,
        admin_client: AsyncClient,
        sample_application: Application,
        interviewer_user: User,
        interviewer_client: AsyncClient,
    ):
        scheduled_at = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
        schedule_response = await admin_client.post(
            "/dashboard/interviews",
            data={
                "application_id": str(sample_application.id),
                "interviewer_id": str(interviewer_user.id),
                "scheduled_at": scheduled_at,
            },
            follow_redirects=False,
        )
        assert schedule_response.status_code == 302

        list_response = await admin_client.get("/dashboard/interviews", follow_redirects=True)
        assert list_response.status_code == 200

        my_response = await interviewer_client.get("/dashboard/interviews/my", follow_redirects=True)
        assert my_response.status_code == 200

    async def test_multiple_interviews_for_same_application(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        sample_application: Application,
        interviewer_user: User,
    ):
        from app.core.security import hash_password

        second_interviewer = User(
            username="secondinterviewer",
            email="second_interviewer@talentflow.local",
            password_hash=hash_password("secondpass123"),
            full_name="Second Interviewer",
            role="Interviewer",
            is_active=True,
        )
        db_session.add(second_interviewer)
        await db_session.flush()
        await db_session.refresh(second_interviewer)

        scheduled_at_1 = (datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
        response_1 = await admin_client.post(
            "/dashboard/interviews",
            data={
                "application_id": str(sample_application.id),
                "interviewer_id": str(interviewer_user.id),
                "scheduled_at": scheduled_at_1,
            },
            follow_redirects=False,
        )
        assert response_1.status_code == 302

        scheduled_at_2 = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M")
        response_2 = await admin_client.post(
            "/dashboard/interviews",
            data={
                "application_id": str(sample_application.id),
                "interviewer_id": str(second_interviewer.id),
                "scheduled_at": scheduled_at_2,
            },
            follow_redirects=False,
        )
        assert response_2.status_code == 302

        list_response = await admin_client.get(
            f"/dashboard/interviews?application_id={sample_application.id}",
            follow_redirects=True,
        )
        assert list_response.status_code == 200