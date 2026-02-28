from collections import Counter
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    List,
)


@dataclass(frozen=True)
class AnalysisData:
    video_info: List[Dict[str, Any]]
    resolution_counts: Counter
    total_episodes: int
    target_width: int
    target_height: int
    target_pixels: int
    upscaling_count: int
    upscaling_pct: float
    progressive_count: int
    needs_deinterlace_count: int
    metadata_mismatch_count: int
