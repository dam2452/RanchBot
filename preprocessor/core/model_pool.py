import threading
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
)

from preprocessor.services.core.logging import ErrorHandlingLogger


class ModelPool:
    def __init__(self) -> None:
        self._models: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._ref_counts: Dict[str, int] = {}

    def get_or_load(
        self,
        model_id: str,
        loader: Callable[[], Any],
        logger: Optional[ErrorHandlingLogger] = None,
    ) -> Any:
        with self._lock:
            if model_id not in self._models:
                if logger:
                    logger.info(f"Loading model to pool: {model_id}")
                self._models[model_id] = loader()
                self._ref_counts[model_id] = 0

            self._ref_counts[model_id] += 1
            return self._models[model_id]

    def release(self, model_id: str, logger: Optional[ErrorHandlingLogger] = None) -> None:
        with self._lock:
            if model_id in self._ref_counts:
                self._ref_counts[model_id] -= 1
                if self._ref_counts[model_id] <= 0:
                    if logger:
                        logger.info(f"Removing model from pool: {model_id}")
                    del self._models[model_id]
                    del self._ref_counts[model_id]

    def cleanup_all(self, logger: Optional[ErrorHandlingLogger] = None) -> None:
        with self._lock:
            if logger and self._models:
                logger.info(f"Cleaning up {len(self._models)} models from pool")
            self._models.clear()
            self._ref_counts.clear()
