from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from PIL import Image


def _load_single_frame(frames_dir: Path, request: Dict[str, Any], convert_rgb: bool) -> Image.Image:
    frame_num = request["frame_number"]
    frame_path = frames_dir / f"frame_{frame_num:06d}.jpg"
    if frame_path.exists():
        img = Image.open(frame_path)
        if convert_rgb and img.mode != 'RGB':
            img = img.convert('RGB')
        return img
    return Image.new('RGB', (1, 1))


def load_frames_from_requests(
    frames_dir: Path,
    frame_requests: List[Dict[str, Any]],
    convert_rgb: bool = False,
    num_workers: int = 4,
) -> List[Image.Image]:
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        images = list(
            executor.map(
                lambda req: _load_single_frame(frames_dir, req, convert_rgb),
                frame_requests,
            ),
        )
    return images
