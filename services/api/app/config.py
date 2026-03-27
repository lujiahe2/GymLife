from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Always resolve `services/api/.env` (not cwd), so uvicorn works from any directory.
_API_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _API_ROOT / ".env"


class Settings(BaseSettings):
    """Load from process env and `services/api/.env`."""

    jwt_secret: str = "dev-only-set-JWT_SECRET-in-production"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    # Optional: Ollama → http://127.0.0.1:11434/v1 | Azure / other OpenAI-compatible endpoints
    openai_base_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
