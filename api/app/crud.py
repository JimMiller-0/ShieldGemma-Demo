import json
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from api.app import models


DEFAULT_PREDEFINED_POLICY_CONFIG = {
    "dangerous_content": True,
    "harassment": True,
    "hate_speech": True,
    "sexually_explicit": True,
}


# ─── Safety Policy CRUD ──────────────────────────────────────────────

async def create_safety_policy(
    db: AsyncSession,
    name: str,
    description: str | None,
    policy_content: str,
    is_default: bool = False,
    predefined_policy_config: dict | None = None,
) -> models.SafetyPolicy:
    if is_default:
        subquery = select(models.SafetyPolicy.id).where(
            models.SafetyPolicy.is_default == True
        ).scalar_subquery()
        await db.execute(
            models.SafetyPolicy.__table__.update()
            .where(models.SafetyPolicy.id == subquery)
            .values(is_default=False)
        )

    db_policy = models.SafetyPolicy(
        name=name,
        description=description,
        policy_content=policy_content,
        is_default=is_default,
        predefined_policy_config=predefined_policy_config or DEFAULT_PREDEFINED_POLICY_CONFIG,
    )
    db.add(db_policy)
    await db.commit()
    await db.refresh(db_policy)
    return db_policy


async def get_safety_policy(db: AsyncSession, policy_id: UUID) -> models.SafetyPolicy | None:
    result = await db.execute(
        select(models.SafetyPolicy).where(models.SafetyPolicy.id == policy_id)
    )
    return result.scalars().first()


async def get_safety_policy_by_name(db: AsyncSession, name: str) -> models.SafetyPolicy | None:
    result = await db.execute(
        select(models.SafetyPolicy).where(models.SafetyPolicy.name == name)
    )
    return result.scalars().first()


async def get_default_safety_policy(db: AsyncSession) -> models.SafetyPolicy | None:
    result = await db.execute(
        select(models.SafetyPolicy).where(models.SafetyPolicy.is_default == True)
    )
    return result.scalars().first()


async def list_safety_policies(
    db: AsyncSession,
    search: str = "",
    skip: int = 0,
    limit: int = 100,
) -> list[models.SafetyPolicy]:
    query = select(models.SafetyPolicy)
    if search:
        query = query.where(models.SafetyPolicy.name.ilike(f"%{search}%"))
    query = query.order_by(
        desc(models.SafetyPolicy.is_default),
        desc(models.SafetyPolicy.updated_at),
    ).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_safety_policies(db: AsyncSession, search: str = "") -> int:
    query = select(func.count()).select_from(models.SafetyPolicy)
    if search:
        query = query.where(models.SafetyPolicy.name.ilike(f"%{search}%"))
    result = await db.execute(query)
    return result.scalar_one()


async def update_safety_policy(
    db: AsyncSession,
    policy_id: UUID,
    name: str | None = None,
    description: str | None = None,
    policy_content: str | None = None,
    is_default: bool | None = None,
    predefined_policy_config: dict | None = None,
) -> models.SafetyPolicy | None:
    if is_default is True:
        subquery = select(models.SafetyPolicy.id).where(
            models.SafetyPolicy.is_default == True,
            models.SafetyPolicy.id != policy_id,
        ).scalar_subquery()
        await db.execute(
            models.SafetyPolicy.__table__.update()
            .where(models.SafetyPolicy.id == subquery)
            .values(is_default=False)
        )

    result = await db.execute(
        select(models.SafetyPolicy).where(models.SafetyPolicy.id == policy_id)
    )
    db_policy = result.scalar_one_or_none()
    if not db_policy:
        return None

    if name is not None:
        db_policy.name = name
    if description is not None:
        db_policy.description = description
    if policy_content is not None:
        db_policy.policy_content = policy_content
    if is_default is not None:
        db_policy.is_default = is_default
    if predefined_policy_config is not None:
        db_policy.predefined_policy_config = predefined_policy_config

    await db.commit()
    await db.refresh(db_policy)
    return db_policy


async def delete_safety_policy(db: AsyncSession, policy_id: UUID) -> bool:
    result = await db.execute(
        select(models.SafetyPolicy).where(models.SafetyPolicy.id == policy_id)
    )
    db_policy = result.scalar_one_or_none()
    if not db_policy:
        return False
    await db.delete(db_policy)
    await db.commit()
    return True


async def load_seed_policies(db: AsyncSession) -> int:
    seed_file = Path(__file__).parent / "data" / "seed_policies.json"
    if not seed_file.exists():
        logger.warning("Seed policies file not found at {}", seed_file)
        return 0

    with open(seed_file, "r", encoding="utf-8") as f:
        policies = json.load(f)

    loaded = 0
    for policy_data in policies:
        existing = await get_safety_policy_by_name(db, policy_data["name"])
        if existing:
            logger.info("Seed policy '{}' already exists, skipping", policy_data["name"])
            continue
        db_policy = models.SafetyPolicy(
            name=policy_data["name"],
            description=policy_data.get("description", ""),
            policy_content=policy_data["policy_content"],
            is_default=policy_data.get("is_default", False),
            predefined_policy_config=policy_data.get("predefined_policy_config", DEFAULT_PREDEFINED_POLICY_CONFIG),
        )
        db.add(db_policy)
        await db.commit()
        await db.refresh(db_policy)
        loaded += 1
        logger.info("Seeded policy '{}'", policy_data["name"])

    return loaded


# ─── Analysis Log CRUD ────────────────────────────────────────────────

async def create_analysis_log(
    db: AsyncSession,
    text_input: str,
    policy_id: UUID | None,
    policy_name: str | None,
    is_safe: bool,
    safety_categories: list[dict],
    model_used: str,
    max_score: float,
    inference_time_seconds: float,
) -> models.AnalysisLog:
    log = models.AnalysisLog(
        text_input=text_input,
        policy_id=policy_id,
        policy_name=policy_name,
        is_safe=is_safe,
        safety_categories=safety_categories,
        model_used=model_used,
        max_score=max_score,
        inference_time_seconds=inference_time_seconds,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def list_analysis_logs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
) -> list[models.AnalysisLog]:
    result = await db.execute(
        select(models.AnalysisLog)
        .order_by(desc(models.AnalysisLog.created_at))
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_analysis_logs(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).select_from(models.AnalysisLog)
    )
    return result.scalar_one()
