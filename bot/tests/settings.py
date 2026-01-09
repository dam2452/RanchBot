import logging

from pydantic import (
    Field,
    SecretStr,
)
from pydantic_settings import BaseSettings

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

    REST_API_HOST: str = Field("192.168.1.210")
    REST_API_PORT: int = Field(8199)

    class Config:
        env_file = str(env_path)
        env_prefix = ""
        extra = "ignore"

logger.info(f"Loading settings from {Settings.Config.env_file}")
settings = Settings()
