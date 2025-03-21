from enum import Enum
from typing import Any


class Resolution(Enum):
    R1080P = (1920, 1080)
    R720P  = (1280, 720)
    R480P  = (854,  480)

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

    def __str__(self):
        return f"{self.height}p"

    @staticmethod
    def from_str(init: str) -> Any: #todo
        init = init.strip()
        if not init[0].isalpha():
            init = "R" + init.upper()
        else:
            init = init.upper()
        return Resolution[init]

