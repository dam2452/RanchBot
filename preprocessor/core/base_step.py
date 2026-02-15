from __future__ import annotations

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
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
)

from pydantic import BaseModel

from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import OutputDescriptor
from preprocessor.core.temp_files import StepTempFile

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

    def get_output_descriptors(self) -> List[OutputDescriptor]:
        """
        Override in subclass to define step outputs.
        Used for automatic output validation and path resolution.
        """
        return []

    def _resolve_output_path(
        self,
        descriptor_index: int,
        context: ExecutionContext,
        context_vars: Optional[Dict[str, str]] = None,
    ) -> Path:
        """
        Resolve output path from OutputDescriptor at given index.
        Eliminates hardcoded subdirectories - uses descriptor definition.
        """
        descriptors = self.get_output_descriptors()
        if not descriptors or descriptor_index >= len(descriptors):
            raise ValueError(
                f'Step {self.name} has no output descriptor at index {descriptor_index}',
            )

        descriptor = descriptors[descriptor_index]
        return descriptor.resolve_path(context.base_output_dir, context_vars)

    def should_skip_execution(
        self, episode_id: str, context: ExecutionContext, context_vars: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Default caching logic - checks state manager and output validity.
        Subclasses can call this at the start of execute() to skip if already done.
        """
        if context.force_rerun:
            return False

        if not context.is_step_completed(self.name, episode_id):
            return False

        descriptors = self.get_output_descriptors()
        if not descriptors:
            return True

        for descriptor in descriptors:
            result = descriptor.validate(context.base_output_dir, context_vars)
            if not result.is_valid:
                context.logger.warning(
                    f'{episode_id} - output invalid: {result.message}',
                )
                return False

        return True

    @abstractmethod
    def execute(self, input_data: InputT, context: ExecutionContext) -> OutputT:
        pass

    @property
    def supports_batch_processing(self) -> bool:
        return False

    def setup_resources(self, context: ExecutionContext) -> None:
        pass

    def execute_batch(
        self, input_data: List[InputT], context: ExecutionContext,
    ) -> List[OutputT]:
        return [self.execute(item, context) for item in input_data]

    def teardown_resources(self, context: ExecutionContext) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def _check_cache_validity(
        self,
        output_path: Path,
        context: ExecutionContext,
        episode_id: str,
        cache_description: str,
    ) -> bool:
        if output_path.exists() and not context.force_rerun:
            if context.is_step_completed(self.name, episode_id):
                context.logger.info(f'Skipping {episode_id} ({cache_description})')
                return True
        return False

    def _check_output_validity(
        self,
        output_descriptor: OutputDescriptor,
        context: ExecutionContext,
        episode_id: str,
        context_vars: Optional[Dict[str, str]] = None,
    ) -> bool:
        if context.force_rerun:
            return False

        if not context.is_step_completed(self.name, episode_id):
            return False

        validation_result = output_descriptor.validate(
            context.base_output_dir, context_vars,
        )

        if validation_result.is_valid:
            context.logger.info(
                f'Skipping {episode_id} - output valid '
                f'({validation_result.file_count} files, '
                f'{validation_result.total_size_bytes} bytes)',
            )
            return True

        context.logger.warning(
            f'Output invalid for {episode_id}: {validation_result.message}',
        )
        return False


    @staticmethod
    def _execute_with_threadpool(
        input_data: List[InputT],
        context: ExecutionContext,
        max_workers: int,
        executor_fn: Callable[[InputT, ExecutionContext], OutputT],
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
        context: ExecutionContext,
        executor_fn: Callable[[InputT, ExecutionContext], OutputT],
    ) -> List[OutputT]:
        context.logger.info(
            f"Batch processing {len(input_data)} episodes sequentially",
        )

        results = []
        for artifact in input_data:
            result = executor_fn(artifact, context)
            results.append(result)

        return results

    @staticmethod
    def _atomic_write(
        final_path: Path,
        write_func: Callable[[Path], None],
        temp_suffix: str = '.tmp',
    ) -> None:
        with StepTempFile(final_path, temp_suffix) as temp_path:
            write_func(temp_path)
