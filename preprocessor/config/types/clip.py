from typing import (
    Any,
    TypedDict,
    Union,
)


class ClipSegment(TypedDict):
    end_time: float
    start_time: float
    video_path: Union[str, Any]
