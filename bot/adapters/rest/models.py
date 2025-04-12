from enum import Enum
from typing import List

from pydantic import (
    BaseModel,
    Field,
)


class CommandRequest(BaseModel):
    args: List[str]
    reply_json: bool = Field(default=False)

class TextCompatibleCommandWrapper(CommandRequest):
    text: str = Field(default="")

    def __init__(self, command_name: str, args: List[str], json: bool = False):
        text = f"{command_name} {' '.join(args)}".strip()
        super().__init__(args=args, text=text, json=json)

    def __str__(self):
        return self.text

class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
