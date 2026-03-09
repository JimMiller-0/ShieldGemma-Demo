import time

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from model_service.app.config import settings
from model_service.app.models import SafetyRequest, SafetyResponse, SafetyCategoryResult, HealthResponse

router = APIRouter()


@router.post("/v1/inference/safety", response_model=SafetyResponse)
async def safety_inference(request: SafetyRequest, req: Request) -> SafetyResponse:
    engine = req.app.state.safety_engine
    if engine is None:
        raise HTTPException(status_code=503, detail="No safety engine available. Model may still be loading.")

    for p in request.prompts:
        if len(p.text) > settings.max_payload_size:
            raise HTTPException(
                status_code=400,
                detail=f"Prompt text length {len(p.text)} exceeds limit of {settings.max_payload_size}.",
            )

    prompts = [{"category": p.category, "text": p.text} for p in request.prompts]

    start = time.perf_counter()
    try:
        raw_results = await engine.analyze_batch(prompts, max_new_tokens=request.max_new_tokens)
    except Exception as e:
        logger.exception("Safety inference failed for model {}", request.model_id)
        raise HTTPException(status_code=500, detail=f"Inference error: {e}")

    elapsed_ms = (time.perf_counter() - start) * 1000

    results = [
        SafetyCategoryResult(
            category=r["category"],
            yes_prob=r["yes_prob"],
            no_prob=r["no_prob"],
            raw_text=r["raw_text"],
        )
        for r in raw_results
    ]

    return SafetyResponse(
        model_id=request.model_id,
        results=results,
        inference_time_ms=round(elapsed_ms, 2),
    )


@router.get("/v1/health", response_model=HealthResponse)
async def health(req: Request) -> HealthResponse:
    engine = req.app.state.safety_engine
    return HealthResponse(
        status="healthy" if engine is not None else "loading",
        model_loaded=engine.model_id if engine else None,
        device=settings.compute_device,
    )
