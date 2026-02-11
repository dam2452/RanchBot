from preprocessor.config.step_configs import ValidationConfig
from preprocessor.core.artifacts import (
    ElasticDocuments,
    ValidationResult,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.validation.validator import Validator


class ValidationStep(PipelineStep[ElasticDocuments, ValidationResult, ValidationConfig]):

    def execute(
        self,
        input_data: ElasticDocuments,
        context: ExecutionContext,
    ) -> ValidationResult:
        context.logger.info(f"Starting validation for season {context.season}")

        validator = self._create_validator(context)
        self._run_validation(validator)

        context.logger.info("Validation completed successfully")

        return ValidationResult(
            season=context.season,
            validation_report_dir=validator.validation_reports_dir,
        )

    @property
    def name(self) -> str:
        return "validate"

    def _create_validator(self, context: ExecutionContext) -> Validator:
        return Validator(
            season=context.season,
            series_name=context.series_name,
            anomaly_threshold=self.config.anomaly_threshold,
            base_output_dir=context.base_output_dir,
            episodes_info_json=self.config.episodes_info_json,
        )

    @staticmethod
    def _run_validation(validator: Validator) -> None:
        exit_code = validator.validate()
        if exit_code != 0:
            raise RuntimeError(f"Validation failed with exit code {exit_code}")
