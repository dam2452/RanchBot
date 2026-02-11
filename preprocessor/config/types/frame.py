from typing import (
    NotRequired,
    TypedDict,
)


class FrameRequest(TypedDict):
    frame: int
    scene_number: NotRequired[int]
    time: float
    type: str
