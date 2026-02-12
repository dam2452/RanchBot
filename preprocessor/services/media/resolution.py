from enum import Enum
from typing import (
    List,
    Type,
    TypeVar,
)

T = TypeVar('T', bound='Resolution')

class Resolution(Enum):
    R1080P = (1920, 1080)
    R1440P = (2560, 1440)
    R144P = (256, 144)
    R2160P = (3840, 2160)
    R240P = (426, 240)
    R360P = (640, 360)
    R4320P = (7680, 4320)
    R480P = (854, 480)
    R720P = (1280, 720)

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def __str__(self) -> str:
        return f'{self.height}p'

    @classmethod
    def from_string(cls: Type[T], init: str) -> T:
        init = init.strip()
        if not init[0].isalpha():
            init = 'R' + init.upper()
        else:
            init = init.upper()
        return cls[init]

    @classmethod
    def __from_str(cls: Type[T], init: str) -> T:  # pylint: disable=unused-private-member
        return cls.from_string(init)

    @classmethod
    def __get_all_choices(cls) -> List[str]:  # pylint: disable=unused-private-member
        return [str(r) for r in cls]
