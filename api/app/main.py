import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from api.app.config import settings
from api.app.database import async_engine, Base, AsyncSessionLocal
from api.app.routes import safety, policies
from api.app import crud
from api.app import models as _models  # noqa: F401 — register ORM models

logger.remove()
logger.add(
    sys.stderr,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("API service starting...")

    # Create tables (for development; in production use alembic migrate)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")

    # Seed default policies
    async with AsyncSessionLocal() as db:
        try:
            loaded = await crud.load_seed_policies(db)
            logger.info("Seed policies loaded: {}", loaded)
        except Exception as e:
            logger.warning("Failed to seed policies: {}", e)

    yield

    logger.info("API service shutting down")
    await async_engine.dispose()


app = FastAPI(
    title="ShieldGemma Safety API",
    description="Open-source safety moderation API powered by ShieldGemma",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(safety.router)
app.include_router(policies.router)


@app.get("/health")
async def health():
    return {"status": "healthy"}
