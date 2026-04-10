import logging
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

VALID_ROLES = ["System Admin", "HR Recruiter", "Hiring Manager", "Interviewer"]


async def get_optional_user(request: Request, db: AsyncSession) -> Optional[object]:
    """Get the current user if logged in, or None if not authenticated.

    Use this dependency for routes that work for both guests and logged-in users
    (e.g., landing page, public job listings).
    """
    try:
        user = await get_current_user(request, db)
        return user
    except Exception:
        logger.debug("No authenticated user found for request %s", request.url.path)
        return None


def require_role(allowed_roles: list[str]):
    """Dependency factory that enforces role-based access control.

    Returns a FastAPI dependency that checks the current user's role against
    the provided list of allowed roles using exact string matching.

    Raises:
        HTTPException(401): If the user is not authenticated.
        HTTPException(403): If the user's role is not in the allowed roles list.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role(["System Admin"]))])
        async def admin_page(): ...

        Or as a parameter dependency:
        async def admin_page(user = Depends(require_role(["System Admin"]))): ...
    """
    for role in allowed_roles:
        if role not in VALID_ROLES:
            logger.warning(
                "require_role called with invalid role '%s'. Valid roles: %s",
                role,
                VALID_ROLES,
            )

    async def role_dependency(request: Request, db: AsyncSession) -> object:
        user = await get_current_user(request, db)
        if user is None:
            logger.info(
                "Unauthenticated access attempt to %s — redirecting to login",
                request.url.path,
            )
            raise HTTPException(status_code=401, detail="Authentication required")

        if user.role not in allowed_roles:
            logger.warning(
                "User id=%s (role='%s') denied access to %s. Required roles: %s",
                user.id,
                user.role,
                request.url.path,
                allowed_roles,
            )
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {', '.join(allowed_roles)}",
            )

        return user

    return role_dependency


def require_role_redirect(allowed_roles: list[str]):
    """Dependency factory similar to require_role but redirects to login page
    instead of raising HTTPException for unauthenticated users.

    Use this for HTML page routes where a redirect is more user-friendly
    than a JSON error response.

    Raises:
        RedirectResponse: If the user is not authenticated (redirects to /auth/login).
        HTTPException(403): If the user's role is not in the allowed roles list.
    """
    for role in allowed_roles:
        if role not in VALID_ROLES:
            logger.warning(
                "require_role_redirect called with invalid role '%s'. Valid roles: %s",
                role,
                VALID_ROLES,
            )

    async def role_dependency(request: Request, db: AsyncSession) -> object:
        user = await get_current_user(request, db)
        if user is None:
            logger.info(
                "Unauthenticated access attempt to %s — redirecting to login",
                request.url.path,
            )
            return RedirectResponse(url="/auth/login", status_code=302)

        if user.role not in allowed_roles:
            logger.warning(
                "User id=%s (role='%s') denied access to %s. Required roles: %s",
                user.id,
                user.role,
                request.url.path,
                allowed_roles,
            )
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {', '.join(allowed_roles)}",
            )

        return user

    return role_dependency


async def get_authenticated_user(request: Request, db: AsyncSession) -> object:
    """Dependency that requires an authenticated user regardless of role.

    Raises:
        HTTPException(401): If the user is not authenticated.
    """
    user = await get_current_user(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def get_authenticated_user_redirect(request: Request, db: AsyncSession):
    """Dependency that requires an authenticated user, redirecting to login if not.

    Returns the user object if authenticated, or a RedirectResponse to /auth/login.
    """
    user = await get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)
    return user