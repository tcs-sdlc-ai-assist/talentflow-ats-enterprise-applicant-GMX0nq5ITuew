import logging
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate, Skill, candidate_skills

logger = logging.getLogger(__name__)


async def create_candidate(
    db: AsyncSession,
    first_name: str,
    last_name: str,
    email: str,
    phone: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    resume_text: Optional[str] = None,
    skill_names: Optional[list[str]] = None,
) -> Candidate:
    existing = await db.execute(
        select(Candidate).where(func.lower(Candidate.email) == email.strip().lower())
    )
    if existing.scalars().first() is not None:
        raise ValueError(f"A candidate with email '{email}' already exists")

    candidate = Candidate(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email.strip().lower(),
        phone=phone.strip() if phone else None,
        linkedin_url=linkedin_url.strip() if linkedin_url else None,
        resume_text=resume_text.strip() if resume_text else None,
    )

    if skill_names:
        skills = await _resolve_skills(db, skill_names)
        candidate.skills = skills

    db.add(candidate)
    await db.flush()
    await db.refresh(candidate)

    logger.info("Created candidate id=%s email=%s", candidate.id, candidate.email)
    return candidate


async def edit_candidate(
    db: AsyncSession,
    candidate_id: int,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    resume_text: Optional[str] = None,
    skill_names: Optional[list[str]] = None,
) -> Candidate:
    candidate = await get_candidate(db, candidate_id)
    if candidate is None:
        raise ValueError(f"Candidate with id {candidate_id} not found")

    if email is not None:
        normalized_email = email.strip().lower()
        if normalized_email != candidate.email:
            existing = await db.execute(
                select(Candidate).where(
                    func.lower(Candidate.email) == normalized_email,
                    Candidate.id != candidate_id,
                )
            )
            if existing.scalars().first() is not None:
                raise ValueError(f"A candidate with email '{email}' already exists")
            candidate.email = normalized_email

    if first_name is not None:
        candidate.first_name = first_name.strip()
    if last_name is not None:
        candidate.last_name = last_name.strip()
    if phone is not None:
        candidate.phone = phone.strip() if phone.strip() else None
    if linkedin_url is not None:
        candidate.linkedin_url = linkedin_url.strip() if linkedin_url.strip() else None
    if resume_text is not None:
        candidate.resume_text = resume_text.strip() if resume_text.strip() else None

    if skill_names is not None:
        skills = await _resolve_skills(db, skill_names)
        candidate.skills = skills

    await db.flush()
    await db.refresh(candidate)

    logger.info("Updated candidate id=%s", candidate.id)
    return candidate


async def list_candidates(
    db: AsyncSession,
    search: Optional[str] = None,
    skill_name: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Candidate], int]:
    query = select(Candidate).options(
        selectinload(Candidate.skills),
        selectinload(Candidate.applications),
    )
    count_query = select(func.count(Candidate.id))

    if search:
        search_term = f"%{search.strip()}%"
        search_filter = or_(
            Candidate.first_name.ilike(search_term),
            Candidate.last_name.ilike(search_term),
            Candidate.email.ilike(search_term),
            Candidate.phone.ilike(search_term),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if skill_name:
        query = query.join(Candidate.skills).where(
            func.lower(Skill.name) == skill_name.strip().lower()
        )
        count_query = count_query.join(candidate_skills, candidate_skills.c.candidate_id == Candidate.id).join(
            Skill, Skill.id == candidate_skills.c.skill_id
        ).where(func.lower(Skill.name) == skill_name.strip().lower())

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.order_by(Candidate.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    candidates = list(result.scalars().unique().all())

    return candidates, total


async def get_candidate(
    db: AsyncSession,
    candidate_id: int,
) -> Optional[Candidate]:
    result = await db.execute(
        select(Candidate)
        .where(Candidate.id == candidate_id)
        .options(
            selectinload(Candidate.skills),
            selectinload(Candidate.applications),
        )
    )
    candidate = result.scalars().first()
    return candidate


async def add_skill(
    db: AsyncSession,
    candidate_id: int,
    skill_name: str,
) -> Candidate:
    candidate = await get_candidate(db, candidate_id)
    if candidate is None:
        raise ValueError(f"Candidate with id {candidate_id} not found")

    skill_name = skill_name.strip()
    if not skill_name:
        raise ValueError("Skill name must not be empty")

    skill = await _get_or_create_skill(db, skill_name)

    existing_skill_ids = {s.id for s in candidate.skills}
    if skill.id not in existing_skill_ids:
        candidate.skills.append(skill)
        await db.flush()
        await db.refresh(candidate)
        logger.info("Added skill '%s' to candidate id=%s", skill_name, candidate_id)
    else:
        logger.info("Skill '%s' already exists on candidate id=%s", skill_name, candidate_id)

    return candidate


async def remove_skill(
    db: AsyncSession,
    candidate_id: int,
    skill_name: str,
) -> Candidate:
    candidate = await get_candidate(db, candidate_id)
    if candidate is None:
        raise ValueError(f"Candidate with id {candidate_id} not found")

    skill_name = skill_name.strip()
    if not skill_name:
        raise ValueError("Skill name must not be empty")

    skill_to_remove = None
    for skill in candidate.skills:
        if skill.name.lower() == skill_name.lower():
            skill_to_remove = skill
            break

    if skill_to_remove is not None:
        candidate.skills.remove(skill_to_remove)
        await db.flush()
        await db.refresh(candidate)
        logger.info("Removed skill '%s' from candidate id=%s", skill_name, candidate_id)
    else:
        logger.info("Skill '%s' not found on candidate id=%s", skill_name, candidate_id)

    return candidate


async def get_all_skills(db: AsyncSession) -> list[Skill]:
    result = await db.execute(select(Skill).order_by(Skill.name))
    return list(result.scalars().all())


async def _resolve_skills(
    db: AsyncSession,
    skill_names: list[str],
) -> list[Skill]:
    skills = []
    seen = set()
    for name in skill_names:
        name = name.strip()
        if not name:
            continue
        lower_name = name.lower()
        if lower_name in seen:
            continue
        seen.add(lower_name)
        skill = await _get_or_create_skill(db, name)
        skills.append(skill)
    return skills


async def _get_or_create_skill(
    db: AsyncSession,
    skill_name: str,
) -> Skill:
    result = await db.execute(
        select(Skill).where(func.lower(Skill.name) == skill_name.strip().lower())
    )
    skill = result.scalars().first()
    if skill is None:
        skill = Skill(name=skill_name.strip())
        db.add(skill)
        await db.flush()
        await db.refresh(skill)
        logger.info("Created new skill '%s' id=%s", skill.name, skill.id)
    return skill