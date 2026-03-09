import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://demo:demo@localhost:5432/shieldgemma_demo",
        )
    )
    model_service_url: str = field(
        default_factory=lambda: os.environ.get("MODEL_SERVICE_URL", "http://localhost:8080")
    )
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))
    port: int = field(default_factory=lambda: int(os.environ.get("PORT", "8000")))

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("postgresql+asyncpg", "postgresql")


settings = Settings()
