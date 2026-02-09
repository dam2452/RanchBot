from typing import (
    List,
    NotRequired,
    TypedDict,
)


class CharacterDetectionInFrame(TypedDict):
    name: str
    confidence: float
    bbox: List[int]
    embedding: NotRequired[List[float]]


class ObjectDetectionInFrame(TypedDict):
    class_name: str
    class_id: int
    confidence: float
    bbox: List[int]


class Detection(TypedDict):
    bbox: List[int]
    confidence: float
    class_id: NotRequired[int]
    class_name: NotRequired[str]
    name: NotRequired[str]
