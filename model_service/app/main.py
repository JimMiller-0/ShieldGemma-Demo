import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

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


async def _load_model_async(application: FastAPI, model_path: Path):
    if not model_path.exists():
        auto_download = os.environ.get("AUTO_DOWNLOAD_MODEL", "false").lower() in ("1", "true", "yes", "on")
        has_token = bool(os.environ.get("HF_TOKEN"))
        if auto_download or has_token:
            try:
                logger.info("Model not found at {}. Starting automatic download...", model_path)
                from model_service.scripts.download_model import download_model
                await asyncio.to_thread(download_model, model_id=settings.model_id, model_dir=settings.model_dir)
            except Exception:
                logger.exception("Failed to automatically download model {}", settings.model_id)

    if not model_path.exists():
        logger.error(
            "Model not found at {}. Provide a GCS volume mount, set AUTO_DOWNLOAD_MODEL=true / HF_TOKEN, or run download_model.",
            model_path,
        )
        return

    try:
        from model_service.app.engine import get_safety_engine
        engine = await asyncio.to_thread(
            get_safety_engine,
            model_id=settings.model_id,
            model_path=str(model_path),
        )
        application.state.safety_engine = engine
        logger.info("Model service ready — {} loaded ({})", settings.model_id, engine.__class__.__name__)
    except Exception:
        logger.exception("Failed to load model {}", settings.model_id)


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Model service starting — starting HTTP server and background model load...")
    application.state.safety_engine = None
    model_path = settings.model_path

    load_task = asyncio.create_task(_load_model_async(application, model_path))

    yield

    logger.info("Model service shutting down")
    if not load_task.done():
        load_task.cancel()
    if application.state.safety_engine is not None and hasattr(application.state.safety_engine, "close"):
        try:
            await application.state.safety_engine.close()
        except Exception:
            logger.exception("Error during safety engine shutdown")
    application.state.safety_engine = None



app = FastAPI(
    title="ShieldGemma Model Service",
    description="Local inference service for ShieldGemma safety classification",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)
