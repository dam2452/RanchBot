from typing import (
    Any,
    TypedDict,
    Union,
)


class ClipSegment(TypedDict):
    video_path: Union[str, Any]
    start_time: float
    end_time: float
