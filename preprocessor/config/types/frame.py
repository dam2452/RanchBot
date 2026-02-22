from typing import (
    NotRequired,
    TypedDict,
)


class FrameRequest(TypedDict):
    frame_number: int
    timestamp: float
    type: str
    scene_number: NotRequired[int]
    original_timestamp: NotRequired[float]
    snapped_to_keyframe: NotRequired[bool]
