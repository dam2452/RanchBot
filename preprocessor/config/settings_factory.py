from typing import Optional

from preprocessor.config.config import Settings


class SettingsFactory:
    __instance: Optional[Settings] = None

    @classmethod
    def get_settings(cls) -> Settings:
        if cls.__instance is None:
            cls.__instance = Settings._from_env()
        return cls.__instance

    @classmethod
    def reset(cls, new_settings: Optional[Settings] = None) -> None:
        cls.__instance = new_settings
