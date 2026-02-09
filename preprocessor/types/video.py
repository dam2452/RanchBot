from typing import (
    List,
    NotRequired,
    TypedDict,
)

class HashResult(TypedDict):
    frame_number: int
    timestamp: float
    hash: str
    file_path: NotRequired[str]


class VideoMetadata(TypedDict):
    width: int
    height: int
    fps: float
    duration: float
    codec: NotRequired[str]
    bitrate: NotRequired[int]
