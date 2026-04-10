import logging
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate, Skill
from app.models.application import Application
from app.models.job import Job
from app.models.user import User

logger = logging.getLogger(__name__)


class TestCandidateListPage:
    """Tests for GET /dashboard/candidates"""

    async def test_list_candidates_as_admin(
        self, admin_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await admin_client.get("/dashboard/candidates", follow_redirects=True)
        assert response.status_code == 200
        assert "Jane" in response.text
        assert "Doe" in response.text

    async def test_list_candidates_as_recruiter(
        self, recruiter_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await recruiter_client.get("/dashboard/candidates", follow_redirects=True)
        assert response.status_code == 200
        assert "jane.doe@example.com" in response.text

    async def test_list_candidates_forbidden_for_interviewer(
        self, interviewer_client: AsyncClient
    ):
        response = await interviewer_client.get(
            "/dashboard/candidates", follow_redirects=True
        )
        assert response.status_code == 403

    async def test_list_candidates_forbidden_for_hiring_manager(
        self, hiring_manager_client: AsyncClient
    ):
        response = await hiring_manager_client.get(
            "/dashboard/candidates", follow_redirects=True
        )
        assert response.status_code == 403

    async def test_list_candidates_unauthenticated_redirects_to_login(
        self, async_client: AsyncClient
    ):
        response = await async_client.get(
            "/dashboard/candidates", follow_redirects=False
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    async def test_list_candidates_search_by_name(
        self, admin_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await admin_client.get(
            "/dashboard/candidates?search=Jane", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Jane" in response.text

    async def test_list_candidates_search_no_results(
        self, admin_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await admin_client.get(
            "/dashboard/candidates?search=NonExistentPerson", follow_redirects=True
        )
        assert response.status_code == 200
        assert "No candidates found" in response.text

    async def test_list_candidates_filter_by_skill(
        self, admin_client: AsyncClient, db_session: AsyncSession, sample_candidate: Candidate
    ):
        skill = Skill(name="Python")
        db_session.add(skill)
        await db_session.flush()
        await db_session.refresh(skill)
        sample_candidate.skills.append(skill)
        await db_session.flush()

        response = await admin_client.get(
            "/dashboard/candidates?skill=Python", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Jane" in response.text

    async def test_list_candidates_empty(self, admin_client: AsyncClient):
        response = await admin_client.get("/dashboard/candidates", follow_redirects=True)
        assert response.status_code == 200
        assert "No candidates found" in response.text


class TestCandidateCreateForm:
    """Tests for GET /dashboard/candidates/create"""

    async def test_create_form_as_admin(self, admin_client: AsyncClient):
        response = await admin_client.get(
            "/dashboard/candidates/create", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Add New Candidate" in response.text

    async def test_create_form_as_recruiter(self, recruiter_client: AsyncClient):
        response = await recruiter_client.get(
            "/dashboard/candidates/create", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Add New Candidate" in response.text

    async def test_create_form_forbidden_for_interviewer(
        self, interviewer_client: AsyncClient
    ):
        response = await interviewer_client.get(
            "/dashboard/candidates/create", follow_redirects=True
        )
        assert response.status_code == 403

    async def test_create_form_unauthenticated_redirects(
        self, async_client: AsyncClient
    ):
        response = await async_client.get(
            "/dashboard/candidates/create", follow_redirects=False
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")


class TestCandidateCreate:
    """Tests for POST /dashboard/candidates"""

    async def test_create_candidate_success(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/dashboard/candidates",
            data={
                "first_name": "John",
                "last_name": "Smith",
                "email": "john.smith@example.com",
                "phone": "+1-555-0200",
                "linkedin_url": "https://linkedin.com/in/johnsmith",
                "skills": "Python, FastAPI, SQL",
                "resume_text": "Experienced developer with 5 years of experience.",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard/candidates/" in response.headers.get("location", "")

    async def test_create_candidate_minimal_fields(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/dashboard/candidates",
            data={
                "first_name": "Alice",
                "last_name": "Wonder",
                "email": "alice.wonder@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard/candidates/" in response.headers.get("location", "")

    async def test_create_candidate_with_skills(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/dashboard/candidates",
            data={
                "first_name": "Bob",
                "last_name": "Builder",
                "email": "bob.builder@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "Docker, Kubernetes, AWS",
                "resume_text": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "/dashboard/candidates/" in location

        detail_response = await admin_client.get(location, follow_redirects=True)
        assert detail_response.status_code == 200
        assert "Docker" in detail_response.text
        assert "Kubernetes" in detail_response.text
        assert "AWS" in detail_response.text

    async def test_create_candidate_duplicate_email(
        self, admin_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await admin_client.post(
            "/dashboard/candidates",
            data={
                "first_name": "Another",
                "last_name": "Person",
                "email": "jane.doe@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 400
        assert "already exists" in response.text

    async def test_create_candidate_as_recruiter(self, recruiter_client: AsyncClient):
        response = await recruiter_client.post(
            "/dashboard/candidates",
            data={
                "first_name": "Recruiter",
                "last_name": "Created",
                "email": "recruiter.created@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard/candidates/" in response.headers.get("location", "")

    async def test_create_candidate_forbidden_for_interviewer(
        self, interviewer_client: AsyncClient
    ):
        response = await interviewer_client.post(
            "/dashboard/candidates",
            data={
                "first_name": "Test",
                "last_name": "User",
                "email": "test.user@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 403

    async def test_create_candidate_forbidden_for_hiring_manager(
        self, hiring_manager_client: AsyncClient
    ):
        response = await hiring_manager_client.post(
            "/dashboard/candidates",
            data={
                "first_name": "Test",
                "last_name": "User",
                "email": "test.hm@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 403

    async def test_create_candidate_unauthenticated_redirects(
        self, async_client: AsyncClient
    ):
        response = await async_client.post(
            "/dashboard/candidates",
            data={
                "first_name": "Test",
                "last_name": "User",
                "email": "test.unauth@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")


class TestCandidateDetail:
    """Tests for GET /dashboard/candidates/{candidate_id}"""

    async def test_view_candidate_detail_as_admin(
        self, admin_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await admin_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Jane" in response.text
        assert "Doe" in response.text
        assert "jane.doe@example.com" in response.text

    async def test_view_candidate_detail_as_recruiter(
        self, recruiter_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await recruiter_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Jane" in response.text

    async def test_view_candidate_detail_as_hiring_manager(
        self, hiring_manager_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await hiring_manager_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Jane" in response.text

    async def test_view_candidate_detail_as_interviewer(
        self, interviewer_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await interviewer_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Jane" in response.text

    async def test_view_candidate_detail_not_found(self, admin_client: AsyncClient):
        response = await admin_client.get(
            "/dashboard/candidates/99999", follow_redirects=True
        )
        assert response.status_code == 404

    async def test_view_candidate_detail_unauthenticated_redirects(
        self, async_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await async_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=False
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    async def test_view_candidate_with_skills(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        sample_candidate: Candidate,
    ):
        skill1 = Skill(name="React")
        skill2 = Skill(name="TypeScript")
        db_session.add(skill1)
        db_session.add(skill2)
        await db_session.flush()
        sample_candidate.skills.append(skill1)
        sample_candidate.skills.append(skill2)
        await db_session.flush()

        response = await admin_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert "React" in response.text
        assert "TypeScript" in response.text

    async def test_view_candidate_with_resume(
        self, admin_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await admin_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Experienced software engineer" in response.text

    async def test_view_candidate_with_application_history(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        sample_candidate: Candidate,
        sample_job: Job,
    ):
        application = Application(
            job_id=sample_job.id,
            candidate_id=sample_candidate.id,
            status="Applied",
        )
        db_session.add(application)
        await db_session.flush()

        response = await admin_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Application History" in response.text
        assert "Senior Backend Engineer" in response.text
        assert "Applied" in response.text


class TestCandidateEditForm:
    """Tests for GET /dashboard/candidates/{candidate_id}/edit"""

    async def test_edit_form_as_admin(
        self, admin_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await admin_client.get(
            f"/dashboard/candidates/{sample_candidate.id}/edit", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Edit Candidate" in response.text
        assert "Jane" in response.text

    async def test_edit_form_as_recruiter(
        self, recruiter_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await recruiter_client.get(
            f"/dashboard/candidates/{sample_candidate.id}/edit", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Edit Candidate" in response.text

    async def test_edit_form_forbidden_for_interviewer(
        self, interviewer_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await interviewer_client.get(
            f"/dashboard/candidates/{sample_candidate.id}/edit", follow_redirects=True
        )
        assert response.status_code == 403

    async def test_edit_form_forbidden_for_hiring_manager(
        self, hiring_manager_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await hiring_manager_client.get(
            f"/dashboard/candidates/{sample_candidate.id}/edit", follow_redirects=True
        )
        assert response.status_code == 403

    async def test_edit_form_not_found(self, admin_client: AsyncClient):
        response = await admin_client.get(
            "/dashboard/candidates/99999/edit", follow_redirects=True
        )
        assert response.status_code == 404

    async def test_edit_form_unauthenticated_redirects(
        self, async_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await async_client.get(
            f"/dashboard/candidates/{sample_candidate.id}/edit", follow_redirects=False
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")


class TestCandidateUpdate:
    """Tests for POST /dashboard/candidates/{candidate_id}"""

    async def test_update_candidate_success(
        self, admin_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await admin_client.post(
            f"/dashboard/candidates/{sample_candidate.id}",
            data={
                "first_name": "Janet",
                "last_name": "Doe-Smith",
                "email": "janet.doesmith@example.com",
                "phone": "+1-555-0300",
                "linkedin_url": "https://linkedin.com/in/janetdoesmith",
                "skills": "Go, Rust",
                "resume_text": "Updated resume text.",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert f"/dashboard/candidates/{sample_candidate.id}" in location

        detail_response = await admin_client.get(location, follow_redirects=True)
        assert detail_response.status_code == 200
        assert "Janet" in detail_response.text
        assert "Doe-Smith" in detail_response.text
        assert "janet.doesmith@example.com" in detail_response.text

    async def test_update_candidate_skills(
        self, admin_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await admin_client.post(
            f"/dashboard/candidates/{sample_candidate.id}",
            data={
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane.doe@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "Python, FastAPI, Docker",
                "resume_text": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

        detail_response = await admin_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=True
        )
        assert detail_response.status_code == 200
        assert "Python" in detail_response.text
        assert "FastAPI" in detail_response.text
        assert "Docker" in detail_response.text

    async def test_update_candidate_remove_skills(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        sample_candidate: Candidate,
    ):
        skill = Skill(name="OldSkill")
        db_session.add(skill)
        await db_session.flush()
        sample_candidate.skills.append(skill)
        await db_session.flush()

        response = await admin_client.post(
            f"/dashboard/candidates/{sample_candidate.id}",
            data={
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane.doe@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

        detail_response = await admin_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=True
        )
        assert detail_response.status_code == 200
        assert "OldSkill" not in detail_response.text

    async def test_update_candidate_duplicate_email(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        sample_candidate: Candidate,
    ):
        other_candidate = Candidate(
            first_name="Other",
            last_name="Person",
            email="other.person@example.com",
            phone=None,
        )
        db_session.add(other_candidate)
        await db_session.flush()

        response = await admin_client.post(
            f"/dashboard/candidates/{sample_candidate.id}",
            data={
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "other.person@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 400
        assert "already exists" in response.text

    async def test_update_candidate_as_recruiter(
        self, recruiter_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await recruiter_client.post(
            f"/dashboard/candidates/{sample_candidate.id}",
            data={
                "first_name": "Jane",
                "last_name": "Updated",
                "email": "jane.doe@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

    async def test_update_candidate_forbidden_for_interviewer(
        self, interviewer_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await interviewer_client.post(
            f"/dashboard/candidates/{sample_candidate.id}",
            data={
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane.doe@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 403

    async def test_update_candidate_forbidden_for_hiring_manager(
        self, hiring_manager_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await hiring_manager_client.post(
            f"/dashboard/candidates/{sample_candidate.id}",
            data={
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane.doe@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 403

    async def test_update_candidate_not_found(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/dashboard/candidates/99999",
            data={
                "first_name": "Ghost",
                "last_name": "User",
                "email": "ghost@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 404

    async def test_update_candidate_unauthenticated_redirects(
        self, async_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await async_client.post(
            f"/dashboard/candidates/{sample_candidate.id}",
            data={
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane.doe@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "",
                "resume_text": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")


class TestCandidateSkillManagement:
    """Tests for skill tag add/remove via candidate create/update (many-to-many)"""

    async def test_create_candidate_with_multiple_skills(
        self, admin_client: AsyncClient
    ):
        response = await admin_client.post(
            "/dashboard/candidates",
            data={
                "first_name": "Skill",
                "last_name": "Tester",
                "email": "skill.tester@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "Python, JavaScript, Go, Rust, C++",
                "resume_text": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        location = response.headers.get("location", "")

        detail_response = await admin_client.get(location, follow_redirects=True)
        assert detail_response.status_code == 200
        assert "Python" in detail_response.text
        assert "JavaScript" in detail_response.text
        assert "Go" in detail_response.text
        assert "Rust" in detail_response.text
        assert "C++" in detail_response.text

    async def test_create_candidate_with_duplicate_skills_deduplicates(
        self, admin_client: AsyncClient
    ):
        response = await admin_client.post(
            "/dashboard/candidates",
            data={
                "first_name": "Dedup",
                "last_name": "Tester",
                "email": "dedup.tester@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "Python, python, PYTHON",
                "resume_text": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        location = response.headers.get("location", "")

        detail_response = await admin_client.get(location, follow_redirects=True)
        assert detail_response.status_code == 200
        assert "Python" in detail_response.text or "python" in detail_response.text

    async def test_update_candidate_replace_skills(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        sample_candidate: Candidate,
    ):
        skill_old = Skill(name="OldTech")
        db_session.add(skill_old)
        await db_session.flush()
        sample_candidate.skills.append(skill_old)
        await db_session.flush()

        response = await admin_client.post(
            f"/dashboard/candidates/{sample_candidate.id}",
            data={
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane.doe@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "NewTech, AnotherTech",
                "resume_text": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

        detail_response = await admin_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=True
        )
        assert detail_response.status_code == 200
        assert "NewTech" in detail_response.text
        assert "AnotherTech" in detail_response.text
        assert "OldTech" not in detail_response.text

    async def test_create_candidate_with_whitespace_skills(
        self, admin_client: AsyncClient
    ):
        response = await admin_client.post(
            "/dashboard/candidates",
            data={
                "first_name": "Whitespace",
                "last_name": "Skills",
                "email": "whitespace.skills@example.com",
                "phone": "",
                "linkedin_url": "",
                "skills": "  Python  ,  FastAPI  , ",
                "resume_text": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        location = response.headers.get("location", "")

        detail_response = await admin_client.get(location, follow_redirects=True)
        assert detail_response.status_code == 200
        assert "Python" in detail_response.text
        assert "FastAPI" in detail_response.text


class TestCandidateApplicationHistory:
    """Tests for application history display on candidate detail page"""

    async def test_candidate_with_no_applications(
        self, admin_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await admin_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert "No applications found" in response.text

    async def test_candidate_with_single_application(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        sample_candidate: Candidate,
        sample_job: Job,
    ):
        application = Application(
            job_id=sample_job.id,
            candidate_id=sample_candidate.id,
            status="Screening",
        )
        db_session.add(application)
        await db_session.flush()

        response = await admin_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Senior Backend Engineer" in response.text
        assert "Screening" in response.text

    async def test_candidate_with_multiple_applications(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        sample_candidate: Candidate,
        hiring_manager_user: User,
    ):
        job1 = Job(
            title="Frontend Developer",
            department="Engineering",
            location="Remote",
            type="Full-Time",
            salary_min=80000,
            salary_max=120000,
            description="Frontend role",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        job2 = Job(
            title="DevOps Engineer",
            department="Engineering",
            location="New York",
            type="Full-Time",
            salary_min=100000,
            salary_max=150000,
            description="DevOps role",
            status="Published",
            hiring_manager_id=hiring_manager_user.id,
        )
        db_session.add(job1)
        db_session.add(job2)
        await db_session.flush()

        app1 = Application(
            job_id=job1.id,
            candidate_id=sample_candidate.id,
            status="Applied",
        )
        app2 = Application(
            job_id=job2.id,
            candidate_id=sample_candidate.id,
            status="Interview",
        )
        db_session.add(app1)
        db_session.add(app2)
        await db_session.flush()

        response = await admin_client.get(
            f"/dashboard/candidates/{sample_candidate.id}", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Frontend Developer" in response.text
        assert "DevOps Engineer" in response.text
        assert "Applied" in response.text
        assert "Interview" in response.text


class TestCandidateServiceLayer:
    """Tests for candidate service functions directly"""

    async def test_create_candidate_service(self, db_session: AsyncSession):
        from app.services.candidate_service import create_candidate

        candidate = await create_candidate(
            db=db_session,
            first_name="Service",
            last_name="Test",
            email="service.test@example.com",
            phone="+1-555-0400",
            skill_names=["Python", "SQL"],
        )
        assert candidate.id is not None
        assert candidate.first_name == "Service"
        assert candidate.last_name == "Test"
        assert candidate.email == "service.test@example.com"
        assert len(candidate.skills) == 2

    async def test_create_candidate_service_duplicate_email(
        self, db_session: AsyncSession, sample_candidate: Candidate
    ):
        from app.services.candidate_service import create_candidate

        with pytest.raises(ValueError, match="already exists"):
            await create_candidate(
                db=db_session,
                first_name="Duplicate",
                last_name="Email",
                email="jane.doe@example.com",
            )

    async def test_edit_candidate_service(
        self, db_session: AsyncSession, sample_candidate: Candidate
    ):
        from app.services.candidate_service import edit_candidate

        updated = await edit_candidate(
            db=db_session,
            candidate_id=sample_candidate.id,
            first_name="Updated",
            last_name="Name",
            email="updated.name@example.com",
            skill_names=["NewSkill"],
        )
        assert updated.first_name == "Updated"
        assert updated.last_name == "Name"
        assert updated.email == "updated.name@example.com"
        assert len(updated.skills) == 1
        assert updated.skills[0].name == "NewSkill"

    async def test_edit_candidate_service_not_found(self, db_session: AsyncSession):
        from app.services.candidate_service import edit_candidate

        with pytest.raises(ValueError, match="not found"):
            await edit_candidate(
                db=db_session,
                candidate_id=99999,
                first_name="Ghost",
            )

    async def test_get_candidate_service(
        self, db_session: AsyncSession, sample_candidate: Candidate
    ):
        from app.services.candidate_service import get_candidate

        candidate = await get_candidate(db_session, sample_candidate.id)
        assert candidate is not None
        assert candidate.id == sample_candidate.id
        assert candidate.first_name == "Jane"

    async def test_get_candidate_service_not_found(self, db_session: AsyncSession):
        from app.services.candidate_service import get_candidate

        candidate = await get_candidate(db_session, 99999)
        assert candidate is None

    async def test_list_candidates_service(
        self, db_session: AsyncSession, sample_candidate: Candidate
    ):
        from app.services.candidate_service import list_candidates

        candidates, total = await list_candidates(db=db_session)
        assert total >= 1
        assert any(c.id == sample_candidate.id for c in candidates)

    async def test_list_candidates_service_with_search(
        self, db_session: AsyncSession, sample_candidate: Candidate
    ):
        from app.services.candidate_service import list_candidates

        candidates, total = await list_candidates(db=db_session, search="Jane")
        assert total >= 1
        assert any(c.first_name == "Jane" for c in candidates)

    async def test_list_candidates_service_search_no_match(
        self, db_session: AsyncSession, sample_candidate: Candidate
    ):
        from app.services.candidate_service import list_candidates

        candidates, total = await list_candidates(db=db_session, search="ZZZNonExistent")
        assert total == 0
        assert len(candidates) == 0

    async def test_add_skill_service(
        self, db_session: AsyncSession, sample_candidate: Candidate
    ):
        from app.services.candidate_service import add_skill

        updated = await add_skill(db_session, sample_candidate.id, "NewSkill")
        assert any(s.name == "NewSkill" for s in updated.skills)

    async def test_add_skill_service_duplicate(
        self, db_session: AsyncSession, sample_candidate: Candidate
    ):
        from app.services.candidate_service import add_skill

        await add_skill(db_session, sample_candidate.id, "DuplicateSkill")
        updated = await add_skill(db_session, sample_candidate.id, "DuplicateSkill")
        skill_count = sum(1 for s in updated.skills if s.name == "DuplicateSkill")
        assert skill_count == 1

    async def test_add_skill_service_candidate_not_found(
        self, db_session: AsyncSession
    ):
        from app.services.candidate_service import add_skill

        with pytest.raises(ValueError, match="not found"):
            await add_skill(db_session, 99999, "SomeSkill")

    async def test_remove_skill_service(
        self, db_session: AsyncSession, sample_candidate: Candidate
    ):
        from app.services.candidate_service import add_skill, remove_skill

        await add_skill(db_session, sample_candidate.id, "RemovableSkill")
        updated = await remove_skill(db_session, sample_candidate.id, "RemovableSkill")
        assert not any(s.name == "RemovableSkill" for s in updated.skills)

    async def test_remove_skill_service_nonexistent_skill(
        self, db_session: AsyncSession, sample_candidate: Candidate
    ):
        from app.services.candidate_service import remove_skill

        updated = await remove_skill(
            db_session, sample_candidate.id, "NonExistentSkill"
        )
        assert updated is not None

    async def test_remove_skill_service_candidate_not_found(
        self, db_session: AsyncSession
    ):
        from app.services.candidate_service import remove_skill

        with pytest.raises(ValueError, match="not found"):
            await remove_skill(db_session, 99999, "SomeSkill")

    async def test_get_all_skills_service(self, db_session: AsyncSession):
        from app.services.candidate_service import get_all_skills, create_candidate

        await create_candidate(
            db=db_session,
            first_name="Skill",
            last_name="Collector",
            email="skill.collector@example.com",
            skill_names=["Alpha", "Beta", "Gamma"],
        )

        skills = await get_all_skills(db_session)
        skill_names = [s.name for s in skills]
        assert "Alpha" in skill_names
        assert "Beta" in skill_names
        assert "Gamma" in skill_names


class TestCandidatePagination:
    """Tests for candidate list pagination"""

    async def test_pagination_default_page(
        self, admin_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await admin_client.get(
            "/dashboard/candidates?page=1", follow_redirects=True
        )
        assert response.status_code == 200
        assert "Jane" in response.text

    async def test_pagination_invalid_page_defaults(
        self, admin_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await admin_client.get(
            "/dashboard/candidates?page=0", follow_redirects=True
        )
        assert response.status_code == 200

    async def test_pagination_high_page_number(
        self, admin_client: AsyncClient, sample_candidate: Candidate
    ):
        response = await admin_client.get(
            "/dashboard/candidates?page=999", follow_redirects=True
        )
        assert response.status_code == 200