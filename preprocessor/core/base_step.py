from abc import (
    ABC,
    abstractmethod,
)
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    List,
    TypeVar,
)

from pydantic import BaseModel

if TYPE_CHECKING:
    from preprocessor.core.context import ExecutionContext

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")
ConfigT = TypeVar("ConfigT", bound=BaseModel)


class PipelineStep(ABC, Generic[InputT, OutputT, ConfigT]):
    def __init__(self, config: ConfigT) -> None:
        self.__config: ConfigT = config

    @property
    def config(self) -> ConfigT:
        return self.__config

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def is_global(self) -> bool:
        return False

    @abstractmethod
    def execute(self, input_data: InputT, context: "ExecutionContext") -> OutputT:
        pass

    @property
    def supports_batch_processing(self) -> bool:
        return False

    def setup_resources(self, context: "ExecutionContext") -> None:
        pass

    def execute_batch(
        self, input_data: List[InputT], context: "ExecutionContext",
    ) -> List[OutputT]:
        return [self.execute(item, context) for item in input_data]

    def teardown_resources(self, context: "ExecutionContext") -> None:
        pass

    def cleanup(self) -> None:
        pass

    def _check_cache_validity(
        self,
        output_path: Path,
        context: "ExecutionContext",
        episode_id: str,
        cache_description: str,
    ) -> bool:
        if output_path.exists() and not context.force_rerun:
            if context.is_step_completed(self.name, episode_id):
                context.logger.info(f'Skipping {episode_id} ({cache_description})')
                return True
        return False

    @staticmethod
    def _execute_with_threadpool(
        input_data: List[InputT],
        context: "ExecutionContext",
        max_workers: int,
        executor_fn: Callable[[InputT, "ExecutionContext"], OutputT],
    ) -> List[OutputT]:
        context.logger.info(
            f"Batch processing {len(input_data)} episodes with {max_workers} workers",
        )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(executor_fn, artifact, context): artifact
                for artifact in input_data
            }

            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

            return results

    @staticmethod
    def _execute_sequential(
        input_data: List[InputT],
        context: "ExecutionContext",
        executor_fn: Callable[[InputT, "ExecutionContext"], OutputT],
    ) -> List[OutputT]:
        context.logger.info(
            f"Batch processing {len(input_data)} episodes sequentially",
        )

        results = []
        for artifact in input_data:
            result = executor_fn(artifact, context)
            results.append(result)

        return results
