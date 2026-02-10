import json
from pathlib import Path
import subprocess
from typing import (
    List,
    Optional,
)

from preprocessor.core.base_processor import BaseProcessor
from preprocessor.lib.core.logging import ErrorHandlingLogger


class AudioNormalizer:
    SUPPORTED_VIDEO_EXTENSIONS = BaseProcessor.SUPPORTED_VIDEO_EXTENSIONS

    def __init__(self, input_videos: Path, output_dir: Path, logger: ErrorHandlingLogger, video_files: Optional[List[Path]]=None):
        self.__input_videos: Path = input_videos
        self.__output_dir: Path = output_dir
        self.__logger: ErrorHandlingLogger = logger
        self.__video_files: Optional[List[Path]] = video_files
        self.__output_dir.mkdir(parents=True, exist_ok=True)

    def __call__(self) -> None:
        if self.__video_files is not None:
            for video in self.__video_files:
                self.__process_video(video)
        else:
            for video in self.__input_videos.rglob('*'):
                if video.suffix.lower() in self.SUPPORTED_VIDEO_EXTENSIONS:
                    self.__process_video(video)

    def __process_video(self, video: Path) -> None:
        try:
            output_path = self.__output_dir / video.with_suffix('.wav').name
            if output_path.exists():
                return
            audio_idx = self.__get_best_audio_stream(video)
            if audio_idx is None:
                self.__logger.error(f"Cannot find audio stream for file: '{video}'")
                return
            self.__normalize(video=video, audio_idx=audio_idx, output=output_path)
        except Exception as e:
            self.__logger.error(f'Error processing video {video}: {e}')

    def __get_best_audio_stream(self, video: Path) -> Optional[int]:
        cmd = ['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index,bit_rate', '-of', 'json', str(video)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        streams = json.loads(result.stdout).get('streams', [])
        if not streams:
            self.__logger.error(f'No audio streams found in file: {video}')
            return None
        best_stream = max(streams, key=lambda s: int(s.get('bit_rate', 0)))
        return best_stream['index']

    def __normalize(self, video: Path, audio_idx: int, output: Path) -> None:
        tmp_output = output.with_name(output.stem + '_temp.wav')
        extract_cmd = ['ffmpeg', '-y', '-i', str(video), '-map', f'0:{audio_idx}', '-acodec', 'pcm_s16le', '-ar', '48000', '-ac', '1', str(output)]
        subprocess.run(extract_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.__logger.info(f'Converted audio: {output}')
        normalize_cmd = ['ffmpeg', '-y', '-i', str(output), '-af', 'dynaudnorm', str(tmp_output)]
        subprocess.run(normalize_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.__logger.info(f'Normalized audio: {tmp_output}')
        tmp_output.replace(output)
        self.__logger.info(f'Replaced original file with normalized audio: {video} -> {output}')
