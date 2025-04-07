from typing import List

from pydantic import (
    BaseModel,
    Field,
)


class CommandRequest(BaseModel):
    args: List[str]

class TextCompatibleCommandWrapper(CommandRequest):
    text: str = Field(default="")

    def __init__(self, command_name: str, args: list[str]):
        text = f"{command_name} {' '.join(args)}".strip()
        super().__init__(args=args, text=text)

    def __str__(self):
        return self.text
