from typing import (
    List,
    NotRequired,
    TypedDict,
)


class CharacterDetectionInFrame(TypedDict):
    bbox: List[int]
    confidence: float
    embedding: NotRequired[List[float]]
    name: str


class ObjectDetectionInFrame(TypedDict):
    bbox: List[int]
    class_id: int
    class_name: str
    confidence: float


class Detection(TypedDict):
    bbox: List[int]
    class_id: NotRequired[int]
    class_name: NotRequired[str]
    confidence: float
    name: NotRequired[str]
