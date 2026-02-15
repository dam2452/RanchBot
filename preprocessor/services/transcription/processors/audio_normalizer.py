import json
from pathlib import Path
import subprocess
from typing import (
    List,
    Optional,
)

from preprocessor.services.core.base_processor import BaseProcessor
from preprocessor.services.core.logging import ErrorHandlingLogger


class AudioNormalizer:
    SUPPORTED_VIDEO_EXTENSIONS = BaseProcessor.SUPPORTED_VIDEO_EXTENSIONS

    def __init__(
            self,
            input_videos: Path,
            output_dir: Path,
            logger: ErrorHandlingLogger,
            video_files: Optional[List[Path]] = None,
    ) -> None:
        self.__input_videos = input_videos
        self.__output_dir = output_dir
        self.__logger = logger
        self.__video_files = video_files
        self.__output_dir.mkdir(parents=True, exist_ok=True)

    def __call__(self) -> None:
        targets = self.__video_files if self.__video_files is not None else self.__discover_videos()
        for video in targets:
            self.__process_video(video)

    def __discover_videos(self) -> List[Path]:
        return [
            v for v in self.__input_videos.rglob('*')
            if v.suffix.lower() in self.SUPPORTED_VIDEO_EXTENSIONS
        ]

    def __process_video(self, video: Path) -> None:
        try:
            output_path = self.__output_dir / video.with_suffix('.wav').name
            if output_path.exists():
                return

            audio_idx = self.__get_best_audio_stream(video)
            if audio_idx is None:
                return

            self.__execute_normalization_pipeline(video, audio_idx, output_path)
        except Exception as e:
            self.__logger.error(f'Error processing video {video}: {e}')

    def __get_best_audio_stream(self, video: Path) -> Optional[int]:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'a',
            '-show_entries', 'stream=index,bit_rate', '-of', 'json', str(video),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        streams = json.loads(result.stdout).get('streams', [])

        if not streams:
            self.__logger.error(f'No audio streams found in file: {video}')
            return None

        best_stream = max(streams, key=lambda s: int(s.get('bit_rate', 0) or 0))
        return best_stream['index']

    def __execute_normalization_pipeline(self, video: Path, audio_idx: int, output: Path) -> None:
        self.__extract_audio(video, audio_idx, output)

        tmp_output = output.with_name(output.stem + '_temp.wav')
        normalize_cmd = ['ffmpeg', '-y', '-i', str(output), '-af', 'dynaudnorm', str(tmp_output)]
        subprocess.run(normalize_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        tmp_output.replace(output)
        self.__logger.info(f'Normalization complete: {output.name}')

    @staticmethod
    def __extract_audio(video: Path, audio_idx: int, output: Path) -> None:
        cmd = [
            'ffmpeg', '-y', '-i', str(video), '-map', f'0:{audio_idx}',
            '-acodec', 'pcm_s16le', '-ar', '48000', '-ac', '1', str(output),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
