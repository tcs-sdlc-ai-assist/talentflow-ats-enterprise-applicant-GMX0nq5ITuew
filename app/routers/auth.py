import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    clear_session_cookie,
    get_current_user,
    set_session_cookie,
)
from app.services.auth_service import authenticate_user, register_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)

ROLE_DASHBOARD_REDIRECTS = {
    "System Admin": "/dashboard",
    "HR Recruiter": "/dashboard",
    "Hiring Manager": "/dashboard",
    "Interviewer": "/dashboard/interviews/my",
}


@router.get("/login")
async def login_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user(request, db)
    if user is not None:
        redirect_url = ROLE_DASHBOARD_REDIRECTS.get(user.role, "/dashboard")
        return RedirectResponse(url=redirect_url, status_code=302)

    return templates.TemplateResponse(
        request,
        "auth/login.html",
        context={"user": None, "error": None},
    )


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    username = username.strip()
    password = password.strip()

    if not username or not password:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={"user": None, "error": "Username and password are required."},
            status_code=400,
        )

    user = await authenticate_user(db, username, password)
    if user is None:
        logger.info("Failed login attempt for username='%s'", username)
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={"user": None, "error": "Invalid username or password."},
            status_code=401,
        )

    redirect_url = ROLE_DASHBOARD_REDIRECTS.get(user.role, "/dashboard")
    response = RedirectResponse(url=redirect_url, status_code=302)
    set_session_cookie(response, user.id, user.role)

    logger.info("User '%s' (role='%s') logged in successfully", user.username, user.role)
    return response


@router.get("/register")
async def register_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user(request, db)
    if user is not None:
        redirect_url = ROLE_DASHBOARD_REDIRECTS.get(user.role, "/dashboard")
        return RedirectResponse(url=redirect_url, status_code=302)

    return templates.TemplateResponse(
        request,
        "auth/register.html",
        context={"user": None, "error": None, "errors": None, "form_data": None},
    )


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    full_name: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    username = username.strip()
    email = email.strip().lower()
    full_name = full_name.strip()

    form_data = {
        "username": username,
        "email": email,
        "full_name": full_name,
    }

    errors = []

    if not username:
        errors.append("Username is required.")
    elif len(username) < 3:
        errors.append("Username must be at least 3 characters long.")
    elif len(username) > 32:
        errors.append("Username must be at most 32 characters long.")
    else:
        import re
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            errors.append("Username must contain only alphanumeric characters and underscores.")

    if not email:
        errors.append("Email is required.")

    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    elif len(password) > 128:
        errors.append("Password must be at most 128 characters long.")

    if not confirm_password:
        errors.append("Please confirm your password.")
    elif password != confirm_password:
        errors.append("Passwords do not match.")

    if errors:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "user": None,
                "error": None,
                "errors": errors,
                "form_data": form_data,
            },
            status_code=400,
        )

    try:
        user = await register_user(
            db=db,
            username=username,
            email=email,
            password=password,
            full_name=full_name if full_name else None,
            role="Interviewer",
        )
        await db.commit()
    except ValueError as e:
        error_message = str(e)
        logger.info("Registration failed for username='%s': %s", username, error_message)
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "user": None,
                "error": error_message,
                "errors": None,
                "form_data": form_data,
            },
            status_code=400,
        )
    except Exception:
        logger.exception("Unexpected error during registration for username='%s'", username)
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "user": None,
                "error": "An unexpected error occurred. Please try again.",
                "errors": None,
                "form_data": form_data,
            },
            status_code=500,
        )

    redirect_url = ROLE_DASHBOARD_REDIRECTS.get(user.role, "/dashboard/interviews/my")
    response = RedirectResponse(url=redirect_url, status_code=302)
    set_session_cookie(response, user.id, user.role)

    logger.info("User '%s' registered successfully with role='%s'", user.username, user.role)
    return response


@router.post("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=302)
    clear_session_cookie(response)
    logger.info("User logged out")
    return response