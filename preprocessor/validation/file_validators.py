import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image


@dataclass
class ValidationResult:
    is_valid: bool
    error_message: Optional[str] = None
    metadata: Optional[dict] = None


def validate_json_file(path: Path) -> ValidationResult:
    if not path.exists():
        return ValidationResult(is_valid=False, error_message=f"File does not exist: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)
        return ValidationResult(is_valid=True, metadata={"size_bytes": path.stat().st_size})
    except json.JSONDecodeError as e:
        return ValidationResult(is_valid=False, error_message=f"Invalid JSON: {e}")
    except Exception as e:
        return ValidationResult(is_valid=False, error_message=f"Error reading file: {e}")


def validate_jsonl_file(path: Path) -> ValidationResult:
    if not path.exists():
        return ValidationResult(is_valid=False, error_message=f"File does not exist: {path}")

    try:
        line_count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                    line_count += 1
                except json.JSONDecodeError as e:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Invalid JSON at line {line_num}: {e}",
                    )
        return ValidationResult(
            is_valid=True,
            metadata={"size_bytes": path.stat().st_size, "line_count": line_count},
        )
    except Exception as e:
        return ValidationResult(is_valid=False, error_message=f"Error reading file: {e}")


def validate_image_file(path: Path) -> ValidationResult:
    if not path.exists():
        return ValidationResult(is_valid=False, error_message=f"File does not exist: {path}")

    try:
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            width, height = img.size
            format_type = img.format
            size_mb = path.stat().st_size / (1024 * 1024)

        return ValidationResult(
            is_valid=True,
            metadata={
                "width": width,
                "height": height,
                "format": format_type,
                "size_mb": round(size_mb, 2),
            },
        )
    except Exception as e:
        return ValidationResult(is_valid=False, error_message=f"Invalid image: {e}")


def validate_video_file(path: Path) -> ValidationResult:
    if not path.exists():
        return ValidationResult(is_valid=False, error_message=f"File does not exist: {path}")

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name,width,height,duration",
                "-show_entries",
                "format=duration,size",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        probe_data = json.loads(result.stdout)
        stream = probe_data.get("streams", [{}])[0]
        format_info = probe_data.get("format", {})

        duration = float(stream.get("duration", format_info.get("duration", 0)))
        size_bytes = int(format_info.get("size", 0))
        size_mb = size_bytes / (1024 * 1024)

        return ValidationResult(
            is_valid=True,
            metadata={
                "codec": stream.get("codec_name"),
                "width": stream.get("width"),
                "height": stream.get("height"),
                "duration": round(duration, 2),
                "size_mb": round(size_mb, 2),
            },
        )
    except subprocess.CalledProcessError as e:
        return ValidationResult(is_valid=False, error_message=f"ffprobe error: {e.stderr}")
    except Exception as e:
        return ValidationResult(is_valid=False, error_message=f"Error validating video: {e}")
