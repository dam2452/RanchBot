import json
import logging
from pathlib import Path
import subprocess
import tempfile
from typing import (
    List,
    Optional,
    Tuple,
)

import ffmpeg

from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class TranscriptionGenerator:
    DEFAULT_OUTPUT_DIR: Path = "transcriptions"
    DEFAULT_MODEL: str = "large-v3"
    DEFAULT_LANGUAGE: str = "Polish"
    DEFAULT_DEVICE: str = "cuda"

    SUPPORTED_AUDIO_EXTENSIONS: Tuple[str, str]      = [".wav", ".mp3"]
    SUPPORTED_VIDEO_EXTENSIONS: Tuple[str, str, str] = [".mp4", ".mkv", ".avi"]


    def __init__(self, args: json):
        self.__input_videos: Path = Path(args["input_videos"])
        self.__output_jsons: Path = Path(args["transcription_jsons_dir"])

        self.__model: str = args["model"]
        self.__language: str = args["language"]
        self.__device: str = args["device"]

        self.__extra_json_keys_to_remove: List[str] = args["extra_json_keys_to_remove"]

        self.__temp_dir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()

        if not self.__input_videos.is_dir():
            raise NotADirectoryError(f"Input videos is not a directory: '{self.__input_videos}'")

        self.__output_jsons.mkdir(parents=True, exist_ok=True)

        self.logger: ErrorHandlingLogger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=2,
        )

        # normalizer -> audio processor -> json processor

    def work(self) -> int:
        try:
            normalized_paths = []
            for video in self.__input_videos.rglob("*"):
                if video.suffix.lower() in self.SUPPORTED_VIDEO_EXTENSIONS:
                    normalized_paths.append(self.__process_video(video))

            processed_audio_files = []
            for audio in normalized_paths:
                if audio.suffix.lower() in self.SUPPORTED_AUDIO_EXTENSIONS:
                    processed_audio_files.append(self.__process_normalized_audio(audio))

        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error(f"Error generating transcriptions: {e}")

        return self.logger.finalize()

    def __process_video(self, video: Path) -> Optional[Path]:
        audio_idx = self.__get_best_audio_stream(video)

        if audio_idx is None:
            self.logger.error(f"Cannot find audio stream for file: '{video}'")
            return None

        normalized_path = Path(self.__temp_dir.name) / video.relative_to(self.__input_videos).with_suffix(".wav")
        self.__normalize(
            video=video,
            audio_idx=audio_idx,
            output=normalized_path,
        )
        return normalized_path

    def __get_best_audio_stream(self, video: Path) -> Optional[int]:
        probe = ffmpeg.probe(video, select_streams="a", show_streams=True)
        streams = probe.get("streams", [])

        if not streams:
            self.logger.error(f"No audio streams found in file: {video}")
            return None

        best_stream = max(streams, key=lambda s: int(s.get("bit_rate", 0)))
        return best_stream["index"]

    def __normalize(self, video: Path, audio_idx: int, output: Path) -> None:
        tmp_output = str(output).replace(".wav", "_temp.wav")

        ffmpeg.input(video, **{"map": f"0:{audio_idx}"}) \
            .output(output, acodec="pcm_s16le", ar=48000, ac=1) \
            .run(overwrite_output=True)

        self.logger.info(f"Converted audio: {output}")

        ffmpeg.input(output).output(tmp_output, af="dynaudnorm").run(overwrite_output=True)
        self.logger.info(f"Normalized audio: {tmp_output}")

        Path(tmp_output).replace(output)
        self.logger.info(f"Replaced original file with normalized audio: {output}")

    def __process_normalized_audio(self, normalized_audio: Path) -> Optional[Path]:
        try:
            output_path = self.__temp_dir.name / normalized_audio.relative_to(self.__temp_dir.name).with_suffix("_processed.wav")

            subprocess.run(
                [
                    "whisper", str(normalized_audio), "--model", self.__model,
                    "--language", self.__language, "--device", self.__device,
                    "--output_dir", str(output_path.parent),
                ],
                check=True,
            )
            self.logger.info(f"Processed: {normalized_audio} -> {output_path}")
            return output_path
        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error(f"Error processing file {normalized_audio}: {e}")

        return None

    def __dump_json(self) -> None:
        pass

    def __format_json(self) -> None:
        pass
