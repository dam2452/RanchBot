import io
import json
import logging
import zipfile
from pathlib import Path
from typing import Dict, List


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
        if 'text_segments' in filename:
            return 'text_segments'
        elif 'text_embeddings' in filename:
            return 'text_embeddings'
        elif 'video_frames' in filename:
            return 'video_frames'
        elif 'episode_name' in filename:
            return 'episode_names'
        elif 'full_episode_embedding' in filename:
            return 'full_episode_embeddings'
        elif 'sound_event_embeddings' in filename:
            return 'sound_event_embeddings'
        elif 'sound_events' in filename:
            return 'sound_events'
        else:
            return None
