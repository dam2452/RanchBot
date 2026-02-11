from typing import (
    List,
    NotRequired,
    TypedDict,
)


class SceneDict(TypedDict):
    end_frame: int
    end_time: float
    fps: float
    scene_number: int
    start_frame: int
    start_time: float

class SceneTimestampPoint(TypedDict):
    frame: int
    seconds: float

class SceneTimestamp(TypedDict):
    end: SceneTimestampPoint
    scene_number: int
    start: SceneTimestampPoint

class SceneTimestampsData(TypedDict):
    fps: NotRequired[float]
    scenes: List[SceneTimestamp]
    total_scenes: NotRequired[int]
