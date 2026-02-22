import os
from typing import Optional


class Environment:
    __is_docker_cached: Optional[bool] = None

    @staticmethod
    def is_docker() -> bool:
        if Environment.__is_docker_cached is None:
            Environment.__is_docker_cached = (
                os.getenv('DOCKER_CONTAINER', 'false').lower() == 'true'
            )
        return Environment.__is_docker_cached

    @staticmethod
    def reset_cache() -> None:
        Environment.__is_docker_cached = None
