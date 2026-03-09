from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from typing import Annotated

from api.app.database import get_db_session
from api.app.schemas import (
    SafetyAnalysisRequest,
    SafetyAnalysisResponse,
    AnalysisLogListResponse,
)
from api.app.service import analyze_safety
from api.app import crud

router = APIRouter(
    prefix="/api/v1/safety",
    tags=["safety-moderation"],
)


@router.post("/analyze", response_model=SafetyAnalysisResponse)
async def analyze(
    request: SafetyAnalysisRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Analyze text for safety violations using ShieldGemma and the selected policy."""
    try:
        return await analyze_safety(request, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.opt(exception=True).error("Safety analysis failed: {}", e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.get("/models")
async def list_models():
    """List available safety models."""
    return {
        "available_models": ["google/shieldgemma-2b"],
        "default_model": "google/shieldgemma-2b",
    }


@router.get("/logs", response_model=AnalysisLogListResponse)
async def list_logs(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """List recent analysis logs."""
    logs = await crud.list_analysis_logs(db, skip=skip, limit=limit)
    total = await crud.count_analysis_logs(db)
    return AnalysisLogListResponse(logs=logs, total=total)
