import io
import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)
import zipfile


class ZipExtractor:
    def __init__(self, logger: logging.Logger):
        self.__logger = logger

    def extract_to_memory(self, zip_path: Path) -> Dict[str, io.BytesIO]:
        extracted_files = {}

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for file_info in zf.infolist():
                    if not file_info.filename.endswith('.jsonl'):
                        continue

                    content = zf.read(file_info.filename)
                    buffer = io.BytesIO(content)

                    jsonl_type = self.__detect_type_from_filename(file_info.filename)
                    if jsonl_type:
                        extracted_files[jsonl_type] = buffer

        except zipfile.BadZipFile as e:
            self.__logger.error(f"Corrupted zip file: {zip_path}")
            raise ValueError(f"Invalid zip file: {zip_path}") from e

        return extracted_files

    def parse_jsonl_from_memory(self, buffer: io.BytesIO) -> List[Dict[str, Any]]:
        documents = []
        buffer.seek(0)

        for line in buffer:
            line_str = line.decode('utf-8').strip()
            if line_str:
                try:
                    doc = json.loads(line_str)
                    documents.append(doc)
                except json.JSONDecodeError as e:
                    self.__logger.warning(f"Failed to parse JSONL line: {e}")

        return documents

    def __detect_type_from_filename(self, filename: str) -> Optional[str]:
        _type_mapping = {
            'text_segments': 'text_segments',
            'text_embeddings': 'text_embeddings',
            'video_frames': 'video_frames',
            'episode_name': 'episode_names',
            'full_episode_embedding': 'full_episode_embeddings',
            'sound_event_embeddings': 'sound_event_embeddings',
            'sound_events': 'sound_events',
        }

        for key, value in _type_mapping.items():
            if key in filename:
                return value

        return None
