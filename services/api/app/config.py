from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# services/api/app/config.py -> repo root is three levels up. Resolved
# absolutely so `.env` at the repo root is found regardless of the process's
# working directory (uvicorn run from services/api, Docker, or elsewhere).
_REPO_ROOT_ENV = Path(__file__).resolve().parent.parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(_REPO_ROOT_ENV, ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://medirag:medirag@localhost:5432/medirag"

    llm_provider: str = "mock"
    ocr_provider: str = "mock"
    maps_provider: str = "mock"
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    auth_secret: str = "change-me-in-production"
    auth_token_ttl_minutes: int = 60

    storage_dir: str = "./uploads"

    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    default_region: str = "US"


@lru_cache
def get_settings() -> Settings:
    return Settings()
