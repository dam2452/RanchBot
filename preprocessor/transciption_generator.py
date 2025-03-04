import json
import logging
from pathlib import Path
import subprocess
import tempfile
from typing import (
    Dict,
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

    DEFAULT_KEYS_TO_REMOVE: List[str] = ["tokens", "no_speech_prob", "compression_ratio", "avg_logprob", "temperature"]
    UNICODE_TO_POLISH_MAP: Dict[str, str] = {
        '\\u0105': 'ą', '\\u0107': 'ć', '\\u0119': 'ę', '\\u0142': 'ł',
        '\\u0144': 'ń', '\\u00F3': 'ó', '\\u015B': 'ś', '\\u017A': 'ź',
        '\\u017C': 'ż', '\\u0104': 'Ą', '\\u0106': 'Ć', '\\u0118': 'Ę',
        '\\u0141': 'Ł', '\\u0143': 'Ń', '\\u00D3': 'Ó', '\\u015A': 'Ś',
        '\\u0179': 'Ź', '\\u017B': 'Ż',
    }


    def __init__(self, args: json):
        self.__input_videos: Path = Path(args["input_videos"])
        self.__output_jsons: Path = Path(args["transcription_jsons_dir"])

        self.__model: str = args["model"]
        self.__language: str = args["language"]
        self.__device: str = args["device"]

        self.__json_keys_to_remove: List[str] = self.DEFAULT_KEYS_TO_REMOVE + args["extra_json_keys_to_remove"]

        self.__temp_dir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()

        if not self.__input_videos.is_dir():
            raise NotADirectoryError(f"Input videos is not a directory: '{self.__input_videos}'")

        self.__output_jsons.mkdir(parents=True, exist_ok=True)

        self.logger: ErrorHandlingLogger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=2,
        )

    def work(self) -> int:
        try:
            normalized_paths = []
            for video in self.__input_videos.rglob("*"):
                if video.suffix.lower() in self.SUPPORTED_VIDEO_EXTENSIONS:
                    normalized_paths.append(self.__process_video(video))

            was_anything_successful = False
            for audio in normalized_paths:
                if audio.suffix.lower() in self.SUPPORTED_AUDIO_EXTENSIONS:
                    was_anything_successful |= self.__process_normalized_audio(audio)

            if was_anything_successful:
                for item in Path(self.__temp_dir.name).rglob("*"):
                    if item.is_file() and item.suffix() == ".json":
                        self.__format_json(item, self.__output_jsons / item.name)

        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error(f"Error generating transcriptions: {e}")

        return self.logger.finalize()

    def __process_video(self, video: Path) -> Optional[Path]:
        try:
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
        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error(f"Error processing video: {e}")

        return None

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

    def __process_normalized_audio(self, normalized_audio: Path) -> bool:
        try:
            subprocess.run(
                [
                    "whisper", str(normalized_audio), "--model", self.__model,
                    "--language", self.__language, "--device", self.__device,
                    "--output_dir", str(self.__temp_dir.name),
                ],
                check=True,
            )
            self.logger.info(f"Processed: {normalized_audio}")
            return True
        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error(f"Error processing file {normalized_audio}: {e}")

        return False

    def __format_json(self, file_path: Path, output_path: Path) -> None:
        try:
            with file_path.open('r', encoding='utf-8') as file:
                data = json.load(file)

            if "segments" in data:
                data["segments"] = [self.__process_json_segment(segment) for segment in data["segments"]]

                with output_path.open('w', encoding='utf-8') as file:
                    json.dump({"segments": data["segments"]}, file, ensure_ascii=False, indent=4)

                self.logger.info(f"Processed file: {file_path}")

        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error(f"Error formatting JSON file {file_path}: {e}")

    def __process_json_segment(self, segment: json) -> json:
        for key in self.__json_keys_to_remove:
            segment.pop(key, None)

        segment["text"] = self.__replace_unicode_chars(segment.get("text", ""))
        segment.update({
            "author": "",
            "comment": "",
            "tags": ["", ""],
            "location": "",
            "actors": ["", ""],
        })
        return segment

    @staticmethod
    def __replace_unicode_chars(text: str) -> str:
        for unicode_char, char in TranscriptionGenerator.UNICODE_TO_POLISH_MAP.items():
            text = text.replace(unicode_char, char)
        return text
