import io
import json
import logging
from pathlib import Path
from typing import (
    Dict,
    List,
)
import zipfile


class ZipExtractor:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def extract_to_memory(self, zip_path: Path) -> Dict[str, io.BytesIO]:
        extracted_files = {}

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for file_info in zf.infolist():
                    if not file_info.filename.endswith('.jsonl'):
                        continue

                    content = zf.read(file_info.filename)
                    buffer = io.BytesIO(content)

                    jsonl_type = self._detect_type_from_filename(file_info.filename)
                    if jsonl_type:
                        extracted_files[jsonl_type] = buffer

        except zipfile.BadZipFile as e:
            self.logger.error(f"Corrupted zip file: {zip_path}")
            raise ValueError(f"Invalid zip file: {zip_path}") from e

        return extracted_files

    def parse_jsonl_from_memory(self, buffer: io.BytesIO) -> List[Dict]:
        documents = []
        buffer.seek(0)

        for line in buffer:
            line_str = line.decode('utf-8').strip()
            if line_str:
                try:
                    doc = json.loads(line_str)
                    documents.append(doc)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse JSONL line: {e}")

        return documents

    def _detect_type_from_filename(self, filename: str) -> str:
        for type in ["text_segments", "text_embeddings", "video_frames", "episode_name", "full_episode_embedding", "sound_event_embeddings", "sound_events"]:
            if type in filename:
                return type
        return None
        return None
