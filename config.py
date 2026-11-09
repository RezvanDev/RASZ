from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    BOT_TOKEN: str = ""
    ADMIN_IDS: Union[List[int], str] = []

    # LLM Settings (OpenAI / OpenRouter / DeepSeek / etc.)
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"

    # Database
    DB_URL: str = "sqlite+aiosqlite:///data/finance.db"

    # Regional & Scheduling (Uzbekistan / Tashkent)
    DEFAULT_CURRENCY: str = "UZS"
    DAILY_REPORT_TIME: str = "09:00"
    TIMEZONE: str = "Asia/Tashkent"

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Union[str, List[int]]) -> List[int]:
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip().isdigit()]
        if isinstance(v, list):
            return [int(x) for x in v]
        return []

settings = Settings()

