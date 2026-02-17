from dataclasses import dataclass
import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    Optional,
)

from PIL import Image

from preprocessor.config.types.keys import (
    FfprobeFormatKeys,
    FfprobeKeys,
    FfprobeStreamKeys,
    ValidationMetadataKeys,
)
from preprocessor.services.media.ffmpeg import FFmpegWrapper


@dataclass
class ValidationResult:
    is_valid: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class FileValidator:
    @staticmethod
    def validate_image_file(path: Path) -> ValidationResult:
        err = FileValidator.__verify_existence(path)
        if err:
            return err
        try:
            with Image.open(path) as img:
                img.verify()
            with Image.open(path) as img:
                return ValidationResult(
                    is_valid=True,
                    metadata={
                        ValidationMetadataKeys.WIDTH: img.size[0],
                        ValidationMetadataKeys.HEIGHT: img.size[1],
                        ValidationMetadataKeys.FORMAT: img.format,
                        ValidationMetadataKeys.SIZE_MB: round(path.stat().st_size / (1024 * 1024), 2),
                    },
                )
        except Exception as e:
            return ValidationResult(False, f'Invalid image: {e}')

    @staticmethod
    def validate_json_file(path: Path) -> ValidationResult:
        err = FileValidator.__verify_existence(path)
        if err:
            return err
        try:
            with open(path, 'r', encoding='utf-8') as f:
                json.load(f)
            return ValidationResult(True, metadata={ValidationMetadataKeys.SIZE_BYTES: path.stat().st_size})
        except Exception as e:
            return ValidationResult(False, f'JSON error: {e}')

    @staticmethod
    def validate_jsonl_file(path: Path) -> ValidationResult:
        if err := FileValidator.__verify_existence(path):
            return err
        try:
            line_count = 0
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        json.loads(line)
                        line_count += 1
            return ValidationResult(
                True,
                metadata={
                    ValidationMetadataKeys.SIZE_BYTES: path.stat().st_size,
                    'line_count': line_count,
                },
            )
        except Exception as e:
            return ValidationResult(False, f'JSONL error: {e}')

    @staticmethod
    def validate_video_file(path: Path) -> ValidationResult:
        err = FileValidator.__verify_existence(path)
        if err:
            return err
        try:
            probe = FileValidator.__run_ffprobe(path)
            stream = probe.get(FfprobeKeys.STREAMS, [{}])[0]
            fmt = probe.get(FfprobeKeys.FORMAT, {})
            duration = float(stream.get(FfprobeStreamKeys.DURATION) or fmt.get(FfprobeFormatKeys.DURATION, 0))

            return ValidationResult(
                is_valid=True,
                metadata={
                    ValidationMetadataKeys.CODEC: stream.get(FfprobeStreamKeys.CODEC_NAME),
                    ValidationMetadataKeys.WIDTH: stream.get(FfprobeStreamKeys.WIDTH),
                    ValidationMetadataKeys.HEIGHT: stream.get(FfprobeStreamKeys.HEIGHT),
                    ValidationMetadataKeys.DURATION: round(duration, 2),
                    ValidationMetadataKeys.SIZE_MB: round(int(fmt.get(FfprobeFormatKeys.SIZE, 0)) / (1024 * 1024), 2),
                },
            )
        except Exception as e:
            return ValidationResult(False, str(e))

    @staticmethod
    def __verify_existence(path: Path) -> Optional[ValidationResult]:
        if not path.exists():
            return ValidationResult(False, f'Missing: {path}')
        return None

    @staticmethod
    def __run_ffprobe(path: Path) -> Dict[str, Any]:
        return FFmpegWrapper.probe_video(path)
