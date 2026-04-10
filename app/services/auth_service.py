import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.user import User

logger = logging.getLogger(__name__)


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    user = await get_user_by_username(db, username)
    if user is None:
        logger.info("Authentication failed: user '%s' not found", username)
        return None
    if not user.is_active:
        logger.info("Authentication failed: user '%s' is inactive", username)
        return None
    if not verify_password(password, user.password_hash):
        logger.info("Authentication failed: invalid password for user '%s'", username)
        return None
    logger.info("User '%s' authenticated successfully", username)
    return user


async def register_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    full_name: Optional[str] = None,
    role: str = "Interviewer",
) -> User:
    existing_user = await get_user_by_username(db, username)
    if existing_user is not None:
        raise ValueError("Username already exists")

    existing_email = await get_user_by_email(db, email.strip().lower())
    if existing_email is not None:
        raise ValueError("Email already exists")

    hashed = hash_password(password)
    user = User(
        username=username.strip(),
        email=email.strip().lower(),
        password_hash=hashed,
        full_name=full_name.strip() if full_name else None,
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    logger.info("Registered new user '%s' with role '%s'", username, role)
    return user


async def create_default_admin(db: AsyncSession) -> None:
    existing_admin = await get_user_by_username(db, settings.DEFAULT_ADMIN_USERNAME)
    if existing_admin is not None:
        logger.info("Default admin user '%s' already exists, skipping creation", settings.DEFAULT_ADMIN_USERNAME)
        return

    hashed = hash_password(settings.DEFAULT_ADMIN_PASSWORD)
    admin_user = User(
        username=settings.DEFAULT_ADMIN_USERNAME,
        email=f"{settings.DEFAULT_ADMIN_USERNAME}@talentflow.local",
        password_hash=hashed,
        full_name="System Administrator",
        role="System Admin",
        is_active=True,
    )
    db.add(admin_user)
    await db.flush()
    logger.info("Created default admin user '%s' with role 'System Admin'", settings.DEFAULT_ADMIN_USERNAME)


async def get_all_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


async def get_users_by_role(db: AsyncSession, role: str) -> list[User]:
    result = await db.execute(
        select(User).where(User.role == role, User.is_active == True).order_by(User.full_name)
    )
    return list(result.scalars().all())


async def update_user_role(db: AsyncSession, user_id: int, new_role: str) -> Optional[User]:
    allowed_roles = {"System Admin", "HR Recruiter", "Hiring Manager", "Interviewer"}
    if new_role not in allowed_roles:
        raise ValueError(f"Invalid role '{new_role}'. Must be one of: {', '.join(sorted(allowed_roles))}")

    user = await get_user_by_id(db, user_id)
    if user is None:
        return None

    user.role = new_role
    await db.flush()
    await db.refresh(user)
    logger.info("Updated user '%s' role to '%s'", user.username, new_role)
    return user


async def deactivate_user(db: AsyncSession, user_id: int) -> Optional[User]:
    user = await get_user_by_id(db, user_id)
    if user is None:
        return None

    user.is_active = False
    await db.flush()
    await db.refresh(user)
    logger.info("Deactivated user '%s'", user.username)
    return user