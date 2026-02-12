from typing import Optional

from preprocessor.config.config import Settings


class SettingsFactory:

    _instance: Optional[Settings] = None

    @staticmethod
    def get_settings() -> Settings:
        if SettingsFactory._instance is None:
            SettingsFactory._instance = Settings._from_env()
        return SettingsFactory._instance

    @staticmethod
    def reset(new_settings: Optional[Settings] = None) -> None:
        SettingsFactory._instance = new_settings
