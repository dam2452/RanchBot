from enum import Enum
from typing import (
    List,
    Type,
    TypeVar,
)

T = TypeVar('T', bound='Resolution')


class Resolution(Enum):
    R144P = (256, 144)
    R240P = (426, 240)
    R360P = (640, 360)
    R480P = (854, 480)
    R720P = (1280, 720)
    R1080P = (1920, 1080)
    R1440P = (2560, 1440)
    R2160P = (3840, 2160)
    R4320P = (7680, 4320)

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def __str__(self) -> str:
        return f'{self.height}p'

    @classmethod
    def from_string(cls: Type[T], init: str) -> T:
        clean_init = init.strip().upper()
        if not clean_init[0].isalpha():
            clean_init = f'R{clean_init}'
        return cls[clean_init]

    @classmethod
    def get_all_choices(cls) -> List[str]:
        return [str(r) for r in cls]
