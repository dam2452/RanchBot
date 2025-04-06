
from pydantic import BaseModel


class CommandRequest(BaseModel):
    text: str
