from typing import (
    NotRequired,
    TypedDict,
)

class FrameRequest(TypedDict):
    frame: int
    time: float
    type: str
    scene_number: NotRequired[int]
