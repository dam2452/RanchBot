from typing import (
    List,
    NotRequired,
    TypedDict,
)


class SceneDict(TypedDict):
    scene_number: int
    start_frame: int
    end_frame: int
    start_time: float
    end_time: float
    fps: float


class SceneTimestampPoint(TypedDict):
    frame: int
    seconds: float


class SceneTimestamp(TypedDict):
    scene_number: int
    start: SceneTimestampPoint
    end: SceneTimestampPoint


class SceneTimestampsData(TypedDict):
    scenes: List[SceneTimestamp]
    total_scenes: NotRequired[int]
    fps: NotRequired[float]
