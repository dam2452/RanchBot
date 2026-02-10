import logging
from pathlib import Path
import tempfile
from typing import (
    Any,
    Dict,
    List,
    Optional,
)


class MockFFmpeg:
    _video_files: Dict[str, Path] = {}
    _call_log: List[Dict[str, Any]] = []
    _temp_files: List[Path] = []

    @classmethod
    def reset(cls):
        for temp_file in cls._temp_files:
            if temp_file.exists():
                temp_file.unlink()
        cls._video_files = {}
        cls._call_log = []
        cls._temp_files = []

    @classmethod
    def add_mock_clip(
        cls,
        source_video_path: str,
        mock_clip_path: Optional[Path] = None,
        create_file: bool = True,
    ) -> Path:
        if mock_clip_path is None:
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            mock_clip_path = Path(temp_file.name)
            temp_file.close()
            cls._temp_files.append(mock_clip_path)

        if create_file and not mock_clip_path.exists():
            mock_clip_path.write_bytes(b'FAKE_MP4_DATA')

        cls._video_files[source_video_path] = mock_clip_path
        return mock_clip_path

    @classmethod
    def get_mock_clip_path(cls, source_video_path: str) -> Optional[Path]:
        return cls._video_files.get(source_video_path)

    @classmethod
    async def extract_clip(
        cls,
        video_path: str,
        start_time: float,
        end_time: float,
        logger: logging.Logger,
        output_path: Optional[Path] = None,
        resolution_key: str = '720p',
    ) -> Path:
        cls._call_log.append({
            'method': 'extract_clip',
            'video_path': video_path,
            'start_time': start_time,
            'end_time': end_time,
            'resolution_key': resolution_key,
        })

        if video_path in cls._video_files:
            mock_path = cls._video_files[video_path]
            logger.info(f"MockFFmpeg: Returning mock clip {mock_path} for {video_path}")
            return mock_path

        if output_path is None:
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            output_path = Path(temp_file.name)
            temp_file.close()
            cls._temp_files.append(output_path)

        output_path.write_bytes(b'FAKE_EXTRACTED_CLIP')
        logger.warning(f"MockFFmpeg: No mock clip found for {video_path}, creating fake file at {output_path}")
        return output_path

    @classmethod
    async def compile_clips(
        cls,
        clip_paths: List[Path],
        output_path: Path,
        logger: logging.Logger,
        resolution_key: str = '720p',
    ) -> Path:
        cls._call_log.append({
            'method': 'compile_clips',
            'clip_paths': [str(p) for p in clip_paths],
            'output_path': str(output_path),
            'resolution_key': resolution_key,
        })

        output_path.write_bytes(b'FAKE_COMPILED_CLIP')
        logger.info(f"MockFFmpeg: Created fake compiled clip at {output_path}")
        return output_path

    @classmethod
    def get_call_log(cls) -> List[Dict[str, Any]]:
        return cls._call_log

    @classmethod
    def get_call_count(cls, method_name: str) -> int:
        return sum(1 for call in cls._call_log if call['method'] == method_name)

    @classmethod
    def assert_extract_clip_called_with(
        cls,
        video_path: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ):
        for call in cls._call_log:
            if call['method'] != 'extract_clip':
                continue
            if call['video_path'] != video_path:
                continue
            if start_time is not None and abs(call['start_time'] - start_time) > 0.1:
                continue
            if end_time is not None and abs(call['end_time'] - end_time) > 0.1:
                continue
            return True

        raise AssertionError(
            f"extract_clip not called with video_path={video_path}, "
            f"start_time={start_time}, end_time={end_time}",
        )
