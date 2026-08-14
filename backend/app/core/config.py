from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_NAME: str = "PharmaResolve AI"
    APP_VERSION: str = "1.1.0"
    DEBUG: bool = True

    DATABASE_URL: str
    API_V1_PREFIX: str = "/api/v1"
    # Comma-separated browser origins permitted to call the API. Keep this
    # configurable because Vercel production and preview URLs can differ.
    CORS_ORIGINS: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "https://pharma-resolve-ai.vercel.app"
    )
    CORS_ORIGIN_REGEX: str | None = (
        r"https://pharma-resolve-ai(?:-[a-z0-9-]+)?\.vercel\.app"
    )

    GROQ_API_KEY: SecretStr | None = None
    GROQ_MODEL: str = "gemma2-9b-it"
    GROQ_FALLBACK_MODEL: str | None = "llama-3.3-70b-versatile"

    GROQ_TEMPERATURE: float = Field(default=0.1, ge=0, le=2)
    GROQ_MAX_COMPLETION_TOKENS: int = Field(
        default=2500,
        ge=100,
        le=10000,
    )
    GROQ_TIMEOUT_SECONDS: float = Field(
        default=45,
        ge=5,
        le=120,
    )
    UPLOAD_DIRECTORY: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = Field(default=10, ge=1, le=50)
    MAX_PDF_PAGES: int = Field(default=50, ge=1, le=200)
    MIN_EXTRACTED_TEXT_LENGTH: int = Field(
        default=30,
        ge=1,
        le=1000,
    )

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
