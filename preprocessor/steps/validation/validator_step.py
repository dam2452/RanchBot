from typing import List

from preprocessor.config.step_configs import ValidationConfig
from preprocessor.core.artifacts import (
    ElasticDocuments,
    ValidationResult,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.validation.validator import Validator


class ValidationStep(PipelineStep[ElasticDocuments, ValidationResult, ValidationConfig]):
    @property
    def supports_batch_processing(self) -> bool:
        return True

    @property
    def uses_caching(self) -> bool:
        return False

    def execute_batch(
        self, input_data: List[ElasticDocuments], context: ExecutionContext,
    ) -> List[ValidationResult]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def _process(
        self,
        input_data: ElasticDocuments,
        context: ExecutionContext,
    ) -> ValidationResult:
        context.logger.info(f"Starting validation for season {context.season}")

        validator = self.__create_validator(context)
        self.__run_validation(validator)

        context.logger.info("Validation completed successfully")

        return self.__construct_validation_result(context, validator)

    def __create_validator(self, context: ExecutionContext) -> Validator:
        return Validator(
            season=context.season,
            series_name=context.series_name,
            anomaly_threshold=self.config.anomaly_threshold,
            base_output_dir=context.base_output_dir,
            episodes_info_json=self.config.episodes_info_json,
        )

    @staticmethod
    def __run_validation(validator: Validator) -> None:
        exit_code = validator.validate()
        if exit_code != 0:
            raise RuntimeError(f"Validation failed with exit code {exit_code}")

    @staticmethod
    def __construct_validation_result(
        context: ExecutionContext,
        validator: Validator,
    ) -> ValidationResult:
        return ValidationResult(
            season=context.season,
            validation_report_dir=validator.validation_reports_dir,
        )
