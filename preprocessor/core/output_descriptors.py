from abc import (
    ABC,
    abstractmethod,
)
from dataclasses import dataclass
import json
from pathlib import Path
from typing import (
    Callable,
    Dict,
    Optional,
)


@dataclass
class ValidationResult:
    is_valid: bool
    message: str = ''
    file_count: int = 0
    total_size_bytes: int = 0


class OutputDescriptor(ABC):
    def __init__(self, pattern: str, subdir: str) -> None:
        self._pattern = pattern
        self._subdir = subdir

    @property
    def pattern(self) -> str:
        return self._pattern

    @property
    def subdir(self) -> str:
        return self._subdir

    @abstractmethod
    def resolve_path(self, base_dir: Path, context_vars: Optional[Dict[str, str]] = None) -> Path:
        pass

    @abstractmethod
    def validate(self, base_dir: Path, context_vars: Optional[Dict[str, str]] = None) -> ValidationResult:
        pass

    def format_pattern(self, context_vars: Optional[Dict[str, str]] = None) -> str:
        if not context_vars:
            return self._pattern
        return self._pattern.format(**context_vars)


class FileOutput(OutputDescriptor):
    def __init__(
            self,
            pattern: str,
            subdir: str,
            min_size_bytes: int = 1,
            expected_count: int = 1,
    ) -> None:
        super().__init__(pattern, subdir)
        self._min_size_bytes = min_size_bytes
        self._expected_count = expected_count

    def resolve_path(self, base_dir: Path, context_vars: Optional[Dict[str, str]] = None) -> Path:
        formatted_pattern = self.format_pattern(context_vars)
        return base_dir / self._subdir / formatted_pattern

    def validate(self, base_dir: Path, context_vars: Optional[Dict[str, str]] = None) -> ValidationResult:
        file_path = self.resolve_path(base_dir, context_vars)

        if not file_path.exists():
            return ValidationResult(
                is_valid=False,
                message=f'File does not exist: {file_path}',
            )

        if not file_path.is_file():
            return ValidationResult(
                is_valid=False,
                message=f'Path exists but is not a file: {file_path}',
            )

        file_size = file_path.stat().st_size

        if file_size < self._min_size_bytes:
            return ValidationResult(
                is_valid=False,
                message=f'File too small ({file_size} bytes < {self._min_size_bytes}): {file_path}',
                file_count=1,
                total_size_bytes=file_size,
            )

        return ValidationResult(
            is_valid=True,
            message=f'File valid: {file_path}',
            file_count=1,
            total_size_bytes=file_size,
        )


class DirectoryOutput(OutputDescriptor):
    def __init__(
            self,
            pattern: str,
            subdir: str,
            expected_file_pattern: Optional[str] = None,
            min_files: int = 1,
            min_size_per_file_bytes: int = 1,
    ) -> None:
        super().__init__(pattern, subdir)
        self._expected_file_pattern = expected_file_pattern
        self._min_files = min_files
        self._min_size_per_file_bytes = min_size_per_file_bytes

    def resolve_path(self, base_dir: Path, context_vars: Optional[Dict[str, str]] = None) -> Path:
        formatted_pattern = self.format_pattern(context_vars)
        return base_dir / self._subdir / formatted_pattern

    def validate(self, base_dir: Path, context_vars: Optional[Dict[str, str]] = None) -> ValidationResult:
        dir_path = self.resolve_path(base_dir, context_vars)

        if not dir_path.exists():
            return ValidationResult(
                is_valid=False,
                message=f'Directory does not exist: {dir_path}',
            )

        if not dir_path.is_dir():
            return ValidationResult(
                is_valid=False,
                message=f'Path exists but is not a directory: {dir_path}',
            )

        if self._expected_file_pattern:
            files = list(dir_path.glob(self._expected_file_pattern))
        else:
            files = [f for f in dir_path.iterdir() if f.is_file()]

        if len(files) < self._min_files:
            return ValidationResult(
                is_valid=False,
                message=(
                    f'Not enough files in directory ({len(files)} < {self._min_files}): '
                    f'{dir_path}'
                ),
                file_count=len(files),
            )

        total_size = 0
        for file_path in files:
            file_size = file_path.stat().st_size
            total_size += file_size

            if file_size < self._min_size_per_file_bytes:
                return ValidationResult(
                    is_valid=False,
                    message=(
                        f'File too small ({file_size} bytes < {self._min_size_per_file_bytes}): '
                        f'{file_path}'
                    ),
                    file_count=len(files),
                    total_size_bytes=total_size,
                )

        return ValidationResult(
            is_valid=True,
            message=f'Directory valid: {dir_path} ({len(files)} files, {total_size} bytes)',
            file_count=len(files),
            total_size_bytes=total_size,
        )


