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
import re
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
    def name(self) -> str:
        class_name = self.__class__.__name__
        if class_name.endswith('Step'):
            class_name = class_name[:-4]

        snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
        return snake_case

    @property
    def config(self) -> ConfigT:
        return self.__config

    @property
    def is_global(self) -> bool:
        return False

    @property
    def uses_caching(self) -> bool:
        return True

    @property
    def supports_batch_processing(self) -> bool:
        return False

    def execute(self, input_data: InputT, context: ExecutionContext) -> OutputT:
        if not self.uses_caching:
            return self._process(input_data, context)

        return self.__execute_managed_flow(input_data, context)

    def execute_batch(
        self, input_data: List[InputT], context: ExecutionContext,
    ) -> List[OutputT]:
        return [self.execute(item, context) for item in input_data]

    def should_skip_execution(
        self,
        episode_id: str,
        context: ExecutionContext,
        context_vars: Optional[Dict[str, str]] = None,
    ) -> bool:
        if context.force_rerun:
            return False

        if not context.is_step_completed(self.name, episode_id):
            return False

        return self.__validate_all_descriptors(context, context_vars, episode_id)

    def setup_resources(self, context: ExecutionContext) -> None:
        pass

    def teardown_resources(self, context: ExecutionContext) -> None:
        pass

    def cleanup(self) -> None:
        pass

    @abstractmethod
    def _process(self, input_data: InputT, context: ExecutionContext) -> OutputT:
        raise NotImplementedError(
            f'{self.__class__.__name__} must implement _process()',
        )

    def _get_output_descriptors(self) -> List[OutputDescriptor]:
        return []

    def _get_cache_path(self, input_data: InputT, context: ExecutionContext) -> Path:
        raise NotImplementedError(
            f'{self.__class__.__name__} must implement _get_cache_path() when caching is enabled',
        )

    def _load_from_cache(
        self, cache_path: Path, input_data: InputT, context: ExecutionContext,
    ) -> OutputT:
        raise NotImplementedError(
            f'{self.__class__.__name__} must implement _load_from_cache() when caching is enabled',
        )

    def _resolve_output_path(
        self,
        descriptor_index: int,
        context: ExecutionContext,
        context_vars: Optional[Dict[str, str]] = None,
    ) -> Path:
        descriptors = self._get_output_descriptors()
        if not descriptors or descriptor_index >= len(descriptors):
            raise ValueError(
                f'Step {self.name} has no output descriptor at index {descriptor_index}',
            )

        descriptor = descriptors[descriptor_index]
        return descriptor.resolve_path(context.base_output_dir, context_vars)

    def _get_standard_cache_path(
        self,
        input_data: InputT,
        context: ExecutionContext,
        descriptor_index: int = 0,
    ) -> Path:
        return self._resolve_output_path(
            descriptor_index,
            context,
            {
                'season': input_data.episode_info.season_code(),
                'episode': input_data.episode_info.episode_code(),
            },
        )

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
            futures_to_input = {
                executor.submit(executor_fn, artifact, context): artifact
                for artifact in input_data
            }

            results_dict: Dict[int, OutputT] = {}
            for future in as_completed(futures_to_input):
                input_artifact = futures_to_input[future]
                result = future.result()
                results_dict[id(input_artifact)] = result

            return [results_dict[id(artifact)] for artifact in input_data]

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

    def __execute_managed_flow(
        self, input_data: InputT, context: ExecutionContext,
    ) -> OutputT:
        cache_path = self._get_cache_path(input_data, context)

        if self.__should_restore_from_cache(cache_path, input_data, context):
            return self.__restore_result(cache_path, input_data, context)

        return self.__compute_new_result(input_data, context)

    def __should_restore_from_cache(
        self, cache_path: Path, input_data: InputT, context: ExecutionContext,
    ) -> bool:
        episode_id = 'all' if input_data is None else input_data.episode_id
        return self._check_cache_validity(
            cache_path, context, episode_id, 'cached',
        )

    def __restore_result(
        self, cache_path: Path, input_data: InputT, context: ExecutionContext,
    ) -> OutputT:
        episode_id = 'all' if input_data is None else input_data.episode_id
        context.logger.info(f'Loading {episode_id} from cache')
        return self._load_from_cache(cache_path, input_data, context)

    def __compute_new_result(
        self, input_data: InputT, context: ExecutionContext,
    ) -> OutputT:
        episode_id = 'all' if input_data is None else input_data.episode_id
        context.logger.info(f'Processing {episode_id}')
        context.mark_step_started(self.name, episode_id)

        result = self._process(input_data, context)

        context.mark_step_completed(self.name, episode_id)
        return result

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

    def __validate_all_descriptors(
        self,
        context: ExecutionContext,
        context_vars: Optional[Dict[str, str]],
        episode_id: str,
    ) -> bool:
        descriptors = self._get_output_descriptors()
        if not descriptors:
            return True

        return all(
            self.__validate_single_descriptor(descriptor, context, context_vars, episode_id)
            for descriptor in descriptors
        )

    @staticmethod
    def __validate_single_descriptor(
        descriptor: OutputDescriptor,
        context: ExecutionContext,
        context_vars: Optional[Dict[str, str]],
        episode_id: str,
    ) -> bool:
        result = descriptor.validate(context.base_output_dir, context_vars)
        if not result.is_valid:
            context.logger.warning(
                f'{episode_id} - output invalid: {result.message}',
            )
            return False
        return True
