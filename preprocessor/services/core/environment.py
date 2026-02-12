import os
from typing import Optional


class Environment:

    _is_docker_cached: Optional[bool] = None

    @staticmethod
    def is_docker() -> bool:
        if Environment._is_docker_cached is None:
            Environment._is_docker_cached = (
                os.getenv('DOCKER_CONTAINER', 'false').lower() == 'true'
            )
        return Environment._is_docker_cached

    @staticmethod
    def reset_cache() -> None:
        Environment._is_docker_cached = None
