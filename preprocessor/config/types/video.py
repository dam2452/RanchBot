from typing import (
    NotRequired,
    TypedDict,
)


class HashResult(TypedDict):
    file_path: NotRequired[str]
    frame_number: int
    hash: str
    timestamp: float

class VideoMetadata(TypedDict):
    bitrate: NotRequired[int]
    codec: NotRequired[str]
    duration: float
    fps: float
    height: int
    width: int
