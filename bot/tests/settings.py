import logging

from pydantic import (
    Field,
    SecretStr,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

from bot.utils.config_loader import load_env_file

logger = logging.getLogger(__name__)
env_path = load_env_file()

class Settings(BaseSettings):
    SESSION: str = Field("name")
    POSTGRES_SCHEMA: str = Field("ranczo")

    SPECIALIZED_TABLE: str = Field(...)

    TEST_POSTGRES_DB: str = Field(...)
    TEST_POSTGRES_USER: str = Field(...)
    TEST_POSTGRES_PASSWORD: SecretStr = Field(...)
    TEST_POSTGRES_HOST: str = Field(...)
    TEST_POSTGRES_PORT: str = Field(...)

    TEST_ADMINS: str = Field(...)
    TEST_PASSWORD: SecretStr = Field(...)

    REST_API_HOST: str = Field(...)
    REST_API_PORT: int = Field(...)

    model_config = SettingsConfigDict(
        env_file=str(env_path),
        env_prefix="",
        extra="ignore",
    )

settings = Settings()
