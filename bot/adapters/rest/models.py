from enum import Enum
from typing import (
    Annotated,
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
)


class CommandRequest(BaseModel):
    args: List[str]
    reply_json: bool = Field(default=True)


class TextCompatibleCommandWrapper(CommandRequest):
    text: str = Field(default="")

    def __init__(self, command_name: str, args: List[str], json: bool):
        text = f"{command_name} {' '.join(args)}".strip()
        super().__init__(args=args, text=text, reply_json=json)

    def __str__(self):
        return self.text


class RegisterRequest(BaseModel):
    username: Annotated[str, StringConstraints(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")]
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]
    full_name: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    username: Annotated[str, StringConstraints(min_length=1, max_length=64)]


class ResetPasswordRequest(BaseModel):
    username: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    code: Annotated[str, StringConstraints(min_length=6, max_length=6, pattern=r"^\d{6}$")]
    new_password: Annotated[str, StringConstraints(min_length=8, max_length=128)]


class AttachCredentialsRequest(BaseModel):
    token: Annotated[str, StringConstraints(min_length=8, max_length=64)]
    username: Annotated[str, StringConstraints(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")]
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
