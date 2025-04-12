import logging

from pydantic import Field
from pydantic_settings import BaseSettings

from bot.utils.config_loader import load_env_file

logger = logging.getLogger(__name__)
env_path = load_env_file()

class Settings(BaseSettings):
    TELEGRAM_FILE_SIZE_LIMIT_MB: int = Field(50)
    TELEGRAM_BOT_TOKEN: str = Field(...)
    BOT_USERNAME: str = Field(...)
    DEFAULT_ADMIN: str = Field(...)
    DEFAULT_RESOLUTION_KEY: str = Field("1080p")

    POSTGRES_USER: str = Field(...)
    POSTGRES_PASSWORD: str = Field(...)
    POSTGRES_HOST: str = Field(...)
    POSTGRES_PORT: int = Field(...)
    POSTGRES_DB: str = Field(...)
    POSTGRES_SCHEMA: str = Field(...)

    SPECIALIZED_TABLE: str = Field(...)

    ES_HOST: str = Field(...)
    ES_USER: str = Field(...)
    ES_PASS: str = Field(...)
    ES_TRANSCRIPTION_INDEX: str = Field(...)

    EXTEND_BEFORE: float = Field(5)
    EXTEND_AFTER: float = Field(5)

    EXTEND_BEFORE_COMPILE: float = Field(1)
    EXTEND_AFTER_COMPILE: float = Field(1)

    MESSAGE_LIMIT: int = Field(5)
    LIMIT_DURATION: int = Field(30)
    MAX_CLIPS_PER_COMPILATION: int = Field(30)
    MAX_ADJUSTMENT_DURATION: int = Field(20)
    MAX_SEARCH_QUERY_LENGTH: int = Field(200)
    MAX_CLIP_DURATION: int = Field(60)
    MAX_CLIP_NAME_LENGTH: int = Field(40)
    MAX_REPORT_LENGTH: int = Field(1000)
    MAX_CLIPS_PER_USER: int = Field(100)

    LOG_LEVEL: str = Field("INFO")

    PLATFORM: str = Field("telegram")
    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30
    JWT_ISSUER: str = Field("RanchBot")
    JWT_AUDIENCE: str = Field("CLI")
    MAX_ACTIVE_TOKENS: int = Field(10)

    REST_API_HOST: str = Field("0.0.0.0")
    REST_API_PORT: int = Field(8000)
    REST_API_APP_PATH: str = Field("bot.platforms.rest_runner:app")


    class Config:
        env_file = str(env_path)
        env_prefix = ""
        extra = "ignore"

settings = Settings()
