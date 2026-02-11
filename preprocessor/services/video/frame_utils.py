from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from PIL import Image


class FrameLoader:

    @staticmethod
    def load_from_requests(frames_dir: Path, frame_requests: List[Dict[str, Any]], convert_rgb: bool=False, num_workers: int=4) -> List[Image.Image]:
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            images = list(executor.map(lambda req: FrameLoader.__load_single(frames_dir, req, convert_rgb), frame_requests))
        return images

    @staticmethod
    def __load_single(frames_dir: Path, request: Dict[str, Any], convert_rgb: bool) -> Image.Image:
        if 'frame_path' in request:
            frame_path = frames_dir / request['frame_path']
        else:
            frame_num = request['frame_number']
            frame_path = frames_dir / f'frame_{frame_num:06d}.jpg'
        if frame_path.exists():
            img = Image.open(frame_path)
            if convert_rgb and img.mode != 'RGB':
                img = img.convert('RGB')
            return img
        return Image.new('RGB', (1, 1))
