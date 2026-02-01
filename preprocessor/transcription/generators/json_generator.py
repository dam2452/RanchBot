import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class JsonGenerator:
    DEFAULT_KEYS_TO_REMOVE: List[str] = [
        "tokens", "no_speech_prob", "compression_ratio", "avg_logprob", "temperature",
    ]

    UNICODE_TO_POLISH_MAP: Dict[str, str] = {
        '\\u0105': 'ą', '\\u0107': 'ć', '\\u0119': 'ę', '\\u0142': 'ł',
        '\\u0144': 'ń', '\\u00F3': 'ó', '\\u015B': 'ś', '\\u017A': 'ź',
        '\\u017C': 'ż', '\\u0104': 'Ą', '\\u0106': 'Ć', '\\u0118': 'Ę',
        '\\u0141': 'Ł', '\\u0143': 'Ń', '\\u00D3': 'Ó', '\\u015A': 'Ś',
        '\\u0179': 'Ź', '\\u017B': 'Ż',
    }

    def __init__(
        self,
        jsons_dir: Path,
        output_dir: Path,
        logger: ErrorHandlingLogger,
        extra_keys_to_remove: List[str],
    ):
        self.__jsons_dir: Path = jsons_dir
        self.__output_dir: Path = output_dir
        self.__logger: ErrorHandlingLogger = logger
        self.__keys_to_remove: List[str] = self.DEFAULT_KEYS_TO_REMOVE + extra_keys_to_remove

        self.__output_dir.mkdir(parents=True, exist_ok=True)

    def __call__(self) -> None:
        for item in self.__jsons_dir.rglob("*"):
            if item.is_file() and item.suffix == ".json":
                output_path = self.__output_dir / item.name
                self.__format_json(item, output_path)

    def __format_json(self, file_path: Path, output_path: Path) -> None:
        try:
            with file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if "segments" in data:
                data["segments"] = [self.__process_json_segment(segment) for segment in data["segments"]]

                with output_path.open("w", encoding="utf-8") as file:
                    json.dump({"segments": data["segments"]}, file, ensure_ascii=False, indent=4)

                self.__logger.info(f"Processed file: {file_path}")

        except Exception as e:
            self.__logger.error(f"Error formatting JSON file {file_path}: {e}")

    def __process_json_segment(self, segment: Dict[str, Any]) -> Dict[str, Any]:
        for key in self.__keys_to_remove:
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
        for unicode_char, char in JsonGenerator.UNICODE_TO_POLISH_MAP.items():
            text = text.replace(unicode_char, char)
        return text
