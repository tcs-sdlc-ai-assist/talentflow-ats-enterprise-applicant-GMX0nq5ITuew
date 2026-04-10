import logging

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, read_session_cookie, SESSION_COOKIE_NAME
from app.models.user import User


logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestRegistration:
    """Tests for user registration flow."""

    async def test_register_page_renders(self, async_client: AsyncClient):
        """GET /auth/register returns the registration form."""
        response = await async_client.get("/auth/register")
        assert response.status_code == 200
        assert "Create your account" in response.text

    async def test_register_success_creates_interviewer(self, async_client: AsyncClient, db_session: AsyncSession):
        """Successful registration creates a user with Interviewer role and sets session cookie."""
        response = await async_client.post(
            "/auth/register",
            data={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "securepass123",
                "confirm_password": "securepass123",
                "full_name": "New User",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard/interviews/my" in response.headers.get("location", "")

        cookie_value = response.cookies.get(SESSION_COOKIE_NAME)
        assert cookie_value is not None

        payload = read_session_cookie(cookie_value)
        assert payload is not None
        assert payload["role"] == "Interviewer"

    async def test_register_duplicate_username(self, async_client: AsyncClient, admin_user: User):
        """Registration with an existing username returns an error."""
        response = await async_client.post(
            "/auth/register",
            data={
                "username": "testadmin",
                "email": "different@example.com",
                "password": "securepass123",
                "confirm_password": "securepass123",
                "full_name": "Duplicate User",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Username already exists" in response.text

    async def test_register_duplicate_email(self, async_client: AsyncClient, admin_user: User):
        """Registration with an existing email returns an error."""
        response = await async_client.post(
            "/auth/register",
            data={
                "username": "uniqueuser",
                "email": "testadmin@talentflow.local",
                "password": "securepass123",
                "confirm_password": "securepass123",
                "full_name": "Duplicate Email User",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Email already exists" in response.text

    async def test_register_password_mismatch(self, async_client: AsyncClient):
        """Registration with mismatched passwords returns a validation error."""
        response = await async_client.post(
            "/auth/register",
            data={
                "username": "mismatchuser",
                "email": "mismatch@example.com",
                "password": "securepass123",
                "confirm_password": "differentpass456",
                "full_name": "Mismatch User",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Passwords do not match" in response.text

    async def test_register_short_password(self, async_client: AsyncClient):
        """Registration with a password shorter than 8 characters returns a validation error."""
        response = await async_client.post(
            "/auth/register",
            data={
                "username": "shortpwduser",
                "email": "shortpwd@example.com",
                "password": "short",
                "confirm_password": "short",
                "full_name": "Short Password User",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Password must be at least 8 characters" in response.text

    async def test_register_short_username(self, async_client: AsyncClient):
        """Registration with a username shorter than 3 characters returns a validation error."""
        response = await async_client.post(
            "/auth/register",
            data={
                "username": "ab",
                "email": "shortname@example.com",
                "password": "securepass123",
                "confirm_password": "securepass123",
                "full_name": "Short Name User",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Username must be at least 3 characters" in response.text

    async def test_register_invalid_username_characters(self, async_client: AsyncClient):
        """Registration with special characters in username returns a validation error."""
        response = await async_client.post(
            "/auth/register",
            data={
                "username": "bad user!",
                "email": "baduser@example.com",
                "password": "securepass123",
                "confirm_password": "securepass123",
                "full_name": "Bad Username User",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "alphanumeric" in response.text

    async def test_register_missing_email(self, async_client: AsyncClient):
        """Registration without an email returns a 422 (FastAPI form validation)."""
        response = await async_client.post(
            "/auth/register",
            data={
                "username": "noemailuser",
                "password": "securepass123",
                "confirm_password": "securepass123",
                "full_name": "No Email User",
            },
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_register_redirects_if_already_logged_in(self, admin_client: AsyncClient):
        """Authenticated users accessing /auth/register are redirected to dashboard."""
        response = await admin_client.get("/auth/register", follow_redirects=False)
        assert response.status_code == 302
        assert "/dashboard" in response.headers.get("location", "")


@pytest.mark.asyncio
class TestLogin:
    """Tests for user login flow."""

    async def test_login_page_renders(self, async_client: AsyncClient):
        """GET /auth/login returns the login form."""
        response = await async_client.get("/auth/login")
        assert response.status_code == 200
        assert "Sign in to TalentFlow" in response.text

    async def test_login_success_admin(self, async_client: AsyncClient, admin_user: User):
        """Successful login as System Admin redirects to /dashboard."""
        response = await async_client.post(
            "/auth/login",
            data={"username": "testadmin", "password": "adminpass123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers.get("location") == "/dashboard"

        cookie_value = response.cookies.get(SESSION_COOKIE_NAME)
        assert cookie_value is not None

        payload = read_session_cookie(cookie_value)
        assert payload is not None
        assert payload["role"] == "System Admin"
        assert payload["user_id"] == admin_user.id

    async def test_login_success_recruiter(self, async_client: AsyncClient, recruiter_user: User):
        """Successful login as HR Recruiter redirects to /dashboard."""
        response = await async_client.post(
            "/auth/login",
            data={"username": "testrecruiter", "password": "recruiterpass123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers.get("location") == "/dashboard"

    async def test_login_success_hiring_manager(self, async_client: AsyncClient, hiring_manager_user: User):
        """Successful login as Hiring Manager redirects to /dashboard."""
        response = await async_client.post(
            "/auth/login",
            data={"username": "testhiringmgr", "password": "hiringmgrpass123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers.get("location") == "/dashboard"

    async def test_login_success_interviewer(self, async_client: AsyncClient, interviewer_user: User):
        """Successful login as Interviewer redirects to /dashboard/interviews/my."""
        response = await async_client.post(
            "/auth/login",
            data={"username": "testinterviewer", "password": "interviewerpass123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers.get("location") == "/dashboard/interviews/my"

    async def test_login_wrong_password(self, async_client: AsyncClient, admin_user: User):
        """Login with incorrect password returns 401 with error message."""
        response = await async_client.post(
            "/auth/login",
            data={"username": "testadmin", "password": "wrongpassword"},
            follow_redirects=False,
        )
        assert response.status_code == 401
        assert "Invalid username or password" in response.text

    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Login with a non-existent username returns 401 with error message."""
        response = await async_client.post(
            "/auth/login",
            data={"username": "ghostuser", "password": "somepassword123"},
            follow_redirects=False,
        )
        assert response.status_code == 401
        assert "Invalid username or password" in response.text

    async def test_login_inactive_user(self, async_client: AsyncClient, inactive_user: User):
        """Login with an inactive user returns 401."""
        response = await async_client.post(
            "/auth/login",
            data={"username": "inactiveuser", "password": "inactivepass123"},
            follow_redirects=False,
        )
        assert response.status_code == 401
        assert "Invalid username or password" in response.text

    async def test_login_empty_username(self, async_client: AsyncClient):
        """Login with empty username returns 400."""
        response = await async_client.post(
            "/auth/login",
            data={"username": "", "password": "somepassword"},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Username and password are required" in response.text

    async def test_login_empty_password(self, async_client: AsyncClient):
        """Login with empty password returns 400."""
        response = await async_client.post(
            "/auth/login",
            data={"username": "testadmin", "password": ""},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Username and password are required" in response.text

    async def test_login_redirects_if_already_logged_in(self, admin_client: AsyncClient):
        """Authenticated users accessing /auth/login are redirected to dashboard."""
        response = await admin_client.get("/auth/login", follow_redirects=False)
        assert response.status_code == 302
        assert "/dashboard" in response.headers.get("location", "")


@pytest.mark.asyncio
class TestLogout:
    """Tests for user logout flow."""

    async def test_logout_clears_session_cookie(self, admin_client: AsyncClient):
        """POST /auth/logout clears the session cookie and redirects to /."""
        response = await admin_client.post("/auth/logout", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers.get("location") == "/"

        set_cookie_header = response.headers.get("set-cookie", "")
        assert SESSION_COOKIE_NAME in set_cookie_header

    async def test_logout_unauthenticated_user(self, async_client: AsyncClient):
        """POST /auth/logout works even for unauthenticated users (no crash)."""
        response = await async_client.post("/auth/logout", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers.get("location") == "/"


@pytest.mark.asyncio
class TestSessionCookieValidation:
    """Tests for session cookie security and validation."""

    async def test_valid_session_cookie_grants_access(self, admin_client: AsyncClient):
        """A valid session cookie allows access to protected pages."""
        response = await admin_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200

    async def test_missing_session_cookie_redirects_to_login(self, async_client: AsyncClient):
        """Accessing a protected page without a session cookie redirects to login."""
        response = await async_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    async def test_tampered_session_cookie_redirects_to_login(self, async_client: AsyncClient):
        """A tampered session cookie is rejected and user is redirected to login."""
        async_client.cookies.set(SESSION_COOKIE_NAME, "tampered.invalid.cookie")
        response = await async_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    async def test_empty_session_cookie_redirects_to_login(self, async_client: AsyncClient):
        """An empty session cookie is rejected and user is redirected to login."""
        async_client.cookies.set(SESSION_COOKIE_NAME, "")
        response = await async_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    async def test_session_cookie_role_mismatch_redirects(
        self, async_client: AsyncClient, admin_user: User
    ):
        """A session cookie with a role that doesn't match the DB is rejected."""
        from app.core.security import create_session_cookie

        fake_cookie = create_session_cookie(admin_user.id, "Interviewer")
        async_client.cookies.set(SESSION_COOKIE_NAME, fake_cookie)

        response = await async_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")

    async def test_session_cookie_nonexistent_user_redirects(self, async_client: AsyncClient):
        """A session cookie referencing a non-existent user ID is rejected."""
        from app.core.security import create_session_cookie

        fake_cookie = create_session_cookie(99999, "System Admin")
        async_client.cookies.set(SESSION_COOKIE_NAME, fake_cookie)

        response = await async_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("location", "")


@pytest.mark.asyncio
class TestRoleBasedRedirects:
    """Tests for role-based dashboard redirects after login."""

    async def test_system_admin_redirects_to_dashboard(self, async_client: AsyncClient, admin_user: User):
        """System Admin login redirects to /dashboard."""
        response = await async_client.post(
            "/auth/login",
            data={"username": "testadmin", "password": "adminpass123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers.get("location") == "/dashboard"

    async def test_hr_recruiter_redirects_to_dashboard(self, async_client: AsyncClient, recruiter_user: User):
        """HR Recruiter login redirects to /dashboard."""
        response = await async_client.post(
            "/auth/login",
            data={"username": "testrecruiter", "password": "recruiterpass123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers.get("location") == "/dashboard"

    async def test_hiring_manager_redirects_to_dashboard(
        self, async_client: AsyncClient, hiring_manager_user: User
    ):
        """Hiring Manager login redirects to /dashboard."""
        response = await async_client.post(
            "/auth/login",
            data={"username": "testhiringmgr", "password": "hiringmgrpass123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers.get("location") == "/dashboard"

    async def test_interviewer_redirects_to_my_interviews(
        self, async_client: AsyncClient, interviewer_user: User
    ):
        """Interviewer login redirects to /dashboard/interviews/my."""
        response = await async_client.post(
            "/auth/login",
            data={"username": "testinterviewer", "password": "interviewerpass123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers.get("location") == "/dashboard/interviews/my"


@pytest.mark.asyncio
class TestRegistrationAndLoginIntegration:
    """Integration tests for register-then-login flow."""

    async def test_register_then_login(self, async_client: AsyncClient):
        """A newly registered user can immediately log in with their credentials."""
        register_response = await async_client.post(
            "/auth/register",
            data={
                "username": "integrationuser",
                "email": "integration@example.com",
                "password": "integrationpass123",
                "confirm_password": "integrationpass123",
                "full_name": "Integration User",
            },
            follow_redirects=False,
        )
        assert register_response.status_code == 302

        fresh_client_transport = ASGITransport(app=async_client._transport.app)
        async with AsyncClient(transport=fresh_client_transport, base_url="http://testserver") as fresh_client:
            login_response = await fresh_client.post(
                "/auth/login",
                data={"username": "integrationuser", "password": "integrationpass123"},
                follow_redirects=False,
            )
            assert login_response.status_code == 302
            assert "/dashboard/interviews/my" in login_response.headers.get("location", "")

            cookie_value = login_response.cookies.get(SESSION_COOKIE_NAME)
            assert cookie_value is not None
            payload = read_session_cookie(cookie_value)
            assert payload is not None
            assert payload["role"] == "Interviewer"

    async def test_register_logout_then_login(self, async_client: AsyncClient):
        """A user can register, logout, and then login again successfully."""
        await async_client.post(
            "/auth/register",
            data={
                "username": "logouttest",
                "email": "logouttest@example.com",
                "password": "logoutpass123",
                "confirm_password": "logoutpass123",
                "full_name": "Logout Test User",
            },
            follow_redirects=False,
        )

        logout_response = await async_client.post("/auth/logout", follow_redirects=False)
        assert logout_response.status_code == 302

        async_client.cookies.clear()

        login_response = await async_client.post(
            "/auth/login",
            data={"username": "logouttest", "password": "logoutpass123"},
            follow_redirects=False,
        )
        assert login_response.status_code == 302
        assert "/dashboard/interviews/my" in login_response.headers.get("location", "")


@pytest.mark.asyncio
class TestPasswordSecurity:
    """Tests for password hashing and verification."""

    async def test_password_is_hashed_not_stored_plaintext(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Registered user's password is stored as a bcrypt hash, not plaintext."""
        from sqlalchemy import select

        await async_client.post(
            "/auth/register",
            data={
                "username": "hashcheckuser",
                "email": "hashcheck@example.com",
                "password": "plaintextpassword",
                "confirm_password": "plaintextpassword",
                "full_name": "Hash Check User",
            },
            follow_redirects=False,
        )

        result = await db_session.execute(
            select(User).where(User.username == "hashcheckuser")
        )
        user = result.scalars().first()
        assert user is not None
        assert user.password_hash != "plaintextpassword"
        assert user.password_hash.startswith("$2b$") or user.password_hash.startswith("$2a$")

    async def test_login_fails_with_hash_as_password(
        self, async_client: AsyncClient, admin_user: User, db_session: AsyncSession
    ):
        """Attempting to login with the password hash itself fails."""
        from sqlalchemy import select

        result = await db_session.execute(
            select(User).where(User.username == "testadmin")
        )
        user = result.scalars().first()
        assert user is not None

        response = await async_client.post(
            "/auth/login",
            data={"username": "testadmin", "password": user.password_hash},
            follow_redirects=False,
        )
        assert response.status_code == 401