class JsonFileOutput(FileOutput):
    def __init__(
            self,
            pattern: str,
            subdir: str,
            min_size_bytes: int = 2,
            schema_validator: Optional[Callable[[Dict], bool]] = None,
    ) -> None:
        super().__init__(pattern, subdir, min_size_bytes)
        self._schema_validator = schema_validator

    def validate(self, base_dir: Path, context_vars: Optional[Dict[str, str]] = None) -> ValidationResult:
        basic_validation = super().validate(base_dir, context_vars)

        if not basic_validation.is_valid:
            return basic_validation

        file_path = self.resolve_path(base_dir, context_vars)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                message=f'Invalid JSON in {file_path}: {e}',
                file_count=1,
                total_size_bytes=basic_validation.total_size_bytes,
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                message=f'Failed to read JSON from {file_path}: {e}',
                file_count=1,
                total_size_bytes=basic_validation.total_size_bytes,
            )

        if self._schema_validator:
            try:
                if not self._schema_validator(data):
                    return ValidationResult(
                        is_valid=False,
                        message=f'JSON schema validation failed: {file_path}',
                        file_count=1,
                        total_size_bytes=basic_validation.total_size_bytes,
                    )
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    message=f'Schema validation error for {file_path}: {e}',
                    file_count=1,
                    total_size_bytes=basic_validation.total_size_bytes,
                )

        return ValidationResult(
            is_valid=True,
            message=f'JSON file valid: {file_path}',
            file_count=1,
            total_size_bytes=basic_validation.total_size_bytes,
        )


class GlobalOutput(OutputDescriptor):
    def __init__(self, pattern: str, subdir: str = '') -> None:
        super().__init__(pattern, subdir)

    def resolve_path(self, base_dir: Path, context_vars: Optional[Dict[str, str]] = None) -> Path:
        formatted_pattern = self.format_pattern(context_vars)
        if self._subdir:
            return base_dir / self._subdir / formatted_pattern
        return base_dir / formatted_pattern

    def validate(self, base_dir: Path, context_vars: Optional[Dict[str, str]] = None) -> ValidationResult:
        file_path = self.resolve_path(base_dir, context_vars)

        if not file_path.exists():
            return ValidationResult(
                is_valid=False,
                message=f'Global output does not exist: {file_path}',
            )

        if file_path.is_file():
            file_size = file_path.stat().st_size
            return ValidationResult(
                is_valid=True,
                message=f'Global file valid: {file_path}',
                file_count=1,
                total_size_bytes=file_size,
            )

        if file_path.is_dir():
            files = [f for f in file_path.rglob('*') if f.is_file()]
            total_size = sum(f.stat().st_size for f in files)
            return ValidationResult(
                is_valid=True,
                message=f'Global directory valid: {file_path} ({len(files)} files)',
                file_count=len(files),
                total_size_bytes=total_size,
            )

        return ValidationResult(
            is_valid=False,
            message=f'Global output path is neither file nor directory: {file_path}',
        )


def create_frames_output() -> DirectoryOutput:
    """Create standard DirectoryOutput descriptor for exported frames."""
    return DirectoryOutput(
        pattern="{season}/{episode}",
        subdir="frames",
        expected_file_pattern="*.png",
        min_files=1,
        min_size_per_file_bytes=1024,
    )
