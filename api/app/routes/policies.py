from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from typing import Annotated

from api.app.database import get_db_session
from api.app.schemas import (
    SafetyPolicyCreate,
    SafetyPolicyUpdate,
    SafetyPolicyResponse,
    SafetyPolicyListResponse,
)
from api.app import crud

router = APIRouter(
    prefix="/api/v1/safety/policies",
    tags=["safety-policies"],
)


@router.post("/", response_model=SafetyPolicyResponse, status_code=201)
async def create_policy(
    policy: SafetyPolicyCreate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Create a new safety policy."""
    existing = await crud.get_safety_policy_by_name(db, policy.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Policy '{policy.name}' already exists.")
    try:
        return await crud.create_safety_policy(
            db=db,
            name=policy.name,
            description=policy.description,
            policy_content=policy.policy_content,
            is_default=policy.is_default,
            predefined_policy_config=policy.predefined_policy_config.model_dump(),
        )
    except Exception as e:
        logger.opt(exception=True).error("Error creating policy: {}", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=SafetyPolicyListResponse)
async def list_policies(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    search: Annotated[str, Query(description="Filter by name")] = "",
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
):
    """List safety policies with search and pagination."""
    policies = await crud.list_safety_policies(db, search=search, skip=skip, limit=limit)
    total = await crud.count_safety_policies(db, search=search)
    return SafetyPolicyListResponse(policies=policies, total=total)


@router.get("/check_name/{policy_name}")
async def check_name(
    policy_name: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Check if a policy name already exists."""
    existing = await crud.get_safety_policy_by_name(db, policy_name)
    return {"exists": existing is not None}


@router.get("/default", response_model=SafetyPolicyResponse)
async def get_default_policy(
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Get the default safety policy."""
    policy = await crud.get_default_safety_policy(db)
    if not policy:
        raise HTTPException(status_code=404, detail="No default policy found")
    return policy


@router.get("/{policy_id}", response_model=SafetyPolicyResponse)
async def get_policy(
    policy_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Get a safety policy by ID."""
    policy = await crud.get_safety_policy(db, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.patch("/{policy_id}", response_model=SafetyPolicyResponse)
async def update_policy(
    policy_id: UUID,
    policy_update: SafetyPolicyUpdate,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Update a safety policy."""
    try:
        updated = await crud.update_safety_policy(
            db=db,
            policy_id=policy_id,
            name=policy_update.name,
            description=policy_update.description,
            policy_content=policy_update.policy_content,
            is_default=policy_update.is_default,
            predefined_policy_config=(
                policy_update.predefined_policy_config.model_dump()
                if policy_update.predefined_policy_config
                else None
            ),
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Policy not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.opt(exception=True).error("Error updating policy: {}", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Delete a safety policy."""
    success = await crud.delete_safety_policy(db, policy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Policy not found")
