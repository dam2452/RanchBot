from enum import Enum


class ResponseType(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    JSON = "json"
