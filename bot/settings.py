import logging
from typing import Optional

from pydantic import (
    Field,
    SecretStr,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

from bot.utils.config_loader import load_env_file

logger = logging.getLogger(__name__)
env_path = load_env_file()

class Settings(BaseSettings):
    FILE_SIZE_LIMIT_MB: int = Field(50)
    TELEGRAM_BOT_TOKEN: Optional[SecretStr] = None
    BOT_USERNAME: str = Field(...)
    DEFAULT_ADMIN: str = Field(...)
    INLINE_CACHE_CHANNEL_ID: Optional[int] = Field(...)
    DEFAULT_RESOLUTION_KEY: str = Field("1080p")

    POSTGRES_USER: str = Field(...)
    POSTGRES_PASSWORD: SecretStr = Field(...)
    POSTGRES_HOST: str = Field(...)
    POSTGRES_PORT: int = Field(...)
    POSTGRES_DB: str = Field(...)
    POSTGRES_SCHEMA: str = Field(...)

    SPECIALIZED_TABLE: str = Field(...)

    ES_HOST: str = Field(...)
    ES_USER: str = Field(...)
    ES_PASS: SecretStr = Field(...)
    ES_TRANSCRIPTION_INDEX: str = Field(...)

    VIDEO_DATA_DIR: str = Field(...)

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
    ENVIRONMENT: str = Field("production")

    ENABLE_TELEGRAM: bool = Field(False)
    ENABLE_REST: bool = Field(False)

    JWT_SECRET_KEY: Optional[SecretStr] = Field("tests")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30
    JWT_ISSUER: str = Field("RanchBot")
    JWT_AUDIENCE: str = Field("CLI")
    MAX_ACTIVE_TOKENS: int = Field(10)

    REST_API_HOST: str = Field("0.0.0.0")
    REST_API_PORT: int = Field(8000)
    REST_API_APP_PATH: str = Field("bot.platforms.rest_runner:app")
    DISABLE_RATE_LIMITING: bool = Field(False)

    @model_validator(mode='after')
    def check_conditional_settings(self) -> 'Settings':
        if not self.ENABLE_TELEGRAM and not self.ENABLE_REST:
            raise ValueError(
                "At least one platform must be enabled. Set ENABLE_TELEGRAM=true or ENABLE_REST=true",
            )

        if self.ENABLE_TELEGRAM and not self.TELEGRAM_BOT_TOKEN:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is required when ENABLE_TELEGRAM=true",
            )

        if self.ENABLE_REST and not self.JWT_SECRET_KEY:
            raise ValueError(
                "JWT_SECRET_KEY is required when ENABLE_REST=true",
            )

        return self

    model_config = SettingsConfigDict(
        env_file=str(env_path),
        env_prefix="",
        extra="ignore",
    )

settings = Settings()
