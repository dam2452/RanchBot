from dataclasses import dataclass
from pathlib import Path
from typing import (
    Optional,
    Tuple,
)


@dataclass
class TranscodeParams:

    input_path: Path
    output_path: Path
    codec: str
    preset: str
    resolution: str
    video_bitrate: str
    minrate: str
    maxrate: str
    bufsize: str
    audio_bitrate: str
    gop_size: int
    target_fps: Optional[float] = None
    deinterlace: bool = False
    is_upscaling: bool = False
    log_command: bool = False

    def get_resolution_tuple(self) -> Tuple[int, int]:
        try:
            width, height = [int(x) for x in self.resolution.split(':')]
            return width, height
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid resolution format: {self.resolution}") from e
