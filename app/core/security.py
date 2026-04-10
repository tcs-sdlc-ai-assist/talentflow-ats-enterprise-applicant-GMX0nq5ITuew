import logging
from typing import Optional

from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SESSION_COOKIE_NAME = "session"
SESSION_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

serializer = URLSafeTimedSerializer(settings.SECRET_KEY)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        logger.warning("Password verification failed due to an unexpected error")
        return False


def create_session_cookie(user_id: int, role: str) -> str:
    payload = {"user_id": user_id, "role": role}
    return serializer.dumps(payload)


def read_session_cookie(cookie_value: str) -> Optional[dict]:
    try:
        payload = serializer.loads(cookie_value, max_age=SESSION_MAX_AGE)
        if not isinstance(payload, dict):
            return None
        if "user_id" not in payload or "role" not in payload:
            return None
        return payload
    except SignatureExpired:
        logger.info("Session cookie has expired")
        return None
    except BadSignature:
        logger.warning("Session cookie has an invalid signature")
        return None
    except Exception:
        logger.warning("Failed to read session cookie")
        return None


def set_session_cookie(response: Response, user_id: int, role: str) -> None:
    cookie_value = create_session_cookie(user_id, role)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=cookie_value,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=not settings.DEBUG,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=not settings.DEBUG,
    )


async def get_current_user(request: Request, db: AsyncSession) -> Optional[object]:
    from app.models.user import User

    cookie_value = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie_value:
        return None

    payload = read_session_cookie(cookie_value)
    if payload is None:
        return None

    user_id = payload.get("user_id")
    if user_id is None:
        return None

    try:
        result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
        user = result.scalars().first()
        if user is None:
            logger.info("Session references non-existent or inactive user id=%s", user_id)
            return None
        if user.role != payload.get("role"):
            logger.warning(
                "Session role mismatch for user id=%s: cookie=%s, db=%s",
                user_id,
                payload.get("role"),
                user.role,
            )
            return None
        return user
    except Exception:
        logger.exception("Error fetching user from session, user_id=%s", user_id)
        return None


async def get_current_user_required(request: Request, db: AsyncSession) -> object:
    from fastapi import HTTPException

    user = await get_current_user(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_role(allowed_roles: list[str]):
    async def dependency(request: Request, db: AsyncSession) -> object:
        from fastapi import HTTPException

        user = await get_current_user(request, db)
        if user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {', '.join(allowed_roles)}",
            )
        return user

    return dependency