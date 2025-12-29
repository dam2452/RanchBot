from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from PIL import Image


def load_frames_from_requests(
    frames_dir: Path,
    frame_requests: List[Dict[str, Any]],
    convert_rgb: bool = False,
) -> List[Image.Image]:
    images = []
    for request in frame_requests:
        frame_num = request["frame_number"]
        frame_path = frames_dir / f"frame_{frame_num:06d}.jpg"
        if frame_path.exists():
            img = Image.open(frame_path)
            if convert_rgb and img.mode != 'RGB':
                img = img.convert('RGB')
            images.append(img)
        else:
            images.append(Image.new('RGB', (1, 1)))
    return images
