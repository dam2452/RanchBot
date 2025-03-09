from pathlib import Path
from typing import (
    Optional,
    Tuple,
)

import ffmpeg

from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class AudioNormalizer:
    SUPPORTED_VIDEO_EXTENSIONS: Tuple[str, str, str] = (".mp4", ".mkv", ".avi")

    def __init__(self, input_videos: Path, output_dir: Path, logger: ErrorHandlingLogger):
        self.__input_videos: Path = input_videos
        self.__output_dir: Path = output_dir
        self.__logger: ErrorHandlingLogger = logger

        self.__output_dir.mkdir(parents=True, exist_ok=True)

    def __call__(self) -> None:
        for video in self.__input_videos.rglob("*"):
            if video.suffix.lower() in self.SUPPORTED_VIDEO_EXTENSIONS:
                self.__process_video(video)


    def __process_video(self, video: Path) -> None:
        try:
            audio_idx = self.__get_best_audio_stream(video)

            if audio_idx is None:
                self.__logger.error(f"Cannot find audio stream for file: '{video}'")
                return

            self.__normalize(
                video=video,
                audio_idx=audio_idx,
                output=self.__output_dir / video.with_suffix(".wav"),
            )
        except Exception as e: # pylint: disable=broad-exception-caught
            self.__logger.error(f"Error processing video: {e}")


    def __get_best_audio_stream(self, video: Path) -> Optional[int]:
        probe = ffmpeg.probe(video, select_streams="a", show_streams=True)
        streams = probe.get("streams", [])

        if not streams:
            self.__logger.error(f"No audio streams found in file: {video}")
            return None

        best_stream = max(streams, key=lambda s: int(s.get("bit_rate", 0)))
        return best_stream["index"]

    def __normalize(self, video: Path, audio_idx: int, output: Path) -> None:
        tmp_output = str(output).replace(".wav", "_temp.wav")

        ffmpeg.input(video, **{"map": f"0:{audio_idx}"}) \
            .output(output, acodec="pcm_s16le", ar=48000, ac=1) \
            .run(overwrite_output=True)

        self.__logger.info(f"Converted audio: {output}")

        ffmpeg.input(output).output(tmp_output, af="dynaudnorm").run(overwrite_output=True)
        self.__logger.info(f"Normalized audio: {tmp_output}")

        Path(tmp_output).replace(output)
        self.__logger.info(f"Replaced original file with normalized audio: {video} -> {output}")
