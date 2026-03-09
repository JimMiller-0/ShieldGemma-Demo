import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from model_service.app.config import settings
from model_service.app.routes import router

logger.remove()
logger.add(
    sys.stderr,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
)


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Model service starting — loading {}...", settings.model_id)

    application.state.safety_engine = None
    model_path = settings.model_path

    if not model_path.exists():
        logger.error(
            "Model not found at {}. Run `python -m model_service.scripts.download_model` first.",
            model_path,
        )
    else:
        try:
            from model_service.app.engine import LocalSafetyEngine
            engine = LocalSafetyEngine(
                model_id=settings.model_id,
                model_path=str(model_path),
            )
            application.state.safety_engine = engine
            logger.info("Model service ready — {} loaded", settings.model_id)
        except Exception:
            logger.exception("Failed to load model {}", settings.model_id)

    yield

    logger.info("Model service shutting down")
    application.state.safety_engine = None


app = FastAPI(
    title="ShieldGemma Model Service",
    description="Local inference service for ShieldGemma safety classification",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)
